#!/bin/bash
###############################################################################
# RRDW Traffic Collection System - Quick Setup Script
# 快速設置腳本
###############################################################################

set -e  # 遇到錯誤立即退出

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 基礎設定
BASE_DIR="/opt/isp_monitor"
BACKUP_DIR="/backup/isp_monitor"
LOG_FILE="/tmp/rrdw_setup.log"

# 印出帶顏色的訊息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

# 檢查是否為 root
check_root() {
    if [ "$EUID" -ne 0 ]; then 
        print_error "請使用 root 權限執行此腳本"
        echo "使用方式: sudo $0"
        exit 1
    fi
}

# 偵測作業系統
detect_os() {
    if [ -f /etc/centos-release ] || [ -f /etc/redhat-release ]; then
        OS="centos"
        print_info "偵測到 CentOS/RHEL 系統"
    elif [ -f /etc/lsb-release ] || [ -f /etc/debian_version ]; then
        OS="ubuntu"
        print_info "偵測到 Ubuntu/Debian 系統"
    else
        print_warning "無法偵測作業系統，假設為 Ubuntu"
        OS="ubuntu"
    fi
}

# 安裝系統套件
install_system_packages() {
    print_info "安裝系統套件..."
    
    if [ "$OS" = "centos" ]; then
        yum install -y epel-release
        yum install -y rrdtool python3 python3-pip net-snmp-utils git
    else
        apt-get update
        apt-get install -y rrdtool python3 python3-pip snmp git
    fi
    
    print_success "系統套件安裝完成"
}

# 安裝 Python 套件
install_python_packages() {
    print_info "安裝 Python 套件..."
    
    pip3 install --upgrade pip
    pip3 install pysnmp pysnmp-mibs configparser
    
    # 嘗試安裝 RRD Python 綁定 (選用)
    pip3 install rrdtool || print_warning "rrdtool Python 綁定安裝失敗 (非必要)"
    
    print_success "Python 套件安裝完成"
}

# 建立目錄結構
create_directory_structure() {
    print_info "建立目錄結構於 $BASE_DIR ..."
    
    # 建立主要目錄
    mkdir -p "$BASE_DIR"/{config/maps,collectors,core,orchestrator,logs,reports/{daily,weekly,monthly}}
    
    # 建立資料目錄
    mkdir -p "$BASE_DIR"/data/{user,sum,sum2m,circuit}
    
    # 建立備份目錄
    mkdir -p "$BACKUP_DIR"
    
    # 設定權限
    chmod 755 "$BASE_DIR"
    chmod 755 "$BASE_DIR"/data
    chmod 755 "$BASE_DIR"/logs
    
    print_success "目錄結構建立完成"
}

# 部署配置檔案
deploy_config_files() {
    print_info "部署配置檔案..."
    
    # 檢查是否已有配置檔案
    if [ -f "$BASE_DIR/config/config.ini" ]; then
        print_warning "config.ini 已存在，備份為 config.ini.bak"
        cp "$BASE_DIR/config/config.ini" "$BASE_DIR/config/config.ini.bak.$(date +%Y%m%d%H%M%S)"
    fi
    
    # 部署範本
    if [ -f "config.ini.template" ]; then
        cp config.ini.template "$BASE_DIR/config/config.ini"
        print_success "config.ini 部署完成"
    else
        print_warning "找不到 config.ini.template，請手動建立"
    fi
    
    # 部署 BRAS-Map 範本
    if [ ! -f "$BASE_DIR/config/BRAS-Map.txt" ]; then
        cat > "$BASE_DIR/config/BRAS-Map.txt" << 'EOF'
# BRAS Map File - 設備映射檔案
# 格式: Area	DeviceType	IP	CircuitID	Slot(Fpc)	Port	InterfaceType	BandwidthMax	IfAssign	Pic
#
# DeviceType:
#   1 = E320 (Legacy BRAS)
#   2 = MX960 (Dynamic IP, High Capacity)
#   3 = MX240 (Dynamic IP with PPPoE)
#   4 = ACX7024 (Fixed IP Services)
#
# 請根據實際環境修改以下內容:
# taipei_1	3	192.168.1.1	CIRCUIT001	1	0	GE	1000	0	0
# taipei_2	2	192.168.1.2	CIRCUIT002	1	1	XE	1000	0	0
EOF
        print_success "BRAS-Map.txt 範本建立完成"
    else
        print_warning "BRAS-Map.txt 已存在，跳過"
    fi
}

# 設定 Python 路徑
setup_python_path() {
    print_info "設定 Python 路徑..."
    
    # 加入 PYTHONPATH
    if ! grep -q "PYTHONPATH.*$BASE_DIR" /etc/environment; then
        echo "PYTHONPATH=$BASE_DIR:\$PYTHONPATH" >> /etc/environment
        print_success "PYTHONPATH 已加入 /etc/environment"
    else
        print_warning "PYTHONPATH 已設定"
    fi
}

# 建立 systemd 服務 (選用)
create_systemd_service() {
    print_info "建立 systemd 服務..."
    
    cat > /etc/systemd/system/rrdw-collector.service << EOF
[Unit]
Description=RRDW Traffic Collector Service
After=network.target

[Service]
Type=oneshot
User=root
WorkingDirectory=$BASE_DIR
ExecStart=/usr/bin/python3 $BASE_DIR/orchestrator/dispatcher.py
StandardOutput=append:$BASE_DIR/logs/collector.log
StandardError=append:$BASE_DIR/logs/collector.log

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    print_success "systemd 服務建立完成"
    print_info "使用 'systemctl start rrdw-collector' 啟動服務"
}

# 建立 cron 排程
setup_cron_job() {
    print_info "設定 cron 排程..."
    
    # 檢查是否已有排程
    if crontab -l 2>/dev/null | grep -q "dispatcher.py"; then
        print_warning "cron 排程已存在"
        return
    fi
    
    # 加入 cron 任務 (每 20 分鐘)
    (crontab -l 2>/dev/null; echo "*/20 * * * * cd $BASE_DIR && /usr/bin/python3 orchestrator/dispatcher.py >> logs/cron.log 2>&1") | crontab -
    
    print_success "cron 排程設定完成 (每 20 分鐘執行一次)"
}

# 執行初始測試
run_initial_tests() {
    print_info "執行初始測試..."
    
    # 測試 Python
    if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,6) else 1)"; then
        PYTHON_VERSION=$(python3 --version)
        print_success "Python 版本檢查通過: $PYTHON_VERSION"
    else
        print_error "Python 版本過舊，需要 3.6 以上"
        return 1
    fi
    
    # 測試 rrdtool
    if command -v rrdtool &> /dev/null; then
        RRDTOOL_VERSION=$(rrdtool --version | head -n1)
        print_success "rrdtool 檢查通過: $RRDTOOL_VERSION"
    else
        print_error "rrdtool 未安裝"
        return 1
    fi
    
    # 測試 Python 套件
    if python3 -c "import pysnmp" &> /dev/null; then
        print_success "pysnmp 套件檢查通過"
    else
        print_error "pysnmp 套件未安裝"
        return 1
    fi
    
    print_success "所有初始測試通過！"
}

# 顯示後續步驟
show_next_steps() {
    echo ""
    echo "=========================================="
    echo "          安裝完成！"
    echo "=========================================="
    echo ""
    echo "後續步驟:"
    echo ""
    echo "1. 編輯配置檔案:"
    echo "   vim $BASE_DIR/config/config.ini"
    echo ""
    echo "2. 編輯 BRAS 映射檔案:"
    echo "   vim $BASE_DIR/config/BRAS-Map.txt"
    echo ""
    echo "3. 產生設備 Map 檔案範本:"
    echo "   python3 collector_validator.py template --output $BASE_DIR/config/maps/map_192.168.1.1.txt --type 3"
    echo ""
    echo "4. 驗證 Map 檔案格式:"
    echo "   python3 collector_validator.py validate --map $BASE_DIR/config/maps/map_192.168.1.1.txt"
    echo ""
    echo "5. 測試 SNMP 連線:"
    echo "   python3 collector_validator.py test --ip 192.168.1.1 --type 3 --map $BASE_DIR/config/maps/map_192.168.1.1.txt"
    echo ""
    echo "6. 手動執行收集器測試:"
    echo "   cd $BASE_DIR && python3 orchestrator/dispatcher.py --dry-run"
    echo ""
    echo "7. 查看日誌:"
    echo "   tail -f $BASE_DIR/logs/collector.log"
    echo ""
    echo "=========================================="
    echo ""
    echo "文件位置:"
    echo "  - 主要目錄: $BASE_DIR"
    echo "  - 配置檔案: $BASE_DIR/config/"
    echo "  - 日誌目錄: $BASE_DIR/logs/"
    echo "  - 資料目錄: $BASE_DIR/data/"
    echo ""
    echo "=========================================="
}

# 主程式
main() {
    echo "=========================================="
    echo "   RRDW 系統快速設置腳本"
    echo "=========================================="
    echo ""
    echo "此腳本將會:"
    echo "  1. 安裝必要的系統套件"
    echo "  2. 安裝 Python 相依套件"
    echo "  3. 建立目錄結構"
    echo "  4. 部署配置檔案範本"
    echo "  5. 設定 cron 排程"
    echo ""
    read -p "是否繼續? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "安裝已取消"
        exit 0
    fi
    
    # 執行安裝步驟
    check_root
    detect_os
    install_system_packages
    install_python_packages
    create_directory_structure
    deploy_config_files
    setup_python_path
    
    # 詢問是否設定排程
    echo ""
    read -p "是否設定 cron 排程? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        setup_cron_job
    fi
    
    # 執行測試
    run_initial_tests
    
    # 顯示後續步驟
    show_next_steps
    
    print_success "安裝腳本執行完成！"
}

# 執行主程式
main "$@"
