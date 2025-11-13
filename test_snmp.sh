#!/bin/bash
# test_snmp.sh - 測試 SNMP 連線

DEVICE_IP="127.0.0.1"
COMMUNITY="public"

echo "=========================================="
echo "測試 SNMP 連線"
echo "=========================================="

# 1. 測試基本連線
echo "[1] 測試基本 SNMP 連線..."
snmpget -v2c -c $COMMUNITY -t 5 $DEVICE_IP sysDescr.0

if [ $? -ne 0 ]; then
    echo "✗ SNMP 連線失敗"
    echo "請檢查："
    echo "  - 設備 IP 是否正確"
    echo "  - Community string 是否正確"
    echo "  - 防火牆是否阻擋"
    exit 1
fi

echo "✓ SNMP 連線正常"
echo ""

# 2. 測試 snmpwalk（小範圍）
echo "[2] 測試 snmpwalk（ifDescr）..."
time snmpwalk -v2c -c $COMMUNITY -t 5 $DEVICE_IP ifDescr | head -10

echo ""

# 3. 測試 snmpbulkwalk（快速）
echo "[3] 測試 snmpbulkwalk（ifDescr）..."
time snmpbulkwalk -v2c -c $COMMUNITY -t 5 -Cr50 $DEVICE_IP ifDescr | head -10

echo ""

# 4. 測試單一 ifHCOutOctets
echo "[4] 測試單一介面查詢..."
time snmpget -v2c -c $COMMUNITY $DEVICE_IP .1.3.6.1.2.1.31.1.1.1.10.1

echo ""

# 5. 測試 bulk walk ifHCOutOctets（可能很慢）
echo "[5] 測試 bulk walk ifHCOutOctets（計時）..."
echo "（如果超過 30 秒請按 Ctrl+C）"
time timeout 30 snmpbulkwalk -v2c -c $COMMUNITY -t 5 -Cr50 $DEVICE_IP .1.3.6.1.2.1.31.1.1.1.10 | wc -l

echo ""
echo "=========================================="
echo "測試完成"
echo "=========================================="
