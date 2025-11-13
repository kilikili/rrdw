#!/bin/bash
# run_collector_group_fixed.sh - 改良版主控腳本
# 修正問題：
# 1. 加入 lock file 防止重複執行
# 2. 加入 timeout 機制
# 3. 改善 process 清理
# 4. 加入 process 監控

set -e  # 遇到錯誤立即停止

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/config.ini"
COLLECTOR_SCRIPT="$SCRIPT_DIR/isp_traffic_collector_final.py"
LOG_DIR="/var/log/isp_traffic"
LOCK_DIR="/var/run/isp_collector"
PID_DIR="$LOCK_DIR/pids"

# 預設 timeout (秒) - 每個收集器最多執行時間
COLLECTOR_TIMEOUT=300  # 5 分鐘

# ========================================
# 顯示用法
# ========================================
if [ -z "$1" ]; then
    echo "用法: $0 <A|B|C|D> [--force] [--timeout=SECONDS]"
    echo ""
    echo "選項:"
    echo "  --force              強制執行（忽略 lock file）"
    echo "  --timeout=SECONDS    設定 timeout（預設: 300 秒）"
    echo ""
    echo "範例:"
    echo "  $0 A                 # 執行 A 組設備"
    echo "  $0 A --force         # 強制執行 A 組"
    echo "  $0 A --timeout=600   # 設定 timeout 為 10 分鐘"
    exit 1
fi

GROUP=$1
FORCE_RUN=0

# 解析參數
shift
while [ $# -gt 0 ]; do
    case "$1" in
        --force)
            FORCE_RUN=1
            ;;
        --timeout=*)
            COLLECTOR_TIMEOUT="${1#*=}"
            ;;
        *)
            echo "未知參數: $1"
            exit 1
            ;;
    esac
    shift
done

# ========================================
# 建立必要目錄
# ========================================
mkdir -p "$LOG_DIR"
mkdir -p "$LOCK_DIR"
mkdir -p "$PID_DIR"

# ========================================
# Lock File 管理
# ========================================
LOCK_FILE="$LOCK_DIR/group_${GROUP}.lock"

# 清理函數（在腳本結束時執行）
cleanup() {
    local exit_code=$?
    echo ""
    echo "=========================================="
    echo "清理中..."
    echo "=========================================="
    
    # 終止所有子 process
    if [ ${#pids[@]} -gt 0 ]; then
        echo "終止所有收集器 process..."
        for pid in "${pids[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                echo "  終止 PID: $pid"
                kill -TERM "$pid" 2>/dev/null || true
            fi
        done
        
        # 等待 3 秒讓 process 正常結束
        sleep 3
        
        # 強制終止還在執行的 process
        for pid in "${pids[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                echo "  強制終止 PID: $pid"
                kill -9 "$pid" 2>/dev/null || true
            fi
        done
    fi
    
    # 清理 PID 檔案
    rm -f "$PID_DIR"/group_${GROUP}_*.pid
    
    # 移除 lock file
    if [ -f "$LOCK_FILE" ]; then
        lock_pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
        if [ "$lock_pid" = "$$" ]; then
            rm -f "$LOCK_FILE"
            echo "Lock file 已移除"
        fi
    fi
    
    echo "清理完成"
    exit $exit_code
}

# 註冊清理函數
trap cleanup EXIT INT TERM

# 檢查是否已有 instance 在執行
if [ -f "$LOCK_FILE" ] && [ $FORCE_RUN -eq 0 ]; then
    lock_pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
    if [ -n "$lock_pid" ] && kill -0 "$lock_pid" 2>/dev/null; then
        echo "錯誤: 組別 $GROUP 已在執行中 (PID: $lock_pid)"
        echo "如果確定沒有在執行，請使用 --force 參數"
        exit 1
    else
        echo "警告: 發現過期的 lock file，將清除"
        rm -f "$LOCK_FILE"
    fi
fi

# 建立 lock file
echo "$$" > "$LOCK_FILE"

# ========================================
# 檢查必要檔案
# ========================================
if [ ! -f "$CONFIG_FILE" ]; then
    echo "錯誤: 找不到設定檔 $CONFIG_FILE"
    exit 1
fi

if [ ! -f "$COLLECTOR_SCRIPT" ]; then
    echo "錯誤: 找不到收集器腳本 $COLLECTOR_SCRIPT"
    exit 1
fi

# ========================================
# 讀取設定
# ========================================
TSV_FILE=$(awk -F= -v group="group_${GROUP}" '
    /^\[device_files\]/ { in_section=1; next }
    /^\[/ { in_section=0 }
    in_section && $1 ~ group { 
        gsub(/^[ \t]+|[ \t]+$/, "", $2); 
        print $2; 
        exit 
    }
' "$CONFIG_FILE")

if [ -z "$TSV_FILE" ]; then
    echo "錯誤: 在設定檔中找不到組別 $GROUP 的設備列表設定"
    exit 1
fi

# 如果是相對路徑，轉換為絕對路徑
if [[ "$TSV_FILE" != /* ]]; then
    TSV_FILE="$SCRIPT_DIR/$TSV_FILE"
fi

if [ ! -f "$TSV_FILE" ]; then
    echo "錯誤: 找不到設備列表檔案 $TSV_FILE"
    exit 1
fi

# 讀取 SNMP community
DEFAULT_COMMUNITY=$(awk -F= '/^\[snmp\]/,/^\[/ { if ($1 ~ /^default_community/) { gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2 } }' "$CONFIG_FILE")
if [ -z "$DEFAULT_COMMUNITY" ]; then
    DEFAULT_COMMUNITY="public"
fi

# ========================================
# 顯示開始資訊
# ========================================
echo "=========================================="
echo "ISP 流量收集器 - 組別 $GROUP"
echo "開始時間: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo "設定檔: $CONFIG_FILE"
echo "設備列表: $TSV_FILE"
echo "收集器: $COLLECTOR_SCRIPT"
echo "Timeout: $COLLECTOR_TIMEOUT 秒"
echo "Lock File: $LOCK_FILE"
echo "PID: $$"
echo ""

# ========================================
# 讀取設備列表
# ========================================
devices=$(grep -v '^#' "$TSV_FILE" | grep -v '^[[:space:]]*$' | tail -n +2)

if [ -z "$devices" ]; then
    echo "錯誤: TSV 檔案中沒有設備資料"
    exit 1
fi

device_count=$(echo "$devices" | wc -l)
echo "找到 $device_count 個設備"
echo ""

# ========================================
# 啟動收集器
# ========================================
pids=()
pid_info=()  # 儲存 PID 和對應的設備資訊
device_num=0
start_time=$(date +%s)

while IFS=$'\t' read -r area device_model ip circuit slot port circuit_type bandwidth if_assign; do
    ((device_num++))
    
    # 清理空白
    ip=$(echo "$ip" | xargs)
    slot=$(echo "$slot" | xargs)
    port=$(echo "$port" | xargs)
    circuit=$(echo "$circuit" | xargs)
    area=$(echo "$area" | xargs)
    
    # 跳過空行
    if [ -z "$ip" ]; then
        continue
    fi
    
    # 產生日誌檔名
    ip_short=$(echo "$ip" | awk -F'.' '{print $4}')
    log_file="$LOG_DIR/collector_${ip_short}_${slot}_${port}.log"
    pid_file="$PID_DIR/group_${GROUP}_${ip_short}_${slot}_${port}.pid"
    
    # 顯示資訊
    echo "[$device_num/$device_count] 啟動: $ip Slot $slot Port $port ($area - $circuit)"
    
    # 背景執行收集器
    (
        # 寫入 PID 檔案
        echo $$ > "$pid_file"
        
        # 執行收集器（加上 timeout）
        timeout "$COLLECTOR_TIMEOUT" python3 "$COLLECTOR_SCRIPT" \
            "$ip" "$slot" "$port" "$area" "$DEFAULT_COMMUNITY" \
            >> "$log_file" 2>&1
        
        exit_code=$?
        
        # 清除 PID 檔案
        rm -f "$pid_file"
        
        # 檢查 timeout
        if [ $exit_code -eq 124 ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] TIMEOUT: $ip Slot $slot Port $port" >> "$log_file"
        fi
        
        exit $exit_code
    ) &
    
    collector_pid=$!
    pids+=($collector_pid)
    pid_info+=("$collector_pid:$ip:$slot:$port")
    
    # 輕微延遲避免同時啟動太多 process
    sleep 0.1
done <<< "$devices"

echo ""
echo "所有收集任務已啟動 (${#pids[@]} 個 process)，等待完成..."
echo "Master PID: $$"
echo "Timeout: $COLLECTOR_TIMEOUT 秒"
echo ""

# ========================================
# 監控 Process 執行狀態
# ========================================
completed=0
failed=0
timeout_count=0
total=${#pids[@]}

# 每 5 秒檢查一次 process 狀態
while [ $completed -lt $total ]; do
    sleep 5
    
    current_time=$(date +%s)
    elapsed=$((current_time - start_time))
    
    temp_completed=0
    temp_failed=0
    running=0
    
    for i in "${!pids[@]}"; do
        pid=${pids[$i]}
        
        if [ -z "$pid" ]; then
            continue
        fi
        
        # 檢查 process 是否還在執行
        if kill -0 "$pid" 2>/dev/null; then
            ((running++))
        else
            # Process 已結束，檢查 exit code
            wait "$pid" 2>/dev/null
            exit_code=$?
            
            if [ $exit_code -eq 0 ]; then
                ((temp_completed++))
            elif [ $exit_code -eq 124 ]; then
                ((temp_failed++))
                ((timeout_count++))
            else
                ((temp_failed++))
            fi
            
            # 清除已完成的 PID
            pids[$i]=""
        fi
    done
    
    completed=$temp_completed
    failed=$temp_failed
    
    # 顯示進度
    echo "[$(date '+%H:%M:%S')] 進度: 完成 $completed | 失敗 $failed | 執行中 $running | 總計 $total | 經過時間 ${elapsed}s"
done

# ========================================
# 最終結果
# ========================================
end_time=$(date +%s)
total_time=$((end_time - start_time))

echo ""
echo "=========================================="
echo "收集完成"
echo "=========================================="
echo "完成時間: $(date '+%Y-%m-%d %H:%M:%S')"
echo "總執行時間: $total_time 秒"
echo ""
echo "結果統計:"
echo "  ✓ 成功: $completed"
echo "  ✗ 失敗: $failed"
echo "  ⏱ Timeout: $timeout_count"
echo "  總計: $total"
echo ""

# 檢查是否有 PID 檔案殘留
remaining_pids=$(find "$PID_DIR" -name "group_${GROUP}_*.pid" 2>/dev/null | wc -l)
if [ $remaining_pids -gt 0 ]; then
    echo "警告: 發現 $remaining_pids 個殘留的 PID 檔案，正在清理..."
    rm -f "$PID_DIR"/group_${GROUP}_*.pid
fi

if [ $failed -gt 0 ]; then
    echo ""
    echo "⚠ 部分收集失敗，請檢查日誌: $LOG_DIR"
    exit 1
fi

echo "✓ 所有設備收集成功"
exit 0
