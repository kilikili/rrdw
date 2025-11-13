#!/bin/bash
# check_collector_status.sh - 檢查收集器狀態
# 用途：即時監控所有收集器的執行狀態

LOCK_DIR="/var/run/isp_collector"
PID_DIR="$LOCK_DIR/pids"
LOG_DIR="/var/log/isp_traffic"

# 顏色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 是否使用顏色（檢測是否為終端）
if [ -t 1 ]; then
    USE_COLOR=1
else
    USE_COLOR=0
fi

# 印出有顏色的文字
print_color() {
    local color=$1
    local text=$2
    
    if [ $USE_COLOR -eq 1 ]; then
        echo -e "${color}${text}${NC}"
    else
        echo "$text"
    fi
}

# ========================================
# 顯示標題
# ========================================
clear
print_color "$BLUE" "=========================================="
print_color "$BLUE" "ISP 流量收集器狀態監控"
print_color "$BLUE" "時間: $(date '+%Y-%m-%d %H:%M:%S')"
print_color "$BLUE" "=========================================="
echo ""

# ========================================
# 檢查 Lock Files（組別執行狀態）
# ========================================
print_color "$YELLOW" "[1] 組別執行狀態"
echo "----------------------------------------"

if [ ! -d "$LOCK_DIR" ]; then
    print_color "$GREEN" "  ✓ Lock 目錄不存在（沒有任何組別在執行）"
else
    lock_files=$(find "$LOCK_DIR" -name "group_*.lock" 2>/dev/null)
    
    if [ -z "$lock_files" ]; then
        print_color "$GREEN" "  ✓ 沒有任何組別在執行"
    else
        while IFS= read -r lock_file; do
            group=$(basename "$lock_file" | sed 's/group_//' | sed 's/.lock//')
            lock_pid=$(cat "$lock_file" 2>/dev/null || echo "unknown")
            
            # 檢查 PID 是否還在執行
            if [ "$lock_pid" != "unknown" ] && kill -0 "$lock_pid" 2>/dev/null; then
                # 計算執行時間
                start_time=$(ps -o lstart= -p "$lock_pid" 2>/dev/null | xargs -I {} date -d "{}" +%s 2>/dev/null || echo "0")
                current_time=$(date +%s)
                elapsed=$((current_time - start_time))
                
                minutes=$((elapsed / 60))
                seconds=$((elapsed % 60))
                
                print_color "$YELLOW" "  ⏳ 組別 $group: 執行中 (PID: $lock_pid, 已執行 ${minutes}m ${seconds}s)"
            else
                print_color "$RED" "  ✗ 組別 $group: Lock file 存在但 process 已結束 (PID: $lock_pid)"
            fi
        done <<< "$lock_files"
    fi
fi

echo ""

# ========================================
# 檢查個別收集器 Process
# ========================================
print_color "$YELLOW" "[2] 收集器 Process 狀態"
echo "----------------------------------------"

collector_processes=$(pgrep -f "isp_traffic_collector")

if [ -z "$collector_processes" ]; then
    print_color "$GREEN" "  ✓ 沒有執行中的收集器 process"
else
    count=$(echo "$collector_processes" | wc -l)
    print_color "$YELLOW" "  發現 $count 個執行中的收集器 process:"
    echo ""
    
    # 顯示詳細資訊
    printf "  %-8s %-8s %-10s %-8s %s\n" "PID" "USER" "TIME" "CPU%" "COMMAND"
    echo "  ----------------------------------------"
    
    while IFS= read -r pid; do
        ps_output=$(ps -o pid=,user=,etime=,pcpu=,args= -p "$pid" 2>/dev/null)
        if [ -n "$ps_output" ]; then
            echo "  $ps_output"
        fi
    done <<< "$collector_processes"
fi

echo ""

# ========================================
# 檢查 PID Files
# ========================================
print_color "$YELLOW" "[3] PID Files 狀態"
echo "----------------------------------------"

if [ ! -d "$PID_DIR" ]; then
    print_color "$GREEN" "  ✓ PID 目錄不存在"
else
    pid_files=$(find "$PID_DIR" -name "*.pid" 2>/dev/null)
    
    if [ -z "$pid_files" ]; then
        print_color "$GREEN" "  ✓ 沒有 PID file"
    else
        count=$(echo "$pid_files" | wc -l)
        print_color "$YELLOW" "  發現 $count 個 PID file"
        
        # 檢查這些 PID 是否還在執行
        active=0
        stale=0
        
        while IFS= read -r pid_file; do
            pid=$(cat "$pid_file" 2>/dev/null || echo "")
            
            if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
                ((active++))
            else
                ((stale++))
            fi
        done <<< "$pid_files"
        
        echo "    活躍: $active"
        echo "    失效: $stale"
        
        if [ $stale -gt 0 ]; then
            print_color "$RED" "    ⚠ 建議執行清理腳本: ./cleanup_collectors.sh"
        fi
    fi
fi

echo ""

# ========================================
# 檢查最近的日誌錯誤
# ========================================
print_color "$YELLOW" "[4] 最近的錯誤日誌"
echo "----------------------------------------"

if [ ! -d "$LOG_DIR" ]; then
    print_color "$GREEN" "  ✓ 日誌目錄不存在"
else
    # 檢查最近 5 分鐘的錯誤
    recent_errors=$(find "$LOG_DIR" -name "*.log" -mmin -5 -type f -exec grep -l "ERROR\|TIMEOUT\|FAIL" {} \; 2>/dev/null)
    
    if [ -z "$recent_errors" ]; then
        print_color "$GREEN" "  ✓ 最近 5 分鐘沒有錯誤"
    else
        count=$(echo "$recent_errors" | wc -l)
        print_color "$RED" "  ✗ 發現 $count 個檔案有錯誤，顯示最近 5 條:"
        echo ""
        
        while IFS= read -r log_file; do
            echo "  檔案: $(basename "$log_file")"
            tail -5 "$log_file" | sed 's/^/    /'
            echo ""
        done <<< "$recent_errors" | head -20
    fi
fi

echo ""

# ========================================
# 系統資源使用狀況
# ========================================
print_color "$YELLOW" "[5] 系統資源使用"
echo "----------------------------------------"

# CPU 使用率
cpu_usage=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
echo "  CPU 使用率: ${cpu_usage}%"

# 記憶體使用率
mem_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
echo "  記憶體使用率: ${mem_usage}%"

# Python process 總數
python_count=$(pgrep -f python | wc -l)
echo "  Python process 數量: $python_count"

# 收集器 process CPU 總和
if [ -n "$collector_processes" ]; then
    total_cpu=$(ps -p $collector_processes -o %cpu= 2>/dev/null | awk '{s+=$1} END {printf "%.1f", s}')
    echo "  收集器 CPU 使用: ${total_cpu}%"
fi

echo ""

# ========================================
# Crontab 狀態
# ========================================
print_color "$YELLOW" "[6] Crontab 排程"
echo "----------------------------------------"

cron_entries=$(crontab -l 2>/dev/null | grep "run_collector_group" | grep -v "^#")

if [ -z "$cron_entries" ]; then
    print_color "$RED" "  ✗ 沒有發現收集器的 crontab 設定"
else
    count=$(echo "$cron_entries" | wc -l)
    echo "  發現 $count 個排程:"
    echo ""
    while IFS= read -r entry; do
        echo "    $entry"
    done <<< "$cron_entries"
fi

echo ""

# ========================================
# 總結和建議
# ========================================
print_color "$BLUE" "=========================================="
print_color "$BLUE" "狀態總結"
print_color "$BLUE" "=========================================="
echo ""

# 判斷整體狀態
has_issues=0

if [ -n "$collector_processes" ]; then
    collector_count=$(echo "$collector_processes" | wc -l)
    if [ $collector_count -gt 20 ]; then
        print_color "$RED" "⚠ 警告: 收集器 process 數量異常 ($collector_count 個)"
        has_issues=1
    fi
fi

if [ -d "$LOCK_DIR" ] && [ -n "$(find "$LOCK_DIR" -name "group_*.lock" 2>/dev/null)" ]; then
    # 檢查是否有 lock file 超過 30 分鐘
    old_locks=$(find "$LOCK_DIR" -name "group_*.lock" -mmin +30 2>/dev/null)
    if [ -n "$old_locks" ]; then
        print_color "$RED" "⚠ 警告: 發現超過 30 分鐘的 lock file"
        has_issues=1
    fi
fi

if [ $has_issues -eq 0 ]; then
    print_color "$GREEN" "✓ 系統狀態正常"
else
    echo ""
    echo "建議動作:"
    echo "  1. 執行清理腳本: ./cleanup_collectors.sh"
    echo "  2. 檢查日誌: tail -100 $LOG_DIR/group_*_master.log"
    echo "  3. 手動測試: ./run_collector_group_fixed.sh A --force"
fi

echo ""

# ========================================
# 互動模式
# ========================================
if [ -t 0 ]; then
    echo "按 Enter 結束，或輸入以下指令："
    echo "  r - 重新整理"
    echo "  c - 執行清理"
    echo "  q - 結束"
    echo ""
    read -n 1 -r action
    
    case "$action" in
        r|R)
            exec "$0"
            ;;
        c|C)
            echo ""
            ./cleanup_collectors.sh
            ;;
        *)
            exit 0
            ;;
    esac
fi
