#!/bin/bash
# quick_test_e320.sh - E320 快速測試
# 使用方法: ./quick_test_e320.sh <IP> <slot> <port> [community]

IP=${1:-"127.0.0.1"}
SLOT=${2:-"1"}
PORT=${3:-"0"}
COMMUNITY=${4:-"public"}

echo "測試 E320 收集器..."
echo "設備: $IP, Slot: $SLOT, Port: $PORT"
echo ""

# 建立臨時 config
cat > /tmp/test_config.ini << EOF
[snmp]
default_community = $COMMUNITY
timeout = 15
retries = 2

[rrd]
base_dir = /tmp/test_rrd

[logging]
log_level = INFO
EOF

mkdir -p /tmp/test_rrd

# 執行收集器
#cd /tmp
python3 "$(dirname "$0")/isp_traffic_collector_final.py" "$IP" "$SLOT" "$PORT" "測試" "$COMMUNITY"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✓ 測試成功！"
    echo ""
    echo "RRD 檔案："
    ls -lh /tmp/test_rrd/*.rrd 2>/dev/null || echo "無 RRD 檔案"
    
    RRD_FILE="/tmp/test_rrd/${IP##*.}_${SLOT}_${PORT}.rrd"
    if [ -f "$RRD_FILE" ]; then
        echo ""
        echo "RRD 內容："
        rrdtool lastupdate "$RRD_FILE"
    fi
else
    echo ""
    echo "✗ 測試失敗 (退出碼: $EXIT_CODE)"
    echo ""
    echo "請檢查："
    echo "1. IP 位址是否正確"
    echo "2. SNMP community 是否正確"
    echo "3. Slot/Port 編號是否正確"
fi

exit $EXIT_CODE
