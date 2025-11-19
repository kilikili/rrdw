# ISP Traffic Monitor - 程式碼相依關係說明

## 系統架構圖

```
┌─────────────────────────────────────────────────────────────┐
│                    collector_dispatcher.py                   │
│                    (主調度程式)                              │
│  - 讀取 BRAS-Map.txt                                        │
│  - 根據 DeviceType 分派收集器                               │
│  - 協調所有收集任務                                         │
└────────────┬────────────────────────────────────────────────┘
             │
             ├─────────┬──────────┬──────────┬──────────┐
             │         │          │          │          │
             ▼         ▼          ▼          ▼          ▼
    ┌────────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
    │collector   │ │collector│ │collector│ │collector│ │collector│
    │_e320.py    │ │_mx240.py│ │_mx960.py│ │_acx7024│ │_base.py│
    │(Type 3)    │ │(Type 2) │ │(Type 1) │ │(Type 4)│ │(基礎類)│
    └────┬───────┘ └────┬────┘ └────┬────┘ └────┬───┘ └────┬───┘
         │              │           │           │          │
         └──────────────┴───────────┴───────────┴──────────┘
                        │
         ┌──────────────┴──────────────┐
         │                             │
         ▼                             ▼
    ┌─────────────────┐       ┌─────────────────┐
    │ lib/            │       │ lib/            │
    │ bras_map_reader │       │ map_file_reader │
    │ .py             │       │ .py             │
    └────────┬────────┘       └────────┬────────┘
             │                         │
             └──────────┬──────────────┘
                        │
         ┌──────────────┴──────────────┬──────────────┐
         │                             │              │
         ▼                             ▼              ▼
    ┌─────────────┐           ┌─────────────┐  ┌─────────────┐
    │ lib/        │           │ lib/        │  │ lib/        │
    │ rrd_helper  │           │ snmp_helper │  │ config      │
    │ .py         │           │ .py         │  │ _loader.py  │
    └─────────────┘           └─────────────┘  └─────────────┘
         │
         ▼
    ┌─────────────────────────────────────────┐
    │  RRD Database (四層架構)                 │
    │  - data/*.rrd            (User層)       │
    │  - data/sum/*.rrd        (Speed層)      │
    │  - data/sum2m/*.rrd      (FUP層)        │
    │  - data/circuit/*.rrd    (Circuit層)    │
    └─────────────────────────────────────────┘
```

## 核心模組說明

### 1. collector_dispatcher.py (主調度程式)

**功能**: 
- 讀取並解析 BRAS-Map.txt
- 根據 DeviceType 自動選擇適當的收集器
- 協調所有收集任務的執行
- 統計收集結果和錯誤

**相依模組**:
- `lib.bras_map_reader`: 讀取 BRAS-Map.txt
- `lib.config_loader`: 載入配置檔案
- `collectors.collector_e320`: E320收集器
- `collectors.collector_mx240`: MX240收集器
- `collectors.collector_mx960`: MX960收集器
- `collectors.collector_acx7024`: ACX7024收集器

**輸入**:
- `config/config.ini`: 配置檔案
- `config/BRAS-Map.txt`: 設備列表

**輸出**:
- 執行結果日誌
- 收集統計資訊

**使用方式**:
```bash
python3 collector_dispatcher.py
```

---

### 2. collector_e320.py (E320收集器)

**功能**:
- 讀取 map_{ip}.txt 取得用戶清單
- 透過SNMP查詢介面流量
- 建立/更新四層RRD檔案
- 支援舊式兩段式介面命名

**相依模組**:
- `collectors.collector_base`: 收集器基礎類別
- `lib.map_file_reader`: 讀取map檔案
- `lib.snmp_helper`: SNMP操作
- `lib.rrd_helper`: RRD操作

**輸入**:
- `config/maps/map_{ip}.txt`: 用戶映射檔
- SNMP介面資料

**輸出**:
- `data/{ip}_{slot}_{port}_{down}_{up}_{vlan}.rrd`
- `data/sum/{ip}_{slot}_{port}_{down}_{up}.rrd`
- `data/sum2m/{ip}_{slot}_{port}.rrd`
- `data/circuit/{ip}_{slot}_{port}_circuit.rrd`

**特殊設定**:
```ini
[device_timeouts]
e320 = 10  # E320設備SNMP超時較長

[device_retries]
e320 = 3   # E320設備SNMP重試次數較多
```

---

### 3. collector_mx240.py (MX240收集器)

**功能**:
- SNMP Bulk Walk取得所有介面
- 支援PPPoE動態介面
- 並行處理多個介面
- 三段式介面命名

**相依模組**:
- `collectors.collector_base`: 收集器基礎類別
- `lib.snmp_helper`: SNMP操作 (Bulk Walk)
- `lib.rrd_helper`: RRD操作
- `concurrent.futures`: 並行處理

**輸入**:
- SNMP介面列表 (動態取得)
- SNMP流量統計

**輸出**:
- 四層RRD檔案

**效能參數**:
```ini
[collection]
mx240_max_workers = 4
mx240_bulk_size = 40
```

---

### 4. collector_mx960.py (MX960收集器)

**功能**:
- 高效能SNMP Bulk Walk
- 大量動態IP用戶支援
- 介面快取機制
- 最大並行處理能力

**相依模組**:
- `collectors.collector_base`: 收集器基礎類別
- `lib.snmp_helper`: SNMP操作 (高效能Bulk Walk)
- `lib.rrd_helper`: RRD操作
- `concurrent.futures`: 並行處理

**輸入**:
- SNMP介面列表 (動態取得並快取)
- SNMP流量統計

**輸出**:
- 四層RRD檔案

**效能參數**:
```ini
[collection]
mx960_max_workers = 8
mx960_bulk_size = 50
mx960_cache_timeout = 300  # 介面快取5分鐘
```

---

### 5. collector_acx7024.py (ACX7024收集器)

**功能**:
- 固定IP服務收集
- 簡化的介面結構
- 靜態介面配置
- 快速SNMP回應

**相依模組**:
- `collectors.collector_base`: 收集器基礎類別
- `lib.snmp_helper`: SNMP操作
- `lib.rrd_helper`: RRD操作

**輸入**:
- SNMP介面列表
- SNMP流量統計

**輸出**:
- 四層RRD檔案

**效能參數**:
```ini
[collection]
acx_max_workers = 4
acx_bulk_size = 100
```

---

## 函式庫模組

### lib/bras_map_reader.py

**功能**: 讀取並解析 BRAS-Map.txt

**主要類別**: `BRASMapReader`

**主要方法**:
```python
def read_map(file_path: str) -> List[Dict]
    # 讀取BRAS-Map.txt並返回設備列表

def get_devices_by_type(device_type: int) -> List[Dict]
    # 根據DeviceType過濾設備

def get_devices_by_area(area: str) -> List[Dict]
    # 根據Area過濾設備
```

**相依**:
- 無外部相依

**被使用於**:
- `collector_dispatcher.py`

---

### lib/map_file_reader.py

**功能**: 讀取並解析 map_{ip}.txt

**主要類別**: `MapFileReader`

**主要方法**:
```python
def read_map(file_path: str) -> List[Dict]
    # 讀取map檔案並返回用戶列表

def parse_line(line: str) -> Dict
    # 解析單行map資料
    # 格式: username,slot_port_vpi_vci,downstream_upstream,user_id

def validate_format(line: str) -> bool
    # 驗證行格式是否正確
```

**格式驗證規則**:
- 使用底線 `_` 分隔，不使用斜線 `/`
- 四個欄位，用逗號分隔
- 第二欄位: `slot_port_vpi_vci` (四個數字)
- 第三欄位: `downstream_upstream` (兩個數字)

**相依**:
- `re` (正規表達式)

**被使用於**:
- `collector_e320.py`

---

### lib/rrd_helper.py

**功能**: RRD檔案操作輔助函數

**主要函數**:
```python
def create_rrd(file_path: str, step: int = 1200) -> bool
    # 建立RRD檔案，預設20分鐘step

def update_rrd(file_path: str, timestamp: int, in_octets: int, out_octets: int) -> bool
    # 更新RRD資料

def fetch_rrd(file_path: str, start: int, end: int) -> Dict
    # 讀取RRD資料

def get_rrd_info(file_path: str) -> Dict
    # 取得RRD檔案資訊
```

**RRD架構定義**:
```python
# 資料來源定義
DS:in:COUNTER:2400:0:U     # 輸入流量 (40分鐘heartbeat)
DS:out:COUNTER:2400:0:U    # 輸出流量 (40分鐘heartbeat)

# 資料保留策略
RRA:AVERAGE:0.5:1:2160     # 20分鐘 x 2160 = 30天
RRA:AVERAGE:0.5:6:4320     # 2小時 x 4320 = 1年
RRA:AVERAGE:0.5:24:1095    # 8小時 x 1095 = 3年
RRA:MAX:0.5:6:4320         # 最大值統計
```

**相依**:
- `rrdtool`

**被使用於**:
- 所有收集器模組

---

### lib/snmp_helper.py

**功能**: SNMP操作輔助函數

**主要函數**:
```python
def snmp_get(ip: str, oid: str, community: str = 'public', timeout: int = 5) -> str
    # SNMP GET操作

def snmp_walk(ip: str, oid: str, community: str = 'public', timeout: int = 5) -> Dict
    # SNMP WALK操作

def snmp_bulk_walk(ip: str, oid: str, community: str = 'public', 
                   timeout: int = 5, max_repetitions: int = 50) -> Dict
    # SNMP BULK WALK操作 (高效能)

def get_interface_list(ip: str, community: str = 'public') -> Dict
    # 取得介面列表 (ifDescr)

def get_interface_stats(ip: str, interface_index: str, 
                        community: str = 'public') -> Tuple[int, int]
    # 取得介面流量統計 (ifHCInOctets, ifHCOutOctets)
```

**SNMP OID定義**:
```python
# 標準IF-MIB OIDs
OID_IF_DESCR = '1.3.6.1.2.1.2.2.1.2'           # 介面描述
OID_IF_HC_IN_OCTETS = '1.3.6.1.2.1.31.1.1.1.6'  # 64位元輸入
OID_IF_HC_OUT_OCTETS = '1.3.6.1.2.1.31.1.1.1.10' # 64位元輸出
```

**相依**:
- `pysnmp`

**被使用於**:
- 所有收集器模組

---

### lib/config_loader.py

**功能**: 載入和管理配置檔案

**主要類別**: `ConfigLoader`

**主要方法**:
```python
def load_config(config_file: str = 'config/config.ini') -> ConfigParser
    # 載入配置檔案

def get_value(section: str, key: str, default=None) -> Any
    # 取得配置值

def get_snmp_params() -> Dict
    # 取得SNMP參數

def get_rrd_params() -> Dict
    # 取得RRD參數

def get_device_timeout(device_type: int) -> int
    # 根據設備類型取得SNMP超時時間
```

**相依**:
- `configparser`

**被使用於**:
- `collector_dispatcher.py`
- 所有收集器模組

---

## 資料流程

### 收集流程圖

```
1. collector_dispatcher.py 啟動
   │
   ├─> 載入 config.ini
   │
   ├─> 讀取 BRAS-Map.txt (使用 bras_map_reader)
   │   │
   │   └─> 解析設備列表
   │       - Area
   │       - DeviceType
   │       - IP
   │       - Circuit Info
   │
   ├─> 按DeviceType分組設備
   │   - Type 1 -> MX960
   │   - Type 2 -> MX240
   │   - Type 3 -> E320
   │   - Type 4 -> ACX7024
   │
   └─> 分派給各收集器
       │
       ├─> E320 Collector (Type 3)
       │   │
       │   ├─> 讀取 map_{ip}.txt (使用 map_file_reader)
       │   │   └─> 解析用戶清單
       │   │       - username
       │   │       - slot_port_vpi_vci
       │   │       - downstream_upstream
       │   │       - user_id
       │   │
       │   ├─> SNMP查詢介面ifindex (使用 snmp_helper)
       │   │
       │   ├─> SNMP查詢流量統計
       │   │   - ifHCInOctets
       │   │   - ifHCOutOctets
       │   │
       │   └─> 更新RRD檔案 (使用 rrd_helper)
       │       ├─> User層: {ip}_{slot}_{port}_{down}_{up}_{vlan}.rrd
       │       ├─> Speed層: sum/{ip}_{slot}_{port}_{down}_{up}.rrd
       │       ├─> FUP層: sum2m/{ip}_{slot}_{port}.rrd
       │       └─> Circuit層: circuit/{ip}_{slot}_{port}_circuit.rrd
       │
       ├─> MX240/MX960/ACX Collector (Type 1, 2, 4)
       │   │
       │   ├─> SNMP Bulk Walk取得介面列表
       │   │
       │   ├─> 過濾有效介面 (PPPoE, 實體介面)
       │   │
       │   ├─> 並行處理多個介面
       │   │   └─> 使用 ThreadPoolExecutor
       │   │
       │   ├─> SNMP查詢流量統計
       │   │
       │   └─> 更新RRD檔案 (四層架構)
       │
       └─> 收集完成
           └─> 統計結果
               - 成功數量
               - 失敗數量
               - 執行時間
```

---

## 相依套件版本需求

### Python標準函式庫
- `configparser`: Python標準函式庫
- `subprocess`: Python標準函式庫
- `re`: Python標準函式庫
- `os`, `sys`, `pathlib`: Python標準函式庫
- `datetime`: Python標準函式庫
- `concurrent.futures`: Python 3.2+
- `logging`: Python標準函式庫

### 外部套件
```
pysnmp>=4.4.0         # SNMP操作
rrdtool               # RRD資料庫操作
pymysql>=0.9.0        # MySQL連線 (可選)
```

### 系統套件
```
rrdtool               # RRD命令列工具
net-snmp-utils        # SNMP命令列工具 (snmpwalk, snmpget)
```

---

## 模組匯入關係

### collector_dispatcher.py
```python
import sys
import os
from pathlib import Path
import configparser
import logging
from typing import List, Dict

# 內部模組
from lib.bras_map_reader import BRASMapReader
from lib.config_loader import ConfigLoader
from collectors.collector_e320 import CollectorE320
from collectors.collector_mx240 import CollectorMX240
from collectors.collector_mx960 import CollectorMX960
from collectors.collector_acx7024 import CollectorACX7024
```

### collector_e320.py
```python
import logging
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor

# 內部模組
from collectors.collector_base import CollectorBase
from lib.map_file_reader import MapFileReader
from lib.snmp_helper import SNMPHelper
from lib.rrd_helper import RRDHelper
```

### collector_mx240.py
```python
import logging
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor

# 內部模組
from collectors.collector_base import CollectorBase
from lib.snmp_helper import SNMPHelper
from lib.rrd_helper import RRDHelper
```

---

## 配置檔案相依

所有模組都依賴 `config/config.ini`，主要區段：

```ini
[base]
root_path = /opt/isp_monitor

[snmp]
default_community = public
timeout = 5
retries = 2
port = 161
version = 2c

[rrd]
base_dir = data
sum_dir = data/sum
sum2m_dir = data/sum2m
circuit_dir = data/circuit
step = 1200

[collection]
fork_threshold = 2000
max_processes = 4

[device_timeouts]
e320 = 10
mx240 = 5
mx960 = 5
acx7024 = 5

[device_retries]
e320 = 3
mx240 = 2
mx960 = 2
acx7024 = 2
```

---

## 檔案系統相依

### 必要目錄
```
/opt/isp_monitor/
├── config/
│   ├── config.ini          (必要)
│   ├── BRAS-Map.txt        (必要)
│   └── maps/               (必要)
│       ├── map_{ip1}.txt
│       ├── map_{ip2}.txt
│       └── ...
├── collectors/             (必要)
├── lib/                    (必要)
├── data/                   (必要，可寫)
│   ├── sum/                (必要，可寫)
│   ├── sum2m/              (必要，可寫)
│   └── circuit/            (必要，可寫)
└── logs/                   (必要，可寫)

/var/log/isp_traffic/       (必要，可寫)
```

---

## 網路相依

### SNMP連線
- 所有監控設備必須允許SNMP查詢 (UDP 161)
- SNMP community必須正確配置
- 網路路由必須可達所有設備IP

### 防火牆規則
```bash
# 允許SNMP查詢
iptables -A OUTPUT -p udp --dport 161 -j ACCEPT
iptables -A INPUT -p udp --sport 161 -j ACCEPT
```

---

## 效能考量

### CPU使用
- 單核心處理: 適用於 <5000 用戶
- 多核心並行: 適用於 >5000 用戶
- 建議設定: `max_processes = CPU核心數 / 2`

### 記憶體使用
- 基礎: ~100MB
- 每10000用戶: ~50MB額外記憶體
- SNMP快取: ~20MB per 設備

### 磁碟I/O
- RRD更新頻率: 每20分鐘
- 每個用戶: 4個RRD檔案
- 磁碟空間估算: 每用戶 ~1MB/年

### 網路頻寬
- SNMP查詢: ~1KB per 用戶 per 收集週期
- 60000用戶: ~60MB per 20分鐘
- 平均: ~50Kbps

---

## 故障恢復機制

### SNMP超時處理
```python
# 自動重試機制
retries = config.get('snmp', 'retries')  # 預設2次
timeout = config.get('snmp', 'timeout')  # 預設5秒

# E320設備特殊處理
if device_type == 3:
    timeout = 10  # 延長至10秒
    retries = 3   # 增加至3次
```

### RRD檔案恢復
```python
# 如果RRD檔案損壞，自動重建
if not rrd_helper.check_rrd(file_path):
    rrd_helper.create_rrd(file_path)
```

### 日誌記錄
```python
# 所有錯誤都會記錄到日誌
logger.error(f"Failed to collect from {ip}: {error}")

# 可透過日誌追蹤問題
tail -f /var/log/isp_traffic/collector.log
```

---

**文件版本**: 2.0.0  
**最後更新**: 2025-11-19
