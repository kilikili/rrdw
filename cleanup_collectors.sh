#!/bin/bash
# cleanup_collectors.sh - 清理卡住的收集器 process
# 用途：當收集器無法正常結束時，使用此腳本清理

LOCK_DIR="/var/run/isp_collector"
PID_DIR="$LOCK_DIR/pids"
LOG_DIR="/var/log/isp_traffic"

echo "=========================================="
echo "ISP 收集器清理工具"
echo "時間: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

# ========================================
# 檢查執行中的收集器 process
# ========================================
echo "[1/4] 檢查執行中的 Python 收集器..."
collector_processes=$(pgrep -f "isp_traffic_collector")

if [ -z "$collector_processes" ]; then
    echo "  ✓ 沒有發現執行中的收集器 process"
else
    count=$(echo "$collector_processes" | wc -l)
    echo "  ⚠ 發現 $count 個執行中的收集器 process:"
    echo ""
    
    # 顯示詳細資訊
    ps -f -p $collector_processes 2>/dev/null || true
    echo ""
    
    # 詢問是否終止
    read -p "是否終止這些 process? (y/N): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "  終止 process..."
        for pid in $collector_processes; do
            echo "    終止 PID: $pid"
            kill -TERM "$pid" 2>/dev/null || true
        done
        
        # 等待 5 秒
        sleep 5
        
        # 檢查是否還有存活的
        still_alive=$(pgrep -f "isp_traffic_collector")
        if [ -n "$still_alive" ]; then
            echo "  部分 process 仍在執行，強制終止..."
            for pid in $still_alive; do
                echo "    強制終止 PID: $pid"
                kill -9 "$pid" 2>/dev/null || true
            done
        fi
        
        echo "  ✓ Process 已清理"
    else
        echo "  跳過終止 process"
    fi
fi

echo ""

# ========================================
# 清理 Lock Files
# ========================================
echo "[2/4] 清理 Lock Files..."

if [ ! -d "$LOCK_DIR" ]; then
    echo "  ✓ Lock 目錄不存在，無需清理"
else
    lock_files=$(find "$LOCK_DIR" -name "group_*.lock" 2>/dev/null)
    
    if [ -z "$lock_files" ]; then
        echo "  ✓ 沒有發現 lock file"
    else
        count=$(echo "$lock_files" | wc -l)
        echo "  ⚠ 發現 $count 個 lock file:"
        
        while IFS= read -r lock_file; do
            lock_pid=$(cat "$lock_file" 2>/dev/null || echo "unknown")
            
            # 檢查 PID 是否還在執行
            if [ "$lock_pid" != "unknown" ] && kill -0 "$lock_pid" 2>/dev/null; then
                echo "    $lock_file (PID: $lock_pid, 執行中)"
            else
                echo "    $lock_file (PID: $lock_pid, 已失效)"
                rm -f "$lock_file"
                echo "      ✓ 已移除"
            fi
        done <<< "$lock_files"
    fi
fi

echo ""

# ========================================
# 清理 PID Files
# ========================================
echo "[3/4] 清理 PID Files..."

if [ ! -d "$PID_DIR" ]; then
    echo "  ✓ PID 目錄不存在，無需清理"
else
    pid_files=$(find "$PID_DIR" -name "*.pid" 2>/dev/null)
    
    if [ -z "$pid_files" ]; then
        echo "  ✓ 沒有發現 PID file"
    else
        count=$(echo "$pid_files" | wc -l)
        echo "  ⚠ 發現 $count 個 PID file，清理中..."
        
        rm -f "$PID_DIR"/*.pid
        echo "  ✓ 已清理"
    fi
fi

echo ""

# ========================================
# 檢查殭屍 Process
# ========================================
echo "[4/4] 檢查殭屍 process..."

zombie_processes=$(ps aux | awk '$8=="Z" {print $0}')

if [ -z "$zombie_processes" ]; then
    echo "  ✓ 沒有發現殭屍 process"
else
    echo "  ⚠ 發現殭屍 process:"
    echo ""
    echo "$zombie_processes"
    echo ""
    echo "  提示: 殭屍 process 通常會在其父 process 結束後自動清理"
    echo "        如果持續存在，請考慮重啟相關服務"
fi

echo ""
echo "=========================================="
echo "清理完成"
echo "=========================================="
echo ""

# ========================================
# 提供建議
# ========================================
echo "後續建議:"
echo ""
echo "1. 檢查最近的日誌："
echo "   tail -100 $LOG_DIR/group_*_master.log"
echo ""
echo "2. 手動執行收集器測試："
echo "   ./run_collector_group_fixed.sh A"
echo ""
echo "3. 如果問題持續，檢查 crontab："
echo "   crontab -l"
echo ""
echo "4. 監控系統資源："
echo "   top -u root | grep python"
echo ""
