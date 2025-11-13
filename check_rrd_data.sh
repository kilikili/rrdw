#!/bin/bash
# check_rrd_data.sh - 檢查 RRD 是否有資料

DEVICE_IP="61.64.191.166"
RRD_DIR="data/$DEVICE_IP"

echo "=========================================="
echo "檢查 RRD 資料狀態"
echo "=========================================="
echo ""

# 1. 檢查 RRD 檔案數量
echo "[1] RRD 檔案統計"
echo "----------------------------------------"
rrd_count=$(find "$RRD_DIR" -name "*.rrd" -type f 2>/dev/null | wc -l)
echo "找到 $rrd_count 個 RRD 檔案"
echo ""

# 2. 檢查最近更新時間
echo "[2] 最近更新的 RRD (前 5 個)"
echo "----------------------------------------"
find "$RRD_DIR" -name "*.rrd" -type f -printf "%T@ %p\n" 2>/dev/null | \
    sort -rn | head -5 | while read timestamp filepath; do
    filename=$(basename "$filepath")
    update_time=$(date -d "@${timestamp%.*}" '+%Y-%m-%d %H:%M:%S')
    echo "  $filename"
    echo "    更新時間: $update_time"
done
echo ""

# 3. 檢查 RRD 內容（選一個檔案）
echo "[3] RRD 資料檢查"
echo "----------------------------------------"
sample_rrd=$(find "$RRD_DIR" -name "*.rrd" -type f 2>/dev/null | head -1)

if [ -n "$sample_rrd" ]; then
    echo "範例 RRD: $(basename $sample_rrd)"
    echo ""
    
    # 顯示 RRD info
    echo "RRD 資訊:"
    rrdtool info "$sample_rrd" | grep -E "(step|last_update)"
    echo ""
    
    # 嘗試 fetch 最近資料
    echo "最近的資料點:"
    rrdtool fetch "$sample_rrd" AVERAGE --start -7200 --end now 2>/dev/null | tail -10
    
    # 檢查是否有非 NaN 的資料
    has_data=$(rrdtool fetch "$sample_rrd" AVERAGE --start -7200 --end now 2>/dev/null | \
               grep -v "nan" | grep -E "[0-9]+\.[0-9]+" | wc -l)
    
    echo ""
    if [ $has_data -gt 0 ]; then
        echo "✓ RRD 有 $has_data 個有效資料點"
    else
        echo "⚠️  RRD 目前沒有有效資料（剛建立需要等待下一次更新）"
    fi
fi

echo ""
echo "=========================================="
echo "建議："
echo "=========================================="
echo "1. 如果是剛建立的 RRD，需要等待至少 20 分鐘（1 個 step）"
echo "2. 確認收集器正在運作: crontab -l | grep run_collector_group"
echo "3. 檢查收集器日誌: tail -f /var/log/isp_traffic/group_*_master.log"
echo ""
