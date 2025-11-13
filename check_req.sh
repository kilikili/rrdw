#!/bin/bash
# check_requirements.sh - 檢查系統需求

echo "=========================================="
echo "系統需求檢查"
echo "=========================================="

# 1. 作業系統
echo "[1] 作業系統:"
cat /etc/os-release | grep "PRETTY_NAME"

# 2. Python 版本
echo "[2] Python 版本:"
python3 --version

# 3. 可用磁碟空間
echo "[3] 磁碟空間:"
df -h / /home /var

# 4. 記憶體
echo "[4] 記憶體:"
free -h

# 5. 網路連通性（測試到設備）
echo "[5] 測試 SNMP 連通性:"
ping -c 2 61.64.191.166

echo "=========================================="
