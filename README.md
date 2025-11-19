# RRDW Traffic Collection System

## 系統概述

RRDW (RRD Wrapper) 是一個用於 ISP 流量監控的完整系統，支援多種 Juniper 設備（E320、MX240、MX960、ACX7024）的流量數據收集與 RRD 數據庫管理。

### 核心功能
- **多設備支援**: E320、MX240、MX960、ACX7024
- **四層 RRD 架構**: User Layer → Sum Layer → Sum2m Layer → Circuit Layer
- **自動化調度**: 基於 BRAS-Map 的智能設備識別與收集器調度
- **效能優化**: SNMP bulk walking、並行處理、介面快取
- **完整統計**: TOP100 排名、電路壅塞分析、I/O 統計、速率分類

### 服務用戶規模
- 總用戶數: 約 60,000 用戶
- 部署區域: 北區、中區、南區
- 收集週期: 每 20 分鐘
- 資料保留: 6 個月至 3 年

## 系統架構

### 目錄結構
```
/opt/isp_monitor/
├── config/
│   ├── config.ini              # 主要配置檔案
│   ├── BRAS-Map.txt           # BRAS 設備映射檔案
│   └── maps/                  # 設備用戶映射目錄
│       ├── map_61.64.191.74.txt
│       ├── map_61.64.191.76.txt
│       └── ...
├── collectors/
│   ├── collector_e320.py      # E320 收集器
│   ├── collector_mx240.py     # MX240 收集器 (PPPoE)
│   ├── collector_mx960.py     # MX960 收集器 (Dynamic IP)
│   └── collector_acx7024.py   # ACX7024 收集器 (Fixed IP)
├── core/
│   ├── rrd_manager.py         # RRD 管理核心
│   ├── snmp_helper.py         # SNMP 工具函式
│   └── config_loader.py       # 配置載入器
├── orchestrator/
│   └── dispatcher.py          # 主要調度器
├── data/
│   ├── user/                  # 個別用戶 RRD (VLAN tracking)
│   ├── sum/                   # 速率檔次彙總 RRD
│   ├── sum2m/                 # FUP 層 RRD
│   └── circuit/               # 電路統計 RRD
├── logs/
│   └── collector.log
└── reports/
    ├── daily/
    ├── weekly/
    └── monthly/
```

### 四層 RRD 架構

#### Layer 1: User Layer (個別用戶層)
- **路徑**: `data/user/{username}.rrd`
- **用途**: VLAN 級別用戶追蹤
- **更新週期**: 20 分鐘
- **保留期限**: 6 個月

#### Layer 2: Sum Layer (速率檔次彙總層)
- **路徑**: `data/sum/{device_ip}_{bandwidth}.rrd`
- **範例**: `data/sum/61.64.191.74_102400_40960.rrd`
- **用途**: 相同速率檔次用戶的流量彙總
- **格式**: 使用底線分隔 (下載_上傳)

#### Layer 3: Sum2m Layer (FUP 層)
- **路徑**: `data/sum2m/{device_ip}.rrd`
- **用途**: Fair Usage Policy 實作，2Mbps 上限控管
- **保留期限**: 3 年

#### Layer 4: Circuit Layer (電路統計層)
- **路徑**: `data/circuit/{circuit_id}.rrd`
- **用途**: 電路級別彙總統計
- **應用**: 電路壅塞分析、容量規劃

## 設備類型與收集器

### DeviceType 編碼
```
1 = E320 (Legacy BRAS)
2 = MX960 (Dynamic IP, High Capacity)
3 = MX240 (Dynamic IP with PPPoE)
4 = ACX7024 (Fixed IP Services)
```

### 收集器特性對照表

| 設備 | DeviceType | IP類型 | 認證方式 | SNMP超時 | 特殊需求 |
|------|-----------|--------|----------|----------|---------|
| E320 | 1 | Dynamic | PPPoE | 10s | 舊版介面格式 |
| MX960 | 2 | Dynamic | PPPoE | 5s | 高容量處理 |
| MX240 | 3 | Dynamic | PPPoE | 5s | PPPoE 支援 |
| ACX7024 | 4 | Fixed | - | 5s | 固定 IP 服務 |

## 配置檔案格式

### 1. BRAS-Map.txt (主映射檔案)
```
Area	DeviceType	IP	CircuitID	Slot(Fpc)	Port	InterfaceType	BandwidthMax	IfAssign	Pic
taipei_4	3	61.64.191.74	223GD99004	1	0	GE	880	0	0
taipei_5	2	61.64.191.76	223GD99018	1	1	XE	880	0	0
south_1	1	61.64.191.78	223GD99019	1	2	XE	880	0	2
center_1	4	61.64.191.80	223GD99020	0	0	XE	880	0	0
```

**欄位說明**:
- **Area**: 區域代碼 (taipei_4, south_1, center_1)
- **DeviceType**: 設備類型代碼 (1-4)
- **IP**: 設備管理 IP
- **CircuitID**: 電路識別碼
- **Slot(Fpc)**: FPC 插槽編號
- **Port**: 埠號
- **InterfaceType**: 介面類型 (GE/XE)
- **BandwidthMax**: 最大頻寬 (Mbps)
- **IfAssign**: 介面指派旗標
- **Pic**: PIC 編號

### 2. map_{ip}.txt (設備用戶映射)
```
0989703334,1_2_0_3490,35840_6144,587247394
0981345344,3_1_0_3441,102400_40960,587272279
0931437368,2_3_0_3780,102400_40960,587208636
shinyi64518,3_1_0_57,5120_384,587269635
```

**格式**: `UserID,Slot_Port_VPI_VCI,Bandwidth_Down_Up,AccountID`

**重要**: 
- 介面位置使用 **底線** 分隔: `1_2_0_3490`
- 頻寬速率使用 **底線** 分隔: `35840_6144` (下載_上傳, bps)
- 第四欄位為電話號碼或用戶 ID，**不是** email

### 3. config.ini (系統配置)
```ini
[base]
root_path = /opt/isp_monitor/

[database]
enabled = false
host = localhost
port = 3306

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

[logging]
log_dir = logs
log_level = INFO

[paths]
map_file_dir = config/maps
bras_map_file = config/BRAS-Map.txt
```

## 安裝部署

### 系統需求
- **作業系統**: CentOS 7/8 或 Ubuntu 20.04+
- **Python**: 3.6+
- **必要套件**: pysnmp, rrdtool, python-rrdtool

### 安裝步驟

#### 1. 安裝系統套件
```bash
# CentOS
sudo yum install -y rrdtool rrdtool-python python3 python3-pip

# Ubuntu
sudo apt-get update
sudo apt-get install -y rrdtool python3 python3-pip
```

#### 2. 安裝 Python 套件
```bash
pip3 install pysnmp pysnmp-mibs configparser
```

#### 3. 建立系統目錄
```bash
sudo mkdir -p /opt/isp_monitor/{config/maps,collectors,core,orchestrator,data/{user,sum,sum2m,circuit},logs,reports}
sudo chown -R $(whoami):$(whoami) /opt/isp_monitor
```

#### 4. 部署配置檔案
```bash
cd /opt/isp_monitor
cp config.ini.example config/config.ini
cp BRAS-Map.txt.example config/BRAS-Map.txt

# 編輯配置檔案
vim config/config.ini
vim config/BRAS-Map.txt
```

#### 5. 設定排程 (Cron)
```bash
# 每 20 分鐘執行一次收集
crontab -e

# 加入以下內容
*/20 * * * * cd /opt/isp_monitor && python3 orchestrator/dispatcher.py >> logs/cron.log 2>&1
```

## 使用指南

### 手動執行收集器

#### 1. 測試單一設備
```bash
# E320 設備
python3 collectors/collector_e320.py --ip 61.64.191.78 --map config/maps/map_61.64.191.78.txt

# MX960 設備
python3 collectors/collector_mx960.py --ip 61.64.191.76 --map config/maps/map_61.64.191.76.txt

# MX240 設備
python3 collectors/collector_mx240.py --ip 61.64.191.74 --map config/maps/map_61.64.191.74.txt

# ACX7024 設備
python3 collectors/collector_acx7024.py --ip 61.64.191.80 --map config/maps/map_61.64.191.80.txt
```

#### 2. 執行完整收集流程
```bash
# 使用調度器自動識別所有設備
python3 orchestrator/dispatcher.py

# 指定特定區域
python3 orchestrator/dispatcher.py --area taipei

# 乾跑模式（不實際收集）
python3 orchestrator/dispatcher.py --dry-run
```

### 驗證數據收集

#### 1. 檢查 RRD 檔案
```bash
# 查看用戶 RRD
rrdtool info data/user/0989703334.rrd

# 查看最新數據
rrdtool lastupdate data/user/0989703334.rrd

# 產生測試圖表
rrdtool graph test.png \
  DEF:inbound=data/user/0989703334.rrd:inbound:AVERAGE \
  LINE1:inbound#00FF00:"Inbound Traffic"
```

#### 2. 查看日誌
```bash
# 即時監控
tail -f logs/collector.log

# 搜尋錯誤
grep ERROR logs/collector.log

# 統計收集狀況
grep "Collection completed" logs/collector.log | wc -l
```

## 程式碼相依關係

### 核心模組依賴圖
```
dispatcher.py (Orchestrator)
    ├── config_loader.py (讀取 BRAS-Map.txt & config.ini)
    ├── collector_e320.py
    ├── collector_mx240.py
    ├── collector_mx960.py
    └── collector_acx7024.py
            ├── snmp_helper.py (SNMP 查詢工具)
            └── rrd_manager.py (RRD 檔案操作)
```

### 各收集器共用組件
```python
# 所有收集器共用
from core.snmp_helper import SNMPHelper
from core.rrd_manager import RRDManager
from core.config_loader import ConfigLoader

# SNMP OIDs (IF-MIB)
ifHCInOctets = '1.3.6.1.2.1.31.1.1.1.6'
ifHCOutOctets = '1.3.6.1.2.1.31.1.1.1.10'
ifDescr = '1.3.6.1.2.1.2.2.1.2'
```

### 外部套件依賴
```
pysnmp>=4.4.12          # SNMP 協定
pysnmp-mibs>=0.1.6      # SNMP MIB 定義
rrdtool>=0.1.16         # RRD 資料庫 (選用 Python 綁定)
configparser>=5.0.0     # INI 配置解析
```

## 效能優化策略

### 1. SNMP Bulk Walking
```python
# 使用 bulkCmd 而非 getCmd
cmdGen.bulkCmd(
    snmpEngine,
    communityData,
    transportTarget,
    contextData,
    0, 50,  # non-repeaters, max-repetitions
    oid
)
```

### 2. 並行處理
```python
from multiprocessing import Pool

# 根據 fork_threshold 決定是否啟用多進程
if user_count > fork_threshold:
    with Pool(processes=max_processes) as pool:
        pool.map(collect_user_data, user_list)
```

### 3. 介面快取
```python
# 快取 SNMP 介面描述查詢結果
interface_cache = {}
if iface_key not in interface_cache:
    interface_cache[iface_key] = snmp_get(ifDescr_oid)
```

### 4. 設備專用參數
```python
# E320 需要較長超時
E320_TIMEOUT = 10
E320_RETRIES = 3

# 現代設備使用預設值
MODERN_TIMEOUT = 5
MODERN_RETRIES = 2
```

## 故障排除

### 常見問題

#### 1. SNMP 連線逾時
```
錯誤: Timeout: No response received before timeout
解決:
- 檢查防火牆規則 (UDP 161)
- 確認 SNMP community string
- 增加 timeout 值 (E320 用 10s)
```

#### 2. RRD 更新失敗
```
錯誤: illegal attempt to update using time XXX when last update time is YYY
解決:
- 確認系統時間同步
- 檢查 RRD step 設定 (1200 秒)
- 避免重複執行收集器
```

#### 3. Map 檔案格式錯誤
```
錯誤: ValueError: not enough values to unpack
解決:
- 確認使用底線分隔符: 1_2_0_3490, 35840_6144
- 檢查欄位數量是否正確 (4 欄)
- 移除空白行或註解行
```

#### 4. 記憶體不足
```
症狀: 收集過程中系統變慢或 OOM
解決:
- 降低 max_processes 值
- 提高 fork_threshold
- 增加系統 swap 空間
```

## 監控與維護

### 日常檢查項目
```bash
#!/bin/bash
# daily_check.sh

echo "=== RRDW Health Check ==="
echo "檢查時間: $(date)"

# 1. 檢查磁碟空間
echo -e "\n[磁碟空間]"
df -h /opt/isp_monitor/data

# 2. 檢查最近收集狀態
echo -e "\n[最近收集]"
tail -20 /opt/isp_monitor/logs/collector.log | grep "completed"

# 3. 檢查 RRD 檔案數量
echo -e "\n[RRD 檔案統計]"
echo "User Layer: $(find /opt/isp_monitor/data/user -name "*.rrd" | wc -l)"
echo "Sum Layer: $(find /opt/isp_monitor/data/sum -name "*.rrd" | wc -l)"
echo "Sum2m Layer: $(find /opt/isp_monitor/data/sum2m -name "*.rrd" | wc -l)"

# 4. 檢查錯誤日誌
echo -e "\n[最近錯誤]"
grep ERROR /opt/isp_monitor/logs/collector.log | tail -10
```

### 定期維護任務
```bash
# 每週清理過期日誌 (保留 30 天)
find /opt/isp_monitor/logs -name "*.log" -mtime +30 -delete

# 每月備份配置檔案
tar czf /backup/isp_monitor_config_$(date +%Y%m%d).tar.gz \
  /opt/isp_monitor/config

# 每季度驗證 RRD 完整性
find /opt/isp_monitor/data -name "*.rrd" -exec rrdtool info {} \; > /tmp/rrd_check.log
```

## 開發指南

### 新增收集器範例
```python
#!/usr/bin/env python3
"""
collector_template.py - 收集器範本
"""
import sys
from core.snmp_helper import SNMPHelper
from core.rrd_manager import RRDManager
from core.config_loader import ConfigLoader

def collect(device_ip, map_file):
    """主要收集函式"""
    config = ConfigLoader()
    snmp = SNMPHelper(device_ip, config)
    rrd = RRDManager(config)
    
    # 讀取 map 檔案
    users = read_map_file(map_file)
    
    # 收集流量數據
    for user in users:
        inbound, outbound = snmp.get_traffic(user['interface'])
        rrd.update_user(user['username'], inbound, outbound)
        rrd.update_sum(device_ip, user['bandwidth'], inbound, outbound)
    
    print(f"Collected {len(users)} users from {device_ip}")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: collector_template.py <ip> <map_file>")
        sys.exit(1)
    collect(sys.argv[1], sys.argv[2])
```

### 程式碼風格規範
- 使用 Python 3.6+ 語法
- 遵循 PEP 8 編碼規範
- 函式需包含 docstring
- 錯誤處理使用 try-except
- 日誌使用標準 logging 模組

## 附錄

### A. 介面命名格式對照

#### E320 格式
```
ge-1/2/0.3490     # GE: slot/port/pic.vci
xe-1/2/2.3490     # XE: slot/port/pic.vci
```

#### MX240/MX960/ACX7024 格式
```
ge-1/0/0:3490     # GE: fpc/pic/port:vci
xe-1/1/0:3490     # XE: fpc/pic/port:vci
```

### B. SNMP OID 參考
```
# IF-MIB (RFC 2863)
ifDescr          1.3.6.1.2.1.2.2.1.2        # 介面描述
ifType           1.3.6.1.2.1.2.2.1.3        # 介面類型
ifSpeed          1.3.6.1.2.1.2.2.1.5        # 介面速度
ifHCInOctets     1.3.6.1.2.1.31.1.1.1.6     # 入站位元組 (64-bit)
ifHCOutOctets    1.3.6.1.2.1.31.1.1.1.10    # 出站位元組 (64-bit)
```

### C. RRD 資料來源定義
```xml
<!-- User Layer RRD -->
<ds>
  <n>inbound</n>
  <type>COUNTER</type>
  <minimal_heartbeat>2400</minimal_heartbeat>
  <min>0</min>
  <max>U</max>
</ds>
<ds>
  <n>outbound</n>
  <type>COUNTER</type>
  <minimal_heartbeat>2400</minimal_heartbeat>
  <min>0</min>
  <max>U</max>
</ds>

<!-- RRA (Round Robin Archive) -->
<rra>
  <cf>AVERAGE</cf>
  <pdp_per_row>1</pdp_per_row>
  <xff>0.5</xff>
  <cdp_prep>...</cdp_prep>
</rra>
```

### D. 聯絡資訊
- **專案負責人**: Jason
- **系統維護**: Database Engineering Team
- **技術支援**: ISP Network Operations

---

**文件版本**: v2.0  
**最後更新**: 2025-11-19  
**適用系統**: Project Sigma - ISP Traffic Monitoring System
