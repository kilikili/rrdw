#!/bin/bash
# sync_bras_map.sh - 從 BRAS-Map.txt 自動產生四組設備檔案

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRAS_MAP="$SCRIPT_DIR/BRAS-Map.txt"

echo "=========================================="
echo "BRAS-Map 同步與分組工具"
echo "=========================================="
echo "腳本目錄: $SCRIPT_DIR"
echo "BRAS-Map: $BRAS_MAP"
echo ""

# 檢查 BRAS-Map.txt 是否存在
if [ ! -f "$BRAS_MAP" ]; then
    echo "✗ 找不到 BRAS-Map.txt"
    echo ""
    echo "請將 BRAS-Map.txt 放在: $SCRIPT_DIR"
    echo ""
    echo "或從上傳位置複製:"
    echo "  cp /mnt/user-data/uploads/BRAS-Map.txt $SCRIPT_DIR/"
    exit 1
fi

echo "✓ 找到 BRAS-Map.txt"

# 統計設備數量
total_devices=$(grep -v "^#" "$BRAS_MAP" | grep -v "^[[:space:]]*$" | wc -l)
echo "  總設備數: $total_devices"
echo ""

# 按 IP 統計
echo "設備分布："
grep -v "^#" "$BRAS_MAP" | grep -v "^[[:space:]]*$" | \
    awk '{print $3}' | sort | uniq -c | \
    awk '{printf "  %s: %d 個\n", $2, $1}'
echo ""

# 計算每組應該有多少設備
devices_per_group=$((total_devices / 4))
remainder=$((total_devices % 4))

echo "分組計劃："
echo "  基礎每組: $devices_per_group 個"
echo "  餘數: $remainder 個（分配給前 $remainder 組）"
echo ""

# 讀取所有設備到陣列
mapfile -t all_devices < <(grep -v "^#" "$BRAS_MAP" | grep -v "^[[:space:]]*$")

# 計算各組設備數
group_sizes=()
for i in {0..3}; do
    if [ $i -lt $remainder ]; then
        group_sizes[$i]=$((devices_per_group + 1))
    else
        group_sizes[$i]=$devices_per_group
    fi
done

echo "各組設備數："
for i in {0..3}; do
    group_name=$(echo "A B C D" | cut -d' ' -f$((i+1)))
    echo "  組別 $group_name: ${group_sizes[$i]} 個"
done
echo ""

# 產生各組 TSV 檔案
echo "產生 TSV 檔案..."

current_index=0

for i in {0..3}; do
    group_name=$(echo "A B C D" | cut -d' ' -f$((i+1)))
    tsv_file="$SCRIPT_DIR/devices_${group_name}.tsv"
    
    # 寫入標頭
    cat > "$tsv_file" << EOF
# ISP 流量收集器 - ${group_name} 組設備列表 (${group_sizes[$i]}個)
# 自動從 BRAS-Map.txt 產生，請勿手動編輯
# 產生時間: $(date '+%Y-%m-%d %H:%M:%S')
# 格式: Area	DEVICE_MODEL	IP	CIRCUIT	SLOT	PORT	CIRCUIT_TYPE	BANDWIDTH	IF_ASSIGN
EOF
    
    # 寫入設備資料
    for ((j=0; j<${group_sizes[$i]}; j++)); do
        if [ $current_index -lt $total_devices ]; then
            echo "${all_devices[$current_index]}" >> "$tsv_file"
            ((current_index++))
        fi
    done
    
    echo "  ✓ 產生 devices_${group_name}.tsv (${group_sizes[$i]} 個設備)"
done

echo ""

# 更新 config.ini
echo "更新 config.ini..."

if [ -f "$SCRIPT_DIR/config.ini" ]; then
    # 檢查是否有 [device_files] section
    if grep -q "\[device_files\]" "$SCRIPT_DIR/config.ini"; then
        # 更新現有設定
        sed -i '/\[device_files\]/,/^\[/ {
            /^group_A/c\group_A = devices_A.tsv
            /^group_B/c\group_B = devices_B.tsv
            /^group_C/c\group_C = devices_C.tsv
            /^group_D/c\group_D = devices_D.tsv
        }' "$SCRIPT_DIR/config.ini"
    else
        # 新增 section
        cat >> "$SCRIPT_DIR/config.ini" << EOF

[device_files]
# 設備列表 TSV 檔案（自動從 BRAS-Map.txt 產生）
group_A = devices_A.tsv
group_B = devices_B.tsv
group_C = devices_C.tsv
group_D = devices_D.tsv
EOF
    fi
    echo "  ✓ 更新 config.ini"
else
    echo "  ⚠️  找不到 config.ini"
fi

echo ""

# 驗證產生的檔案
echo "驗證產生的檔案..."
total_in_groups=0

for group in A B C D; do
    if [ -f "$SCRIPT_DIR/devices_${group}.tsv" ]; then
        count=$(grep -v "^#" "$SCRIPT_DIR/devices_${group}.tsv" | grep -v "^[[:space:]]*$" | wc -l)
        echo "  devices_${group}.tsv: $count 個設備"
        total_in_groups=$((total_in_groups + count))
    fi
done

echo ""
echo "總計: $total_in_groups 個設備"

if [ $total_in_groups -eq $total_devices ]; then
    echo "✓ 驗證通過：設備數量一致"
else
    echo "✗ 驗證失敗：設備數量不一致"
    exit 1
fi

echo ""
echo "=========================================="
echo "同步完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "  1. 驗證設備列表: ./manage_devices.sh show"
echo "  2. 測試執行: ./run_collector_group.sh A"
echo "  3. 安裝 crontab"
echo ""
echo "⚠️  注意："
echo "  devices_*.tsv 是自動產生的，請勿手動編輯"
echo "  如需修改設備列表，請編輯 BRAS-Map.txt 後重新執行本腳本"
