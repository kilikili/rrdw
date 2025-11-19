#!/bin/bash
###############################################################################
# deploy_collectors.sh - 收集器部署腳本
# 
# 此腳本自動部署所有收集器程式碼到指定目錄
###############################################################################

set -e

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 預設安裝路徑
INSTALL_DIR="/opt/isp_monitor"

echo "=========================================="
echo "   RRDW 收集器程式部署"
echo "=========================================="
echo ""

# 檢查是否為 root
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}警告: 建議使用 root 權限執行此腳本${NC}"
    echo "繼續執行可能會遇到權限問題"
    read -p "是否繼續? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

# 詢問安裝路徑
read -p "安裝路徑 [${INSTALL_DIR}]: " INPUT_DIR
if [ ! -z "$INPUT_DIR" ]; then
    INSTALL_DIR="$INPUT_DIR"
fi

echo ""
echo "安裝路徑: $INSTALL_DIR"
echo ""

# 建立目錄結構
echo -e "${GREEN}[1/5]${NC} 建立目錄結構..."
mkdir -p "$INSTALL_DIR"/{core,collectors,config/maps,data/{user,sum,sum2m,circuit},logs}

# 複製核心模組
echo -e "${GREEN}[2/5]${NC} 部署核心模組..."
cp core/config_loader.py "$INSTALL_DIR/core/"
cp core/snmp_helper.py "$INSTALL_DIR/core/"
cp core/rrd_manager.py "$INSTALL_DIR/core/"
cp core/__init__.py "$INSTALL_DIR/core/"

# 複製收集器
echo -e "${GREEN}[3/5]${NC} 部署收集器..."
cp collectors/base_collector.py "$INSTALL_DIR/collectors/"
cp collectors/collector_e320.py "$INSTALL_DIR/collectors/"
cp collectors/collector_mx240.py "$INSTALL_DIR/collectors/"
cp collectors/collector_mx960.py "$INSTALL_DIR/collectors/"
cp collectors/collector_acx7024.py "$INSTALL_DIR/collectors/"
cp collectors/__init__.py "$INSTALL_DIR/collectors/"

# 設定權限
echo -e "${GREEN}[4/5]${NC} 設定執行權限..."
chmod +x "$INSTALL_DIR"/core/*.py
chmod +x "$INSTALL_DIR"/collectors/*.py

# 測試匯入
echo -e "${GREEN}[5/5]${NC} 測試模組匯入..."
cd "$INSTALL_DIR"

if python3 -c "import sys; sys.path.insert(0, '.'); from core.config_loader import ConfigLoader; print('✓ config_loader')" 2>/dev/null; then
    echo "  ✓ config_loader 可正常匯入"
else
    echo -e "  ${YELLOW}⚠ config_loader 匯入測試失敗（需要配置檔案）${NC}"
fi

if python3 -c "import sys; sys.path.insert(0, '.'); from core.snmp_helper import SNMPHelper; print('✓ snmp_helper')" 2>/dev/null; then
    echo "  ✓ snmp_helper 可正常匯入"
else
    echo -e "  ${RED}✗ snmp_helper 匯入失敗（檢查 pysnmp 套件）${NC}"
fi

if python3 -c "import sys; sys.path.insert(0, '.'); from core.rrd_manager import RRDManager; print('✓ rrd_manager')" 2>/dev/null; then
    echo "  ✓ rrd_manager 可正常匯入"
else
    echo -e "  ${YELLOW}⚠ rrd_manager 匯入測試失敗${NC}"
fi

echo ""
echo "=========================================="
echo "   部署完成！"
echo "=========================================="
echo ""
echo "程式位置:"
echo "  核心模組: $INSTALL_DIR/core/"
echo "  收集器:   $INSTALL_DIR/collectors/"
echo "  配置:     $INSTALL_DIR/config/"
echo "  資料:     $INSTALL_DIR/data/"
echo "  日誌:     $INSTALL_DIR/logs/"
echo ""
echo "後續步驟:"
echo "  1. 設定配置檔案: vim $INSTALL_DIR/config/config.ini"
echo "  2. 建立 BRAS Map: vim $INSTALL_DIR/config/BRAS-Map.txt"
echo "  3. 產生 Map 檔案: 使用 collector_validator.py template"
echo "  4. 測試收集器:   參考 TESTING_GUIDE.md"
echo ""
echo "測試指令範例:"
echo "  cd $INSTALL_DIR/collectors"
echo "  python3 collector_e320.py --ip <IP> --map ../config/maps/map_<IP>.txt --debug"
echo ""
