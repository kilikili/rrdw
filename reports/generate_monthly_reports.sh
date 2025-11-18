#!/bin/bash
# generate_monthly_reports.sh
# 月報自動產生腳本

set -e

SCRIPT_DIR="/opt/rrdw"
REPORT_DIR="/var/reports/monthly"
LOG_FILE="/var/log/rrdw/monthly_reports.log"
DATE_STR=$(date +%Y%m)

mkdir -p "$REPORT_DIR"
mkdir -p "$(dirname $LOG_FILE)"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=========================================="
log "開始產生月報 - $DATE_STR"
log "=========================================="

# 1. TOP100 月報
log "產生 TOP100 月報..."
python3 "$SCRIPT_DIR/traffic_ranking_report.py" \
    --period monthly \
    --format all \
    --output-dir "$REPORT_DIR" \
    >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    log "✓ TOP100 月報完成"
else
    log "✗ TOP100 月報失敗"
fi

# 2. VLAN 數量統計
log "產生 VLAN 數量統計..."
python3 "$SCRIPT_DIR/vlan_statistics.py" \
    --format all \
    --output-dir "$REPORT_DIR" \
    >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    log "✓ VLAN 統計完成"
else
    log "✗ VLAN 統計失敗"
fi

log "=========================================="
log "月報產生完成"
log "=========================================="

exit 0
