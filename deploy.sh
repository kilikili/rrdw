#!/bin/bash
# BRAS Map System - One-Click Deployment Script
# 一鍵部署和測試腳本

set -e  # 錯誤時退出

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 函數：印出訊息
print_header() {
    echo -e "\n${BLUE}=================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# 函數：檢查命令是否存在
check_command() {
    if command -v $1 &> /dev/null; then
        print_success "$1 已安裝"
        return 0
    else
        print_error "$1 未安裝"
        return 1
    fi
}

# 函數：檢查檔案是否存在
check_file() {
    if [ -f "$1" ]; then
        print_success "檔案存在: $1"
        return 0
    else
        print_error "檔案不存在: $1"
        return 1
    fi
}

# 主程式開始
print_header "BRAS Map 系統部署與測試"

echo "部署選項："
echo "1) 完整部署（檢查環境 + 安裝套件 + 測試）"
echo "2) 快速測試（只執行測試，不安裝套件）"
echo "3) 產生介面對照表"
echo "4) 執行資料收集（測試模式）"
echo "5) 顯示系統狀態"
echo "6) 清理測試資料"
echo ""
read -p "請選擇 [1-6]: " choice

case $choice in
    1)
        # 完整部署
        print_header "步驟 1: 檢查系統環境"
        
        # 檢查 Python 版本
        if check_command python3; then
            PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
            print_info "Python 版本: $PYTHON_VERSION"
            
            # 檢查版本是否 >= 3.7
            MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
            MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
            if [ $MAJOR -ge 3 ] && [ $MINOR -ge 7 ]; then
                print_success "Python 版本符合需求 (>= 3.7)"
            else
                print_warning "Python 版本過舊，建議升級到 3.7 以上"
            fi
        fi
        
        # 檢查 pip
        check_command pip3 || print_warning "建議安裝 pip3"
        
        # 檢查 SNMP 工具
        check_command snmpwalk || print_warning "建議安裝 snmp 套件"
        check_command snmpget || print_warning "建議安裝 snmp 套件"
        
        print_header "步驟 2: 安裝 Python 套件"
        
        # 檢查並安裝必要套件
        echo "檢查 Python 套件..."
        
        packages=("pysnmp" "mysql-connector-python")
        for pkg in "${packages[@]}"; do
            if python3 -c "import ${pkg//-/_}" 2>/dev/null; then
                print_success "$pkg 已安裝"
            else
                print_warning "$pkg 未安裝，嘗試安裝..."
                pip3 install $pkg --user || print_error "安裝 $pkg 失敗"
            fi
        done
        
        print_header "步驟 3: 檢查必要檔案"
        
        required_files=(
            "BRAS-Map.txt"
            "bras_map_reader.py"
            "bras_map_collector.py"
            "interface_mapping_generator.py"
            "test_bras_map.py"
        )
        
        all_files_exist=true
        for file in "${required_files[@]}"; do
            if ! check_file "$file"; then
                all_files_exist=false
            fi
        done
        
        if [ "$all_files_exist" = false ]; then
            print_error "部分必要檔案不存在，請檢查"
            exit 1
        fi
        
        print_header "步驟 4: 執行系統測試"
        
        echo "執行 BRAS Map 測試套件..."
        if python3 test_bras_map.py; then
            print_success "測試通過"
        else
            print_error "測試失敗，請檢查錯誤訊息"
            exit 1
        fi
        
        print_header "步驟 5: 產生介面對照表"
        
        echo "產生介面對照表..."
        if python3 interface_mapping_generator.py; then
            print_success "介面對照表產生成功"
            
            # 列出產生的檔案
            echo ""
            print_info "產生的檔案："
            ls -lh interface_mapping*.csv 2>/dev/null || print_warning "未找到產生的 CSV 檔案"
        else
            print_warning "產生介面對照表失敗"
        fi
        
        print_header "部署完成"
        
        print_success "BRAS Map 系統部署完成！"
        echo ""
        print_info "下一步："
        echo "  1. 檢查 BRAS-Map.txt 內容是否正確"
        echo "  2. 設定資料庫連線（如需要）"
        echo "  3. 執行資料收集測試: ./deploy.sh -> 選項 4"
        echo "  4. 檢視產生的介面對照表: interface_mapping*.csv"
        ;;
        
    2)
        # 快速測試
        print_header "快速測試模式"
        
        print_info "執行 BRAS Map 測試..."
        if python3 test_bras_map.py; then
            print_success "測試通過"
        else
            print_error "測試失敗"
            exit 1
        fi
        ;;
        
    3)
        # 產生介面對照表
        print_header "產生介面對照表"
        
        if python3 interface_mapping_generator.py; then
            print_success "介面對照表產生成功"
            echo ""
            print_info "產生的檔案："
            ls -lh interface_mapping*.csv
        else
            print_error "產生失敗"
            exit 1
        fi
        ;;
        
    4)
        # 執行資料收集（測試模式）
        print_header "執行資料收集（測試模式）"
        
        print_warning "注意：這是測試模式，將使用測試資料"
        print_info "如需正式收集，請修改 bras_map_collector.py 中的設定"
        echo ""
        
        read -p "確定要執行測試收集？(y/n): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            if python3 bras_map_collector.py; then
                print_success "測試收集完成"
                
                # 顯示產生的檔案
                if [ -f "traffic_data.txt" ]; then
                    echo ""
                    print_info "產生的資料檔案："
                    ls -lh traffic_data.txt
                    echo ""
                    print_info "前 10 筆資料："
                    head -10 traffic_data.txt
                fi
            else
                print_error "收集失敗"
                exit 1
            fi
        else
            print_info "取消執行"
        fi
        ;;
        
    5)
        # 顯示系統狀態
        print_header "系統狀態"
        
        echo "Python 環境："
        python3 --version
        echo ""
        
        echo "已安裝的套件："
        pip3 list | grep -E "(pysnmp|mysql)" || print_warning "相關套件未安裝"
        echo ""
        
        echo "檔案狀態："
        for file in BRAS-Map.txt bras_map_reader.py bras_map_collector.py test_bras_map.py; do
            if [ -f "$file" ]; then
                size=$(ls -lh "$file" | awk '{print $5}')
                mtime=$(stat -c %y "$file" | cut -d' ' -f1)
                print_success "$file ($size, 修改: $mtime)"
            else
                print_error "$file (不存在)"
            fi
        done
        echo ""
        
        echo "BRAS Map 統計："
        if [ -f "BRAS-Map.txt" ]; then
            circuits=$(grep -v '^#' BRAS-Map.txt | grep -v '^$' | wc -l)
            print_info "Circuit 數量: $circuits"
            
            # 統計設備類型
            echo ""
            print_info "設備類型分布："
            grep -v '^#' BRAS-Map.txt | grep -v '^$' | awk -F, '{print $2}' | sort | uniq -c | while read count type; do
                case $type in
                    1) device="MX240" ;;
                    2) device="MX960" ;;
                    3) device="E320" ;;
                    4) device="ACX7024" ;;
                    *) device="Unknown" ;;
                esac
                echo "  $device: $count"
            done
        fi
        
        echo ""
        echo "產生的檔案："
        ls -lh interface_mapping*.csv 2>/dev/null || print_info "尚未產生介面對照表"
        ls -lh traffic_data.txt 2>/dev/null || print_info "尚未收集流量資料"
        ;;
        
    6)
        # 清理測試資料
        print_header "清理測試資料"
        
        print_warning "將刪除以下檔案："
        echo "  - interface_mapping*.csv"
        echo "  - traffic_data.txt"
        echo ""
        
        read -p "確定要清理？(y/n): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            rm -f interface_mapping*.csv
            rm -f traffic_data.txt
            print_success "清理完成"
        else
            print_info "取消清理"
        fi
        ;;
        
    *)
        print_error "無效的選項"
        exit 1
        ;;
esac

echo ""
print_info "執行完成"
