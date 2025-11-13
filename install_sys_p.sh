#!/bin/bash
# install_system_packages.sh - 安裝系統套件

set -e

echo "=========================================="
echo "安裝系統套件"
echo "=========================================="

# 更新套件列表
echo "[1/6] 更新套件列表..."
sudo apt update

# 安裝基本工具
echo "[2/6] 安裝基本工具..."
sudo apt install -y \
    vim \
    curl \
    wget \
    git \
    net-tools \
    htop \
    screen

# 安裝 MySQL Client（如果本機沒有 MySQL Server）
echo "[3/6] 安裝 MySQL Client..."
sudo apt install -y mysql-client

# 安裝 SNMP 工具
echo "[4/6] 安裝 SNMP 工具..."
sudo apt install -y \
    snmp \
    snmp-mibs-downloader \
    libsnmp-dev

# 設定 SNMP MIBs
echo "[5/6] 設定 SNMP MIBs..."
sudo sed -i 's/mibs :/# mibs :/' /etc/snmp/snmp.conf

# 安裝 RRDtool
echo "[6/6] 安裝 RRDtool..."
sudo apt install -y \
    rrdtool \
    librrd-dev

echo "✓ 系統套件安裝完成"
echo "=========================================="
