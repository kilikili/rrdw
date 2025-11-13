#!/bin/bash
# test_python_collector.sh - 測試 Python 收集器
# 用途：快速測試 isp_traffic_collector_final.py 是否正常運作

set -e

# 顏色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 印出有顏色的文字
print_color() {
    local color=$1
    local text=$2
    echo -e "${color}${text}${NC}"
}

print_color "$BLUE" "=========================================="
print_color "$BLUE" "ISP Traffic Collector - 測試腳本"
print_color "$BLUE" "=========================================="
echo ""

# ========================================
# 檢查必要工具
# ========================================
print_color "$YELLOW" "[1/6] 檢查必要工具..."

MISSING=0

# Python3
if command -v python3 &> /dev/null; then
    PYTHON_VER=$(python3 --version 2>&1)
    print_color "$GREEN" "  ✓ Python3: $PYTHON_VER"
else
    print_color "$RED" "  ✗ Python3: 未安裝"
    MISSING=1
fi

# snmpget
if command -v snmpget &> /dev/null; then
    SNMP_VER=$(snmpget --version 2>&1 | head -1)
    print_color "$GREEN" "  ✓ SNMP: $SNMP_VER"
else
    print_color "$RED" "  ✗ SNMP: 未安裝"
    MISSING=1
fi

# rrdtool
if command -v rrdtool &> /dev/null; then
    RRD_VER=$(rrdtool --version | head -1)
    print_color "$GREEN" "  ✓ RRDtool: $RRD_VER"
else
    print_color "$RED" "  ✗ RRDtool: 未安裝"
    MISSING=1
fi

if [ $MISSING -eq 1 ]; then
    echo ""
    print_color "$RED" "錯誤: 缺少必要工具"
    echo "請執行: sudo apt-get install snmp rrdtool python3"
    exit 1
fi

echo ""

# ========================================
# 檢查腳本檔案
# ========================================
print_color "$YELLOW" "[2/6] 檢查腳本檔案..."

COLLECTOR="isp_traffic_collector_final.py"

if [ -f "$COLLECTOR" ]; then
    print_color "$GREEN" "  ✓ $COLLECTOR 存在"
    
    # 檢查是否可執行 Python
    if python3 -m py_compile "$COLLECTOR" 2>/dev/null; then
        print_color "$GREEN" "  ✓ Python 語法正確"
    else
        print_color "$RED" "  ✗ Python 語法錯誤"
        exit 1
    fi
else
    print_color "$RED" "  ✗ $COLLECTOR 不存在"
    exit 1
fi

echo ""

# ========================================
# 詢問測試參數
# ========================================
print_color "$YELLOW" "[3/6] 設定測試參數..."

# 預設值
DEFAULT_IP="192.168.1.1"
DEFAULT_SLOT="1"
DEFAULT_PORT="0"
DEFAULT_COMMUNITY="public"

# 詢問或使用預設值
if [ -t 0 ]; then
    # 互動模式
    read -p "設備 IP [$DEFAULT_IP]: " TEST_IP
    TEST_IP=${TEST_IP:-$DEFAULT_IP}
    
    read -p "Slot 編號 [$DEFAULT_SLOT]: " TEST_SLOT
    TEST_SLOT=${TEST_SLOT:-$DEFAULT_SLOT}
    
    read -p "Port 編號 [$DEFAULT_PORT]: " TEST_PORT
    TEST_PORT=${TEST_PORT:-$DEFAULT_PORT}
    
    read -p "SNMP Community [$DEFAULT_COMMUNITY]: " TEST_COMMUNITY
    TEST_COMMUNITY=${TEST_COMMUNITY:-$DEFAULT_COMMUNITY}
else
    # 非互動模式，使用預設值
    TEST_IP=$DEFAULT_IP
    TEST_SLOT=$DEFAULT_SLOT
    TEST_PORT=$DEFAULT_PORT
    TEST_COMMUNITY=$DEFAULT_COMMUNITY
fi

print_color "$GREEN" "  測試設備: $TEST_IP"
print_color "$GREEN" "  Slot: $TEST_SLOT, Port: $TEST_PORT"
print_color "$GREEN" "  Community: ***"

echo ""

# ========================================
# 測試 SNMP 連線
# ========================================
print_color "$YELLOW" "[4/6] 測試 SNMP 連線..."

SNMP_TEST=$(snmpget -v2c -c "$TEST_COMMUNITY" -t 5 -r 1 "$TEST_IP" sysDescr.0 2>&1)

if [ $? -eq 0 ]; then
    print_color "$GREEN" "  ✓ SNMP 連線成功"
    # 顯示系統描述（前 100 字元）
    SYS_DESC=$(echo "$SNMP_TEST" | cut -c1-100)
    echo "  系統: $SYS_DESC..."
else
    print_color "$RED" "  ✗ SNMP 連線失敗"
    echo "  錯誤: $SNMP_TEST"
    echo ""
    print_color "$YELLOW" "可能的原因："
    echo "  1. IP 位址錯誤或設備離線"
    echo "  2. SNMP community string 錯誤"
    echo "  3. 防火牆阻擋 UDP 161"
    echo "  4. 設備未啟用 SNMP"
    exit 1
fi

echo ""

# ========================================
# 測試介面列表
# ========================================
print_color "$YELLOW" "[5/6] 測試介面列表..."

IF_LIST=$(snmpwalk -v2c -c "$TEST_COMMUNITY" -t 5 "$TEST_IP" ifDescr 2>&1 | head -10)

if [ $? -eq 0 ]; then
    print_color "$GREEN" "  ✓ 可以取得介面列表"
    echo "  前 10 個介面："
    echo "$IF_LIST" | sed 's/^/    /'
else
    print_color "$RED" "  ✗ 無法取得介面列表"
    echo "  錯誤: $IF_LIST"
fi

echo ""

# ========================================
# 執行收集器測試
# ========================================
print_color "$YELLOW" "[6/6] 執行收集器測試..."

# 建立測試目錄
TEST_DIR="/tmp/isp_collector_test_$$"
mkdir -p "$TEST_DIR"

# 設定環境變數
export LOG_LEVEL="INFO"
export SNMP_COMMUNITY="$TEST_COMMUNITY"

# 建立臨時 config
cat > "$TEST_DIR/config.ini" << EOF
[snmp]
default_community = $TEST_COMMUNITY
timeout = 5
retries = 2

[rrd]
base_dir = $TEST_DIR/rrd
step = 1200

[logging]
log_level = INFO
EOF

# 建立 RRD 目錄
mkdir -p "$TEST_DIR/rrd"

print_color "$BLUE" "  執行收集器..."
echo ""

# 執行收集器（在測試目錄）
cd "$TEST_DIR"
python3 "$OLDPWD/$COLLECTOR" "$TEST_IP" "$TEST_SLOT" "$TEST_PORT" "測試" "$TEST_COMMUNITY" 2>&1 | tee collector_output.log

COLLECTOR_EXIT=$?

echo ""

# ========================================
# 檢查結果
# ========================================
print_color "$BLUE" "=========================================="
print_color "$BLUE" "測試結果"
print_color "$BLUE" "=========================================="
echo ""

if [ $COLLECTOR_EXIT -eq 0 ]; then
    print_color "$GREEN" "✓ 收集器執行成功"
    
    # 檢查 RRD 檔案
    RRD_FILE=$(ls "$TEST_DIR/rrd/"*.rrd 2>/dev/null | head -1)
    
    if [ -f "$RRD_FILE" ]; then
        print_color "$GREEN" "✓ RRD 檔案已建立: $(basename "$RRD_FILE")"
        
        # 顯示 RRD 資訊
        echo ""
        print_color "$BLUE" "RRD 檔案資訊:"
        rrdtool info "$RRD_FILE" | head -30
        
        # 顯示最後更新
        echo ""
        print_color "$BLUE" "最後更新:"
        rrdtool lastupdate "$RRD_FILE"
    else
        print_color "$YELLOW" "⚠ RRD 檔案未建立（可能是首次執行）"
    fi
else
    print_color "$RED" "✗ 收集器執行失敗 (退出碼: $COLLECTOR_EXIT)"
    
    echo ""
    print_color "$YELLOW" "常見問題："
    echo "  1. 找不到介面 → 檢查 Slot/Port 編號是否正確"
    echo "  2. SNMP timeout → 檢查網路連線和防火牆"
    echo "  3. 權限錯誤 → 檢查 RRD 目錄權限"
    echo ""
    echo "完整輸出請查看: $TEST_DIR/collector_output.log"
fi

echo ""

# ========================================
# 清理
# ========================================
if [ $COLLECTOR_EXIT -eq 0 ]; then
    read -p "是否保留測試檔案? (y/N): " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$TEST_DIR"
        print_color "$GREEN" "測試檔案已清理"
    else
        print_color "$YELLOW" "測試檔案保留在: $TEST_DIR"
    fi
else
    print_color "$YELLOW" "測試檔案保留在: $TEST_DIR"
    echo "請檢查日誌: $TEST_DIR/collector_output.log"
fi

echo ""

# ========================================
# 總結
# ========================================
if [ $COLLECTOR_EXIT -eq 0 ]; then
    print_color "$GREEN" "=========================================="
    print_color "$GREEN" "✓ 所有測試通過！"
    print_color "$GREEN" "=========================================="
    echo ""
    echo "下一步："
    echo "  1. 編輯 config.ini 設定正式環境"
    echo "  2. 建立設備列表 CSV"
    echo "  3. 整合到 run_collector_group.sh"
    echo "  4. 設定 crontab 定期執行"
    echo ""
    exit 0
else
    print_color "$RED" "=========================================="
    print_color "$RED" "✗ 測試失敗"
    print_color "$RED" "=========================================="
    echo ""
    echo "請檢查："
    echo "  1. 設備 IP 和 SNMP community 是否正確"
    echo "  2. Slot/Port 編號是否正確"
    echo "  3. 網路連線是否正常"
    echo "  4. 查看詳細日誌: $TEST_DIR/collector_output.log"
    echo ""
    exit 1
fi
