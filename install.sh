#!/bin/bash
# install.sh
# ISP 流量監控系統 - 完整部署安裝腳本

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 函數定義
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "請使用 root 權限執行此腳本"
        exit 1
    fi
}

# 安裝目錄
INSTALL_DIR="/opt/rrdw"
RRD_DATA_DIR="/home/bulks_data"
CONFIG_DIR="$INSTALL_DIR/config"
LOG_DIR="/var/log/rrdw"
REPORT_DIR="/var/reports"

echo "=========================================="
echo "ISP 流量監控系統 - 安裝程式"
echo "=========================================="
echo ""

# 檢查 root
check_root

# 1. 檢查必要套件
log_info "檢查必要套件..."

# Python 3
if ! command -v python3 &> /dev/null; then
    log_error "未安裝 Python 3"
    exit 1
fi
log_info "✓ Python 3: $(python3 --version)"

# rrdtool
if ! command -v rrdtool &> /dev/null; then
    log_warn "未安裝 rrdtool，正在安裝..."
    if command -v apt-get &> /dev/null; then
        apt-get update && apt-get install -y rrdtool
    elif command -v yum &> /dev/null; then
        yum install -y rrdtool
    else
        log_error "無法自動安裝 rrdtool，請手動安裝"
        exit 1
    fi
fi
log_info "✓ rrdtool: $(rrdtool --version | head -1)"

# pip3
if ! command -v pip3 &> /dev/null; then
    log_warn "未安裝 pip3，正在安裝..."
    if command -v apt-get &> /dev/null; then
        apt-get install -y python3-pip
    elif command -v yum &> /dev/null; then
        yum install -y python3-pip
    fi
fi
log_info "✓ pip3: $(pip3 --version)"

# 2. 安裝 Python 套件
log_info "安裝 Python 套件..."
pip3 install --upgrade pip
pip3 install pysnmp==4.4.12 pymysql

# 3. 創建目錄結構
log_info "創建目錄結構..."

mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$RRD_DATA_DIR"
mkdir -p "$RRD_DATA_DIR/sum"
mkdir -p "$RRD_DATA_DIR/sum2m"
mkdir -p "$RRD_DATA_DIR/circuit"
mkdir -p "$LOG_DIR"
mkdir -p "$REPORT_DIR/daily"
mkdir -p "$REPORT_DIR/weekly"
mkdir -p "$REPORT_DIR/monthly"

log_info "✓ 目錄結構已創建"

# 4. 複製程式檔案
log_info "複製程式檔案..."

# 假設當前目錄有所有檔案
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 收集器
cp "$CURRENT_DIR"/base_collector.py "$INSTALL_DIR/"
cp "$CURRENT_DIR"/isp_traffic_collector_*.py "$INSTALL_DIR/" 2>/dev/null || true
cp "$CURRENT_DIR"/collector_dispatcher.py "$INSTALL_DIR/"

# 資料讀取器
cp "$CURRENT_DIR"/map_file_reader.py "$INSTALL_DIR/"
cp "$CURRENT_DIR"/bras_map_reader.py "$INSTALL_DIR/"

# 報表系統
cp "$CURRENT_DIR"/traffic_ranking_report.py "$INSTALL_DIR/"
cp "$CURRENT_DIR"/circuit_congestion_analysis.py "$INSTALL_DIR/"
cp "$CURRENT_DIR"/vlan_statistics.py "$INSTALL_DIR/"

# 腳本
cp "$CURRENT_DIR"/generate_*.sh "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR"/*.sh

log_info "✓ 程式檔案已複製"

# 5. 設定檔案
log_info "設定配置檔案..."

if [ ! -f "$CONFIG_DIR/BRAS-Map.txt" ]; then
    if [ -f "$CURRENT_DIR/BRAS-Map.txt" ]; then
        cp "$CURRENT_DIR/BRAS-Map.txt" "$CONFIG_DIR/"
    else
        log_warn "未找到 BRAS-Map.txt，請手動建立"
    fi
fi

log_info "✓ 配置檔案已設定"

# 6. 安裝 Cron 任務
log_info "安裝 Cron 任務..."

if [ -f "$CURRENT_DIR/isp-traffic-monitor.cron" ]; then
    # 更新路徑
    sed "s|/opt/rrdw|$INSTALL_DIR|g" "$CURRENT_DIR/isp-traffic-monitor.cron" > /etc/cron.d/isp-traffic-monitor
    chmod 644 /etc/cron.d/isp-traffic-monitor
    log_info "✓ Cron 任務已安裝"
else
    log_warn "未找到 cron 設定檔，請手動設定"
fi

# 7. 設定日誌輪轉
log_info "設定日誌輪轉..."

cat > /etc/logrotate.d/isp-traffic-monitor << 'EOF'
/var/log/rrdw/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
}
EOF

log_info "✓ 日誌輪轉已設定"

# 8. 權限設定
log_info "設定權限..."

chown -R root:root "$INSTALL_DIR"
chmod 755 "$INSTALL_DIR"
chmod 644 "$INSTALL_DIR"/*.py
chmod 755 "$INSTALL_DIR"/*.sh

chown -R root:root "$RRD_DATA_DIR"
chmod 755 "$RRD_DATA_DIR"

chown -R root:root "$LOG_DIR"
chmod 755 "$LOG_DIR"

log_info "✓ 權限已設定"

# 9. 驗證安裝
log_info "驗證安裝..."

if [ -f "$INSTALL_DIR/collector_dispatcher.py" ]; then
    log_info "✓ 收集器已安裝"
else
    log_error "收集器未安裝"
    exit 1
fi

if [ -f "$INSTALL_DIR/traffic_ranking_report.py" ]; then
    log_info "✓ 報表系統已安裝"
else
    log_error "報表系統未安裝"
    exit 1
fi

if [ -f "/etc/cron.d/isp-traffic-monitor" ]; then
    log_info "✓ Cron 任務已安裝"
else
    log_warn "Cron 任務未安裝"
fi

echo ""
echo "=========================================="
echo "安裝完成！"
echo "=========================================="
echo ""
echo "安裝目錄: $INSTALL_DIR"
echo "RRD 資料: $RRD_DATA_DIR"
echo "配置檔案: $CONFIG_DIR"
echo "日誌目錄: $LOG_DIR"
echo "報表目錄: $REPORT_DIR"
echo ""
echo "下一步："
echo "  1. 編輯 $CONFIG_DIR/BRAS-Map.txt"
echo "  2. 準備 Map File 到 $CONFIG_DIR/maps/"
echo "  3. 測試收集器:"
echo "     python3 $INSTALL_DIR/collector_dispatcher.py --help"
echo "  4. 查看 Cron 任務:"
echo "     cat /etc/cron.d/isp-traffic-monitor"
echo "  5. 查看日誌:"
echo "     tail -f $LOG_DIR/collector.log"
echo ""
echo "=========================================="

exit 0
