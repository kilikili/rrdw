#!/bin/bash
# manage_devices.sh - 管理 TSV 設備列表（更新版）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/config.ini"

# 取得 TSV 檔案路徑
get_tsv_file() {
    local group=$1
    local tsv_file=$(awk -F= -v group="group_${group}" '
        /^\[device_files\]/ { in_section=1; next }
        /^\[/ { in_section=0 }
        in_section && $1 ~ group { 
            gsub(/^[ \t]+|[ \t]+$/, "", $2); 
            print $2; 
            exit 
        }
    ' "$CONFIG_FILE")
    
    if [ -z "$tsv_file" ]; then
        return 1
    fi
    
    # 如果是相對路徑，轉換為絕對路徑
    if [[ "$tsv_file" != /* ]]; then
        tsv_file="$SCRIPT_DIR/$tsv_file"
    fi
    
    echo "$tsv_file"
}

# 顯示設備列表
show_devices() {
    local group=$1
    local tsv_file=$(get_tsv_file "$group")
    
    if [ -z "$tsv_file" ] || [ ! -f "$tsv_file" ]; then
        echo "錯誤: 找不到組別 $group 的設備列表檔案"
        return 1
    fi
    
    echo "=========================================="
    echo "組別 $group 設備列表"
    echo "檔案: $tsv_file"
    echo "=========================================="
    echo ""
    
    # 顯示設備（使用 column 對齊）
    grep -v '^#' "$tsv_file" | column -t -s $'\t'
    
    echo ""
}

# 驗證 TSV 格式
validate_tsv() {
    local group=$1
    local tsv_file=$(get_tsv_file "$group")
    
    if [ -z "$tsv_file" ] || [ ! -f "$tsv_file" ]; then
        echo "錯誤: 找不到組別 $group 的設備列表檔案"
        return 1
    fi
    
    echo "驗證 TSV 檔案: $tsv_file"
    echo ""
    
    local line_num=0
    local error_count=0
    local device_count=0
    
    while IFS=$'\t' read -r area device_model ip circuit slot port circuit_type bandwidth if_assign; do
        ((line_num++))
        
        # 跳過註解和空行
        if [[ "$area" =~ ^#.*$ ]] || [ -z "$area" ]; then
            continue
        fi
        
        # 跳過表頭
        if [ "$area" = "Area" ]; then
            continue
        fi
        
        ((device_count++))
        
        # 驗證 IP
        if ! [[ "$ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
            echo "✗ 第 $line_num 行: 無效的 IP 格式: $ip"
            ((error_count++))
            continue
        fi
        
        # 驗證 Slot 和 Port
        if ! [[ "$slot" =~ ^[0-9]+$ ]] || ! [[ "$port" =~ ^[0-9]+$ ]]; then
            echo "✗ 第 $line_num 行: Slot 或 Port 必須是數字: Slot=$slot, Port=$port"
            ((error_count++))
            continue
        fi
        
        echo "✓ 第 $line_num 行: $ip Slot $slot Port $port ($area - $circuit)"
    done < "$tsv_file"
    
    echo ""
    echo "設備數量: $device_count"
    
    if [ $error_count -eq 0 ]; then
        echo "✓ 驗證通過，沒有錯誤"
    else
        echo "✗ 發現 $error_count 個錯誤"
        return 1
    fi
}

# 主程式
case "$1" in
    show)
        if [ -z "$2" ]; then
            for group in A B C D; do
                show_devices "$group"
                echo ""
            done
        else
            show_devices "$2"
        fi
        ;;
    validate)
        if [ -z "$2" ]; then
            for group in A B C D; do
                validate_tsv "$group"
                echo ""
            done
        else
            validate_tsv "$2"
        fi
        ;;
    *)
        echo "ISP 流量收集器 - TSV 設備管理工具"
        echo ""
        echo "用法:"
        echo "  $0 show [group]      # 顯示設備列表"
        echo "  $0 validate [group]  # 驗證 TSV 格式"
        echo ""
        echo "範例:"
        echo "  $0 show              # 顯示所有組別"
        echo "  $0 show A            # 只顯示 A 組"
        echo "  $0 validate          # 驗證所有 TSV 檔案"
        ;;
esac
