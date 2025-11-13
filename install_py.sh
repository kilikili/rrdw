#!/bin/bash
# install_python_packages.sh - 安裝 Python 套件

set -e

echo "=========================================="
echo "安裝 Python 套件"
echo "=========================================="

# 安裝 pip 和開發工具
echo "[1/3] 安裝 pip..."
sudo apt install -y \
    python3-pip \
    python3-dev \
    build-essential

# 升級 pip
echo "[2/3] 升級 pip..."
pip3 install --upgrade pip

# 安裝必要的 Python 套件
echo "[3/3] 安裝 Python 套件..."
pip3 install --break-system-packages \
    mysql-connector-python==8.1.0 \
    pysnmp==4.4.12 \
    pyasn1==0.5.0 \
    rrdtool

# 驗證安裝
echo ""
echo "驗證 Python 套件:"
python3 << 'EOF'
try:
    import mysql.connector
    print("✓ mysql-connector-python")
    
    import pysnmp
    print("✓ pysnmp")
    
    import rrdtool
    print("✓ rrdtool")
    
    print("\n所有 Python 套件安裝成功！")
except ImportError as e:
    print(f"✗ 錯誤: {e}")
    exit(1)
EOF

echo "=========================================="
