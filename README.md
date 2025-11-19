# RRDW 收集器程式碼包

## 📦 內容說明

此程式碼包包含完整的 RRDW 流量收集系統實作，支援四種 Juniper 設備。

### 檔案結構

```
rrdw_code/
├── core/                          核心模組
│   ├── __init__.py
│   ├── config_loader.py          配置載入器
│   ├── snmp_helper.py            SNMP 輔助工具
│   └── rrd_manager.py            RRD 管理器
│
├── collectors/                    收集器
│   ├── __init__.py
│   ├── base_collector.py         收集器基類
│   ├── collector_e320.py         E320 收集器
│   ├── collector_mx240.py        MX240 收集器
│   ├── collector_mx960.py        MX960 收集器
│   └── collector_acx7024.py      ACX7024 收集器
│
├── deploy_collectors.sh           自動部署腳本
└── README.md                      本檔案
```

## 🚀 快速部署

### 方法 1: 使用自動部署腳本（推薦）

```bash
# 進入程式碼目錄
cd rrdw_code

# 執行部署腳本
sudo bash deploy_collectors.sh

# 按照提示完成部署
```

### 方法 2: 手動部署

```bash
# 建立目錄
sudo mkdir -p /opt/isp_monitor/{core,collectors,config/maps,data/{user,sum,sum2m,circuit},logs}

# 複製檔案
sudo cp -r core/* /opt/isp_monitor/core/
sudo cp -r collectors/* /opt/isp_monitor/collectors/

# 設定權限
sudo chmod +x /opt/isp_monitor/core/*.py
sudo chmod +x /opt/isp_monitor/collectors/*.py
```

## 📋 模組說明

### 1. core/config_loader.py

配置載入器，負責：
- 讀取 config.ini 配置檔案
- 讀取 BRAS-Map.txt 設備映射
- 提供配置參數給其他模組

**使用範例**:
```python
from core.config_loader import ConfigLoader

config = ConfigLoader()
print(f"Root Path: {config.root_path}")
print(f"SNMP Community: {config.snmp_community}")

# 載入 BRAS 設備列表
devices = config.load_bras_map()
for dev in devices:
    print(f"{dev['ip']} - Type {dev['device_type']}")
```

### 2. core/snmp_helper.py

SNMP 輔助工具，提供：
- SNMP GET 查詢
- SNMP Bulk Walk
- 介面資訊查詢
- 流量計數器查詢
- 連線測試

**使用範例**:
```python
from core.snmp_helper import SNMPHelper

snmp = SNMPHelper('192.168.1.1', 'public', timeout=5)

# 測試連線
if snmp.test_connectivity():
    print("連線成功")

# 查詢介面
interfaces = snmp.get_interface_descriptions()
for if_index, if_name in interfaces.items():
    print(f"{if_index}: {if_name}")

# 查詢流量
counters = snmp.get_interface_counters('ge-1/0/0:3490')
if counters:
    inbound, outbound = counters
    print(f"In: {inbound}, Out: {outbound}")
```

### 3. core/rrd_manager.py

RRD 管理器，支援：
- 四層 RRD 架構 (User/Sum/Sum2m/Circuit)
- 自動建立 RRD 檔案
- 更新 RRD 資料
- 查詢 RRD 資訊

**使用範例**:
```python
from core.rrd_manager import RRDManager

rrd = RRDManager('/opt/isp_monitor/data')

# 更新用戶 RRD
rrd.update_user_rrd('user001', inbound=1000000, outbound=500000)

# 更新 Sum Layer
rrd.update_sum_rrd('192.168.1.1', '102400_40960', 
                   inbound=50000000, outbound=25000000, user_count=50)
```

### 4. collectors/base_collector.py

收集器基類，提供：
- Map 檔案解析
- SNMP 連線測試
- 流量收集邏輯
- 統計資訊

所有具體收集器都繼承此基類。

### 5. collectors/collector_*.py

各設備的具體收集器實作：

| 檔案 | DeviceType | 設備 | 介面格式 |
|------|-----------|------|---------|
| collector_e320.py | 1 | E320 | ge-slot/port/pic.vci |
| collector_mx960.py | 2 | MX960 | ge-fpc/pic/port:vci |
| collector_mx240.py | 3 | MX240 | ge-fpc/pic/port:vci |
| collector_acx7024.py | 4 | ACX7024 | ge-fpc/pic/port:vci |

## 🧪 測試

### 單獨測試核心模組

```bash
cd /opt/isp_monitor

# 測試 Config Loader
python3 core/config_loader.py

# 測試 SNMP Helper
python3 core/snmp_helper.py <device_ip> public

# 測試 RRD Manager
python3 core/rrd_manager.py
```

### 測試收集器

```bash
cd /opt/isp_monitor/collectors

# 測試 E320
python3 collector_e320.py \
  --ip <E320_IP> \
  --map ../config/maps/map_<E320_IP>.txt \
  --debug

# 測試 MX240
python3 collector_mx240.py \
  --ip <MX240_IP> \
  --map ../config/maps/map_<MX240_IP>.txt \
  --debug
```

## 📖 詳細文件

請參考：
- **TESTING_GUIDE.md** - 完整測試指南
- **../README.md** - 系統完整文件
- **../docs/COLLECTOR_FIXES.md** - 收集器開發指南

## 🔧 相依套件

### Python 套件
```bash
pip3 install pysnmp pysnmp-mibs configparser
```

### 系統工具
```bash
# CentOS
sudo yum install -y rrdtool python3

# Ubuntu
sudo apt-get install -y rrdtool python3
```

## ⚙️ 配置需求

部署後需要：

1. **config.ini** - 系統配置
2. **BRAS-Map.txt** - 設備映射
3. **map_<IP>.txt** - 各設備的用戶映射

範本可從主專案包取得。

## 🎯 使用流程

1. 部署程式碼
2. 設定配置檔案
3. 建立 Map 檔案
4. 測試收集器
5. 設定 Cron 定時執行

## ⚠️ 重要提醒

### Map 檔案格式

**必須使用底線 (_) 分隔**:
```
✓ 正確: user001,1_2_0_3490,102400_40960,0912345678
✗ 錯誤: user001,1/2/0/3490,102400/40960,0912345678
```

### 介面格式

- **E320**: `ge-slot/port/pic.vci`
- **MX/ACX**: `ge-fpc/pic/port:vci`

### 設備專用參數

- **E320**: timeout=10s (較慢)
- **MX/ACX**: timeout=5s (標準)

## 🐛 故障排除

### 常見問題

1. **匯入錯誤**
   ```
   ModuleNotFoundError: No module named 'core'
   ```
   解決: 確認在正確目錄執行，或調整 PYTHONPATH

2. **SNMP 連線失敗**
   ```
   ERROR - SNMP GET 失敗: Timeout
   ```
   解決: 檢查防火牆、community string、設備 SNMP 設定

3. **RRD 更新失敗**
   ```
   ERROR - illegal attempt to update
   ```
   解決: 檢查系統時間、避免重複執行

## 📞 支援

- 查看日誌: `tail -f /opt/isp_monitor/logs/collector.log`
- 除錯模式: 加上 `--debug` 參數
- 參考文件: TESTING_GUIDE.md

---

**版本**: v2.0  
**最後更新**: 2025-11-19
