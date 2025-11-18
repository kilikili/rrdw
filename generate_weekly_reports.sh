#!/bin/bash
# generate_weekly_reports.sh
# 週報自動產生腳本

set -e

SCRIPT_DIR="/opt/rrdw"
REPORT_DIR="/var/reports/weekly"
LOG_FILE="/var/log/rrdw/weekly_reports.log"
DATE_STR=$(date +%Y%m%d)

mkdir -p "$REPORT_DIR"
mkdir -p "$(dirname $LOG_FILE)"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=========================================="
log "開始產生週報 - $DATE_STR"
log "=========================================="

# TOP100 週報
log "產生 TOP100 週報..."
python3 "$SCRIPT_DIR/traffic_ranking_report.py" \
    --period weekly \
    --format all \
    --output-dir "$REPORT_DIR" \
    >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    log "✓ TOP100 週報完成"
else
    log "✗ TOP100 週報失敗"
fi

log "=========================================="
log "週報產生完成"
log "=========================================="

exit 0
