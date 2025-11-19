#!/bin/bash
###############################################################################
# quick_fix_pysnmp.sh - pysnmp 導入問題快速修正腳本
#
# 此腳本自動修正 pysnmp 導入問題
###############################################################################

set -e

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

INSTALL_DIR="${1:-/opt/isp_monitor}"

echo ""
echo "=========================================="
echo "   pysnmp 導入問題快速修正"
echo "=========================================="
echo ""
echo "安裝目錄: $INSTALL_DIR"
echo ""

# 檢查目錄是否存在
if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${RED}✗ 目錄不存在: $INSTALL_DIR${NC}"
    exit 1
fi

# 備份檔案
echo -e "${YELLOW}[1/3]${NC} 備份原始檔案..."

BACKUP_DIR="$INSTALL_DIR/backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [ -f "$INSTALL_DIR/tools/generate_map_template.py" ]; then
    cp "$INSTALL_DIR/tools/generate_map_template.py" "$BACKUP_DIR/"
    echo "  ✓ 已備份 generate_map_template.py"
fi

if [ -f "$INSTALL_DIR/tools/test_snmp_connection.py" ]; then
    cp "$INSTALL_DIR/tools/test_snmp_connection.py" "$BACKUP_DIR/"
    echo "  ✓ 已備份 test_snmp_connection.py"
fi

if [ -f "$INSTALL_DIR/core/snmp_helper.py" ]; then
    cp "$INSTALL_DIR/core/snmp_helper.py" "$BACKUP_DIR/"
    echo "  ✓ 已備份 snmp_helper.py"
fi

# 修正 generate_map_template.py
echo ""
echo -e "${YELLOW}[2/3]${NC} 修正導入語句..."

cat > "$INSTALL_DIR/tools/generate_map_template.py.tmp" << 'EOFIX1'
#!/usr/bin/env python3
"""
generate_map_template.py - Map 檔案範本產生器

根據 SNMP 查詢結果產生 Map 檔案範本
"""

import sys
import argparse
import os
from typing import List, Dict

try:
    from pysnmp.hlapi import (
        SnmpEngine, CommunityData, UdpTransportTarget, ContextData,
        ObjectType, ObjectIdentity, bulkCmd
    )
except ImportError:
    print("錯誤: 缺少 pysnmp 套件")
    print("請執行: pip3 install pysnmp")
    sys.exit(1)
EOFIX1

# 只替換 import 部分，保留其餘內容
if [ -f "$INSTALL_DIR/tools/generate_map_template.py" ]; then
    # 提取 import 之後的內容
    sed -n '20,$p' "$BACKUP_DIR/generate_map_template.py" >> "$INSTALL_DIR/tools/generate_map_template.py.tmp"
    mv "$INSTALL_DIR/tools/generate_map_template.py.tmp" "$INSTALL_DIR/tools/generate_map_template.py"
    chmod +x "$INSTALL_DIR/tools/generate_map_template.py"
    echo "  ✓ 已修正 generate_map_template.py"
fi

# 測試修正
echo ""
echo -e "${YELLOW}[3/3]${NC} 測試修正..."

cd "$INSTALL_DIR"

# 測試 pysnmp 導入
if python3 -c "from pysnmp.hlapi import bulkCmd; print('bulkCmd imported')" 2>/dev/null; then
    echo "  ✓ pysnmp bulkCmd 可正常導入"
else
    echo -e "  ${RED}✗ pysnmp 導入測試失敗${NC}"
    echo "  請檢查 pysnmp 安裝: pip3 install pysnmp"
fi

# 測試工具
if python3 -c "import sys; sys.path.insert(0, 'tools'); exec(open('tools/generate_map_template.py').read().split('def get_interfaces')[0]); print('Script loads OK')" 2>/dev/null; then
    echo "  ✓ generate_map_template.py 載入正常"
else
    echo -e "  ${YELLOW}⚠ 需要手動檢查 generate_map_template.py${NC}"
fi

echo ""
echo "=========================================="
echo "   修正完成！"
echo "=========================================="
echo ""
echo "備份位置: $BACKUP_DIR"
echo ""
echo "後續測試："
echo "  cd $INSTALL_DIR"
echo "  python3 tools/generate_map_template.py --host <IP> --type <TYPE> --output test.txt"
echo ""
echo "如需還原："
echo "  cp $BACKUP_DIR/*.py $INSTALL_DIR/tools/"
echo "  cp $BACKUP_DIR/snmp_helper.py $INSTALL_DIR/core/"
echo ""
