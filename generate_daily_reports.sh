#!/bin/bash
# generate_daily_reports.sh
# 每日報表自動產生腳本

set -e

# 設定
SCRIPT_DIR="/opt/rrdw"
REPORT_DIR="/var/reports/daily"
LOG_FILE="/var/log/rrdw/daily_reports.log"
DATE_STR=$(date +%Y%m%d)

# 確保目錄存在
mkdir -p "$REPORT_DIR"
mkdir -p "$(dirname $LOG_FILE)"

# 日誌函數
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=========================================="
log "開始產生每日報表 - $DATE_STR"
log "=========================================="

# 1. TOP100 流量統計（日報）
log "產生 TOP100 日報..."
python3 "$SCRIPT_DIR/traffic_ranking_report.py" \
    --period daily \
    --format all \
    --output-dir "$REPORT_DIR" \
    >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    log "✓ TOP100 日報完成"
else
    log "✗ TOP100 日報失敗"
fi

# 2. Circuit 擁塞分析（最近 3 日）
log "產生 Circuit 擁塞分析..."
python3 "$SCRIPT_DIR/circuit_congestion_analysis.py" \
    --days 3 \
    --format text \
    --output-dir "$REPORT_DIR" \
    >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    log "✓ 擁塞分析完成"
else
    log "✗ 擁塞分析失敗"
fi

log "=========================================="
log "每日報表產生完成"
log "報表目錄: $REPORT_DIR"
log "=========================================="

# 3. 寄送報表（可選）
if [ -f "$SCRIPT_DIR/send_email_report.sh" ]; then
    log "寄送報表..."
    bash "$SCRIPT_DIR/send_email_report.sh" daily "$REPORT_DIR" >> "$LOG_FILE" 2>&1
fi

exit 0
