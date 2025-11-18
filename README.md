# BRAS Map 系統部署指南

## 系統概述

BRAS Map 系統整合 Circuit 資訊管理和流量收集功能，支援多種設備類型的混合環境。

### 支援的設備類型

| 代碼 | 設備類型 | 介面格式 | 特殊處理 |
|-----|---------|---------|---------|
| 1 | MX240 | 三段式 (xe-1/0/0.400) | 標準 timeout |
| 2 | MX960 | 三段式 (ge-0/0/1.100) | 標準 timeout |
| 3 | E320 | 兩段式 (ge-0/0.500) | 延長 timeout (10s) |
| 4 | ACX7024 | 三段式 (ge-0/0/2.200) | 標準 timeout |

### 系統架構

```
BRAS-Map.txt (設備和 Circuit 資訊)
    ↓
bras_map_reader.py (讀取和解析)
    ↓
bras_map_collector.py (資料收集)
    ↓
Traffic Data (流量資料)
    ↓
RRD Files (時間序列資料庫)
```

## 檔案結構

```
project/
├── BRAS-Map.txt                    # Circuit 對應表（主要設定檔）
├── BRAS-Map-Format.md              # 格式規範文件
├── bras_map_reader.py              # BRAS Map 讀取器
├── bras_map_collector.py           # 資料收集器
├── interface_mapping_generator.py  # 介面對照表產生器
├── test_bras_map.py                # 測試套件
└── README.md                       # 本文件
```

## 快速開始

### 1. 環境需求

```bash
# Python 版本
Python 3.7+

# 必要套件
pip install pysnmp mysql-connector-python

# 系統套件
apt-get install snmp snmp-mibs-downloader
```

### 2. BRAS-Map.txt 設定

#### 格式說明

```
bras_hostname,device_type,bras_ip,access_switch_hostname,access_switch_port_even,access_switch_port_singular,circuit_name,trunk_number,area,interface_info,slot,port,vlan,atmf
```

#### 範例資料

**MX240 設備**
```
center_3,1,61.64.214.54,TC7520-0,2,-,Circuit-TC-001,43GD10013,台中交心,xe-1/0/0,1,0,400,1
```

**E320 設備**
```
old_erx_1,3,61.64.191.1,KH-SW-02,6,-,Circuit-KH-001,43GD30001,高雄,ge-0/0,0,0,500,-
```

### 3. 測試系統

```bash
# 執行測試套件
python3 test_bras_map.py

# 預期輸出
✓ 檔案存在: BRAS-Map.txt
✓ 成功載入 12 筆 Circuit 資料
✓ 所有 12 筆 Circuit 的設備類型均有效
✓ 所有介面格式均符合規範
✓ 所有 12 筆 VLAN 值均有效 (1-4094)
✓ 所有 IP 位址格式均有效
✓ 所有完整介面名稱產生正確
✓ ATMF 欄位使用正確
✓ 統計資訊產生成功

✓ 所有測試通過！
```

### 4. 產生介面對照表

```bash
# 產生完整介面對照表
python3 interface_mapping_generator.py

# 輸出檔案
# - interface_mapping.csv (統一格式)
# - interface_mapping_MX240.csv (依設備類型)
# - interface_mapping_MX960.csv
# - interface_mapping_E320.csv
# - interface_mapping_ACX7024.csv
# - interface_mapping_台中交心.csv (依區域)
# - interface_mapping_台北.csv
# - interface_mapping_高雄.csv
```

### 5. 執行資料收集

```bash
# 基本收集（使用預設設定）
python3 bras_map_collector.py

# 指定資料庫連線
python3 bras_map_collector.py --db-host localhost --db-user radius --db-pass password
```

## 詳細設定

### BRAS-Map.txt 欄位說明

| 欄位 | 說明 | 範例 | 必填 |
|-----|------|------|-----|
| bras_hostname | BRAS 主機名稱 | center_3 | 是 |
| device_type | 設備類別 (1/2/3/4) | 1 | 是 |
| bras_ip | BRAS IP 位址 | 61.64.214.54 | 是 |
| access_switch_hostname | 接取交換器名稱 | TC7520-0 | 是 |
| access_switch_port_even | 偶數埠號 | 2 | 是 |
| access_switch_port_singular | 單數埠號 | - | 否 |
| circuit_name | Circuit 名稱 | Circuit-TC-001 | 是 |
| trunk_number | Trunk 編號 | 43GD10013 | 是 |
| area | 區域名稱 | 台中交心 | 是 |
| interface_info | 介面資訊 | xe-1/0/0 或 ge-0/0 | 是 |
| slot | 插槽編號 | 1 | 是 |
| port | 埠號 | 0 | 是 |
| vlan | VLAN ID | 400 | 是 |
| atmf | ATM 框架 (MX/ACX 用) | 1 | E320=否 |

### 介面格式規範

#### E320 格式（兩段式）

```
基本格式: ge-{slot}/{port}
完整介面: ge-{slot}/{port}.{vlan}

範例:
- 基本: ge-0/0
- 完整: ge-0/0.500
```

#### MX/ACX 格式（三段式）

```
基本格式: {type}-{fpc}/{pic}/{port}
完整介面: {type}-{fpc}/{pic}/{port}.{vlan}

介面類型:
- xe: 10 Gigabit Ethernet
- ge: Gigabit Ethernet  
- et: 100 Gigabit Ethernet

範例:
- MX240: xe-1/0/0.400
- MX960: ge-0/0/1.100
- ACX7024: ge-0/0/2.200
```

### 收集器設定

#### SNMP 設定

```python
# 在 bras_map_collector.py 中修改
self.community = 'your_community_string'

# 依設備類型自動調整 timeout
E320: timeout = 10 秒
MX/ACX: timeout = 3 秒
```

#### 資料庫設定

```python
db_config = {
    'host': 'localhost',
    'user': 'radius',
    'password': 'your_password',
    'database': 'radius'
}

collector = BRASMapCollector(
    map_file="BRAS-Map.txt",
    db_config=db_config
)
```

#### 並行處理設定

```python
# 最大並行執行緒數
collector.collect_all_data(max_workers=5)

# 建議設定:
# - 小型環境 (<10 BRAS): max_workers=3
# - 中型環境 (10-30 BRAS): max_workers=5
# - 大型環境 (>30 BRAS): max_workers=10
```

## 整合到現有系統

### 1. 與 Map File 整合

```python
# 從 BRAS Map 產生傳統 Map File
from bras_map_reader import BRASMapReader

reader = BRASMapReader("BRAS-Map.txt")
reader.load()

# 產生 Map File 格式
with open("map_file.txt", "w") as f:
    for circuit in reader.circuits:
        # 格式: user_code,interface,download_upload,phone_or_id
        interface = f"{circuit.slot}_{circuit.port}_{circuit.vpi}_{circuit.vci}"
        download_upload = "61440_20480"  # 從資料庫查詢
        line = f"user_code,{interface},{download_upload},phone_number\n"
        f.write(line)
```

### 2. 與 RRD 系統整合

```python
# 收集資料後更新 RRD
import rrdtool

for data in output_data:
    rrd_file = f"/path/to/rrd/{data['user_code']}.rrd"
    
    # 更新 RRD
    rrdtool.update(
        rrd_file,
        f"N:{data['in_octets']}:{data['out_octets']}"
    )
```

### 3. 與 FreeRADIUS 整合

```python
# 從資料庫查詢 RADIUS 使用者對應
def load_radius_users():
    query = """
        SELECT 
            username,
            CONCAT(slot, '_', port, '_', vpi, '_', vci) as interface,
            download_speed,
            upload_speed
        FROM radcheck
        WHERE attribute = 'User-Profile'
    """
    # 執行查詢並回傳結果
```

## 維護與監控

### 日常檢查

```bash
# 1. 檢查 BRAS Map 格式
python3 test_bras_map.py

# 2. 驗證收集結果
tail -f /var/log/bras_collector.log

# 3. 檢查 RRD 檔案
ls -lh /path/to/rrd/*.rrd | wc -l

# 4. 驗證資料完整性
python3 validate_rrd_data.py
```

### 常見問題

#### Q1: E320 收集逾時

```bash
# 解決方案：調整 timeout 值
# 在 bras_map_collector.py 中:
if device_type == DEVICE_TYPE_E320:
    timeout = 15  # 增加到 15 秒
```

#### Q2: 介面名稱不匹配

```bash
# 檢查 SNMP ifDescr
snmpwalk -v2c -c public <bras_ip> ifDescr

# 比對 BRAS-Map.txt 中的 interface_info
# E320: ge-0/0 格式
# MX/ACX: xe-1/0/0 格式
```

#### Q3: VLAN 對應錯誤

```python
# 驗證 VLAN 對應
reader = BRASMapReader("BRAS-Map.txt")
reader.load()

for circuit in reader.circuits:
    full_interface = circuit.get_full_interface()
    print(f"{circuit.circuit_name}: {full_interface}")
```

## 效能優化

### 收集效能

| 環境規模 | BRAS 數量 | 使用者數 | 建議設定 | 預估時間 |
|---------|----------|---------|---------|---------|
| 小型 | 1-5 | <10,000 | workers=3 | <30s |
| 中型 | 6-15 | 10,000-30,000 | workers=5 | 30-60s |
| 大型 | 16-30 | 30,000-60,000 | workers=10 | 60-90s |

### 記憶體使用

```python
# 大量資料時使用批次處理
def collect_in_batches(bras_list, batch_size=5):
    for i in range(0, len(bras_list), batch_size):
        batch = bras_list[i:i+batch_size]
        # 處理批次
        yield process_batch(batch)
```

## 區域遷移策略

### 三階段遷移

#### 階段 1: 北區遷移

```bash
# 1. 準備 BRAS-Map.txt (只包含北區)
# 2. 測試收集
python3 bras_map_collector.py --area 台北

# 3. 驗證資料
python3 validate_data.py --area 台北

# 4. 切換流量
# 5. 監控 24 小時
```

#### 階段 2: 中區遷移

```bash
# 重複階段 1 流程，針對台中區域
```

#### 階段 3: 南區遷移

```bash
# 重複階段 1 流程，針對高雄區域
```

### 回退計畫

```bash
# 1. 保留舊系統 RRD 檔案
cp -r /old/rrd /backup/rrd_$(date +%Y%m%d)

# 2. 準備切換腳本
./switch_to_old_system.sh

# 3. 驗證舊系統可用性
./verify_old_system.sh
```

## 附錄

### A. 完整範例 BRAS-Map.txt

參見 `BRAS-Map.txt` 檔案。

### B. 測試資料產生

```bash
# 產生測試用 BRAS-Map.txt
python3 generate_test_data.py --bras-count 10 --circuits-per-bras 100
```

### C. 監控指令

```bash
# 即時監控收集狀態
watch -n 1 'tail -20 /var/log/bras_collector.log'

# 檢查 SNMP 連線
for ip in $(awk -F, '{print $3}' BRAS-Map.txt | sort -u); do
    echo -n "$ip: "
    snmpget -v2c -c public $ip sysUpTime.0 >/dev/null 2>&1 && echo "OK" || echo "FAIL"
done
```

### D. 系統需求

| 項目 | 最低需求 | 建議配置 |
|-----|---------|---------|
| CPU | 2 cores | 4 cores |
| RAM | 4GB | 8GB |
| 磁碟 | 100GB | 500GB SSD |
| 網路 | 100Mbps | 1Gbps |

---

**版本**: 1.0  
**最後更新**: 2024年  
**維護者**: Jason (ISP Network Team)
