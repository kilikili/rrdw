#!/bin/bash
# test_final.sh

DEVICE_IP="61.64.191.166"
SLOT=1
PORT=2

echo "測試 Python 最終版本"

# 執行收集
python3 isp_traffic_collector_final.py $DEVICE_IP $SLOT $PORT

# 檢查個別 RRD
echo "檢查個別 RRD:"
ls -lh ~/bulks_data/$DEVICE_IP/*_${SLOT}_${PORT}_*_sum.rrd | head -5

# 檢查 Sum RRD
echo "檢查 Sum RRD:"
ls -lh ~/bulks_data/sum/$DEVICE_IP/*_${SLOT}_${PORT}_*_sum.rrd

echo "檢查 Sum2M RRD:"
ls -lh ~/bulks_data/sum2m/$DEVICE_IP/*_${SLOT}_${PORT}_*_sum.rrd

# 比對資料
echo "讀取 Sum RRD 最近資料:"
rrdtool fetch /home/bulks_data/sum/$DEVICE_IP/${DEVICE_IP}_${SLOT}_${PORT}_307200_102400_sum.rrd AVERAGE --start -1h | tail -5

# 檢查超標記錄
echo "檢查超標記錄:"
tail -20 /var/log/ob_log.txt
