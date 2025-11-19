#!/bin/bash
###############################################################################
# quick_test.sh - 快速驗證腳本
# 
# 此腳本快速檢查收集器環境是否正確設定
###############################################################################

set -e

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_DIR="${1:-/opt/isp_monitor}"
ERRORS=0
WARNINGS=0

echo ""
echo "=========================================="
echo "   RRDW 收集器環境驗證"
echo "=========================================="
echo ""
echo "檢查目錄: $INSTALL_DIR"
echo ""

# 檢查函數
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((ERRORS++))
}

# 1. 檢查 Python
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. Python 環境"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    check_pass "Python 3 已安裝: $PYTHON_VERSION"
else
    check_fail "Python 3 未安裝"
fi

# 檢查 pysnmp
if python3 -c "import pysnmp" 2>/dev/null; then
    check_pass "pysnmp 已安裝"
else
    check_fail "pysnmp 未安裝 (pip3 install pysnmp)"
fi

# 檢查 configparser
if python3 -c "import configparser" 2>/dev/null; then
    check_pass "configparser 已安裝"
else
    check_warn "configparser 未安裝（Python 3.2+ 內建）"
fi

# 2. 檢查系統工具
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. 系統工具"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if command -v rrdtool &> /dev/null; then
    RRD_VERSION=$(rrdtool --version | head -1 | awk '{print $2}')
    check_pass "rrdtool 已安裝: $RRD_VERSION"
else
    check_fail "rrdtool 未安裝"
fi

if command -v snmpget &> /dev/null; then
    check_pass "snmpget 已安裝"
else
    check_warn "snmpget 未安裝（非必要，但建議安裝）"
fi

if command -v snmpwalk &> /dev/null; then
    check_pass "snmpwalk 已安裝"
else
    check_warn "snmpwalk 未安裝（非必要，但建議安裝）"
fi

# 3. 檢查目錄結構
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. 目錄結構"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

DIRS=(
    "$INSTALL_DIR/core"
    "$INSTALL_DIR/collectors"
    "$INSTALL_DIR/config/maps"
    "$INSTALL_DIR/data/user"
    "$INSTALL_DIR/data/sum"
    "$INSTALL_DIR/data/sum2m"
    "$INSTALL_DIR/data/circuit"
    "$INSTALL_DIR/logs"
)

for dir in "${DIRS[@]}"; do
    if [ -d "$dir" ]; then
        check_pass "目錄存在: $(basename $(dirname $dir))/$(basename $dir)"
    else
        check_warn "目錄不存在: $dir"
    fi
done

# 4. 檢查核心模組
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. 核心模組"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

CORE_MODULES=(
    "config_loader.py"
    "snmp_helper.py"
    "rrd_manager.py"
)

for module in "${CORE_MODULES[@]}"; do
    if [ -f "$INSTALL_DIR/core/$module" ]; then
        check_pass "$module 已部署"
        
        # 測試模組匯入
        MODULE_NAME=$(basename $module .py)
        if python3 -c "import sys; sys.path.insert(0, '$INSTALL_DIR'); from core.$MODULE_NAME import *" 2>/dev/null; then
            check_pass "  └─ 可正常匯入"
        else
            check_warn "  └─ 匯入測試失敗"
        fi
    else
        check_fail "$module 未部署"
    fi
done

# 5. 檢查收集器
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5. 收集器"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

COLLECTORS=(
    "base_collector.py"
    "collector_e320.py"
    "collector_mx960.py"
    "collector_mx240.py"
    "collector_acx7024.py"
)

for collector in "${COLLECTORS[@]}"; do
    if [ -f "$INSTALL_DIR/collectors/$collector" ]; then
        if [ -x "$INSTALL_DIR/collectors/$collector" ]; then
            check_pass "$collector (可執行)"
        else
            check_warn "$collector (無執行權限)"
        fi
    else
        check_fail "$collector 未部署"
    fi
done

# 6. 檢查配置檔案
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6. 配置檔案"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "$INSTALL_DIR/config/config.ini" ]; then
    check_pass "config.ini 已設定"
else
    check_warn "config.ini 不存在（請複製 config.ini.example）"
fi

if [ -f "$INSTALL_DIR/config/BRAS-Map.txt" ]; then
    LINE_COUNT=$(grep -v '^#' "$INSTALL_DIR/config/BRAS-Map.txt" | grep -v '^$' | wc -l)
    check_pass "BRAS-Map.txt 已設定 ($LINE_COUNT 個設備)"
else
    check_warn "BRAS-Map.txt 不存在（請複製 BRAS-Map.txt.example）"
fi

# 檢查 Map 檔案
MAP_COUNT=$(find "$INSTALL_DIR/config/maps" -name "map_*.txt" 2>/dev/null | wc -l)
if [ $MAP_COUNT -gt 0 ]; then
    check_pass "找到 $MAP_COUNT 個 Map 檔案"
else
    check_warn "未找到 Map 檔案（請建立 map_<IP>.txt）"
fi

# 7. 檢查權限
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7. 檔案權限"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 檢查資料目錄寫入權限
if [ -w "$INSTALL_DIR/data" ]; then
    check_pass "data 目錄可寫入"
else
    check_fail "data 目錄無寫入權限"
fi

# 檢查日誌目錄寫入權限
if [ -w "$INSTALL_DIR/logs" ]; then
    check_pass "logs 目錄可寫入"
else
    check_fail "logs 目錄無寫入權限"
fi

# 8. 快速功能測試
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "8. 功能測試"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 測試 RRD 建立
TEST_RRD="/tmp/test_rrdw_$(date +%s).rrd"
if rrdtool create "$TEST_RRD" --step 300 \
    DS:test:GAUGE:600:0:U \
    RRA:AVERAGE:0.5:1:100 2>/dev/null; then
    check_pass "RRD 建立功能正常"
    rm -f "$TEST_RRD"
else
    check_fail "RRD 建立失敗"
fi

# 總結
echo ""
echo "=========================================="
echo "   驗證結果"
echo "=========================================="

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ 所有檢查通過！環境已就緒。${NC}"
    EXIT_CODE=0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ 通過 ($WARNINGS 個警告)${NC}"
    echo "可以繼續，但建議處理警告項目。"
    EXIT_CODE=0
else
    echo -e "${RED}✗ 失敗 ($ERRORS 個錯誤, $WARNINGS 個警告)${NC}"
    echo "請先解決錯誤項目後再繼續。"
    EXIT_CODE=1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "後續步驟:"
echo "  1. 設定 config.ini"
echo "  2. 建立 BRAS-Map.txt"
echo "  3. 產生 Map 檔案"
echo "  4. 測試收集器"
echo ""
echo "詳細說明請參考 TESTING_GUIDE.md"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

exit $EXIT_CODE
