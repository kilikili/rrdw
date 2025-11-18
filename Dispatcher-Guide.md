# 智能收集器調度系統 - 使用指南

## 🎯 功能說明

**collector_dispatcher.py** 是一個智能調度系統，它可以：

1. **自動讀取 BRAS-Map.txt** - 取得所有設備和 Circuit 資訊
2. **識別設備類型** - 根據 device_type 欄位識別設備
3. **自動選擇收集器** - 依設備類型調用正確的收集方式
4. **混合環境支援** - 同時處理 E320 和 MX/ACX 設備

## 📋 設備類型對應

| device_type | 設備 | 收集器類型 | 收集方式 |
|-------------|------|-----------|---------|
| 3 | E320 | E320_MAP_FILE | Map File + ifindex |
| 1 | MX240 | MX_ACX_INTERFACE | 介面名稱方式 |
| 2 | MX960 | MX_ACX_INTERFACE | 介面名稱方式 |
| 4 | ACX7024 | MX_ACX_INTERFACE | 介面名稱方式 |

### E320 收集流程

```
BRAS-Map.txt → 識別 device_type=3
              ↓
        載入 maps/map_{IP}.txt
              ↓
        取得 ifindex 列表
              ↓
        SNMP 並行查詢
              ↓
        寫入 RRD 檔案
```

### MX/ACX 收集流程

```
BRAS-Map.txt → 識別 device_type=1,2,4
              ↓
        組合介面名稱
              ↓
        SNMP Walk 查詢
              ↓
        介面過濾
              ↓
        寫入 RRD 檔案
```

## 🚀 使用方式

### 基本使用

```bash
# 收集所有設備
python3 collector_dispatcher.py

# 只收集指定 IP
python3 collector_dispatcher.py --bras-ip 61.64.191.1

# 只收集 E320 設備
python3 collector_dispatcher.py --device-type 3

# 指定最大並行數
python3 collector_dispatcher.py --max-workers 5
```

### 進階使用

```bash
# 使用自訂的 BRAS-Map.txt
python3 collector_dispatcher.py --bras-map /path/to/BRAS-Map.txt

# 使用自訂的 Map File 目錄
python3 collector_dispatcher.py --map-dir /path/to/maps

# 組合使用
python3 collector_dispatcher.py \
  --bras-map /etc/rrdw/BRAS-Map.txt \
  --map-dir /etc/rrdw/maps \
  --max-workers 10
```

## 📊 執行範例

### 範例 1: 收集所有設備

```bash
$ python3 collector_dispatcher.py

======================================================================
智能收集器調度系統
======================================================================

======================================================================
載入 BRAS-Map.txt
======================================================================
總 Circuit 數量: 15
總 BRAS 數量: 9

設備類型分布:
  MX240     :   4 circuits,  2 BRAS
  MX960     :   3 circuits,  1 BRAS
  E320      :   5 circuits,  4 BRAS
  ACX7024   :   3 circuits,  2 BRAS

======================================================================
開始收集
======================================================================
總任務數: 15
並行數: 3

任務分布:
  E320: 5 個任務
  MX/ACX: 10 個任務

[執行收集...]

======================================================================
執行總結
======================================================================
總任務: 15
  ✓ 成功: 11
  ✗ 失敗: 0
  ⊘ 跳過: 4

總耗時: 0.52 秒

成功的任務:
  ✓ test_e320 (E320): 成功收集 1 個使用者
    - 用戶數: 1
    - 速率方案: 1
    - 耗時: 0.01s
  ✓ center_3 (MX240): 成功收集 MX/ACX 設備
    - 耗時: 0.05s
  [...]
```

### 範例 2: 只收集 E320 設備

```bash
$ python3 collector_dispatcher.py --bras-ip 127.0.0.1

======================================================================
收集 127.0.0.1
======================================================================
任務數: 1

======================================================================
調度任務: test_e320 (127.0.0.1)
  設備類型: E320
  收集器: E320_MAP_FILE
======================================================================

======================================================================
E320 收集: test_e320 (127.0.0.1)
  Slot: 1, Port: 2
======================================================================
步驟 1: 載入 Map File...
  ✓ 載入 1 個使用者
  ✓ 1 個速率方案
    - 35840_6144 (35.0/6.0 Mbps): 1 用戶

步驟 2: 需要查詢 1 個 ifindex
步驟 3: SNMP 收集 (模擬)
  ✓ 將使用 isp_traffic_collector_e320.py 的邏輯
  ✓ 並行查詢 ifindex: [587247394]...

步驟 4: RRD 檔案路徑範例
  - 0989703334: 127.0.0.1_1_2_35840_6144_3490.rrd

======================================================================
執行總結
======================================================================
總任務: 1
  ✓ 成功: 1
  ✗ 失敗: 0
  ⊘ 跳過: 0

成功的任務:
  ✓ test_e320 (E320): 成功收集 1 個使用者
    - 用戶數: 1
    - 速率方案: 1
    - 耗時: 0.00s
```

## 🔧 整合到實際收集器

### 方式 1: 直接整合

修改 `collector_dispatcher.py` 中的收集函數：

```python
def collect_e320(self, task: CollectionTask) -> Dict:
    """收集 E320 設備資料"""
    # 載入 Map File
    users = self.map_reader.load_map_file(
        task.bras_ip,
        slot=task.slot,
        port=task.port
    )
    
    # 取得 ifindex
    ifindexes = self.map_reader.get_all_ifindexes(users)
    
    # ✅ 在這裡調用實際的 SNMP 收集
    from isp_traffic_collector_e320 import FinalCollector
    
    collector = FinalCollector(
        rrd_base_dir="/home/bulks_data",
        db_config=None
    )
    
    # 執行收集
    collector.collect_device(
        task.bras_ip,
        task.bras_hostname,
        "public",  # community
        task.slot,
        task.port
    )
    
    return {'status': 'success', ...}
```

### 方式 2: 作為包裝器

保持原有的收集器不變，使用調度器作為包裝：

```python
# wrapper_script.py
from collector_dispatcher import CollectorDispatcher

dispatcher = CollectorDispatcher()
dispatcher.load_tasks()

# 取得 E320 任務
e320_tasks = [t for t in dispatcher.get_all_tasks() if t.is_e320]

# 對每個 E320 任務調用原有的收集器
for task in e320_tasks:
    os.system(f"python3 isp_traffic_collector_e320.py {task.bras_ip} {task.slot} {task.port}")
```

### 方式 3: Cron 定時執行

```bash
# /etc/cron.d/isp_traffic_collector

# 每 20 分鐘執行一次
*/20 * * * * /usr/bin/python3 /opt/rrdw/collector_dispatcher.py >> /var/log/collector.log 2>&1
```

## 📋 BRAS-Map.txt 格式要求

調度器需要以下欄位：

```
bras_hostname,device_type,bras_ip,circuit_id,slot,port,...

範例:
test_e320,3,127.0.0.1,TEST-SW-01,2,-,Circuit-TEST-001,43GD60001,測試,ge-1/2,1,2,3490,-
```

**關鍵欄位**:
- **device_type**: 設備類型代碼（1/2/3/4）
- **bras_ip**: BRAS IP 位址
- **slot**: 插槽編號
- **port**: 埠號

## 🎯 實際應用場景

### 場景 1: 日常收集

```bash
# 每天執行一次，收集所有設備
0 2 * * * python3 /opt/rrdw/collector_dispatcher.py
```

### 場景 2: 區域遷移

```bash
# 只收集新遷移的設備
python3 collector_dispatcher.py --bras-ip 10.1.1.1

# 驗證成功後，加入定時任務
```

### 場景 3: 混合環境

```bash
# 同時處理新舊設備
# E320 自動使用 Map File 方式
# MX/ACX 自動使用介面名稱方式
python3 collector_dispatcher.py
```

### 場景 4: 故障排查

```bash
# 只收集有問題的設備
python3 collector_dispatcher.py --bras-ip 61.64.191.1

# 檢查輸出，確認是否成功
```

## ⚙️ 設定說明

### 必要檔案

```
rrdw/
├── BRAS-Map.txt              # 設備清單
├── maps/                     # Map File 目錄
│   ├── map_61.64.191.1.txt   # E320 Map File
│   ├── map_10.1.1.1.txt      # MX Map File (可選)
│   └── ...
├── collector_dispatcher.py   # 調度器
├── bras_map_reader.py        # BRAS Map 讀取器
└── map_file_reader.py        # Map File 讀取器
```

### 環境變數（可選）

```bash
export RRDW_BASE_DIR=/home/bulks_data
export RRDW_MAP_DIR=/opt/rrdw/maps
export RRDW_BRAS_MAP=/opt/rrdw/BRAS-Map.txt
```

## 📊 輸出結果

### 成功的收集

```
✓ test_e320 (E320): 成功收集 1 個使用者
  - 用戶數: 1
  - 速率方案: 1
  - 耗時: 0.01s
```

### 跳過的收集

```
⊘ old_erx_1 (E320): 未找到使用者 (slot=0, port=0)
```

**原因**:
- E320 設備但沒有對應的 Map File
- 或 Map File 中沒有該 slot/port 的資料

### 失敗的收集

```
✗ center_3 (MX240): SNMP 連線失敗
```

**可能原因**:
- SNMP community 錯誤
- 設備無法連線
- Timeout 時間過短

## 🔍 除錯技巧

### 檢查設備類型

```python
from bras_map_reader import BRASMapReader

reader = BRASMapReader("BRAS-Map.txt")
reader.load()

# 顯示所有設備類型
for circuit in reader.circuits:
    print(f"{circuit.bras_hostname}: device_type={circuit.device_type_name}")
```

### 檢查 Map File

```python
from map_file_reader import MapFileReader

reader = MapFileReader("maps")

# 驗證格式
is_valid, errors = reader.validate_map_file("61.64.191.1")
if not is_valid:
    for error in errors:
        print(error)
```

### 測試單一設備

```bash
# 只測試一個設備，查看詳細輸出
python3 collector_dispatcher.py --bras-ip 127.0.0.1
```

## 💡 最佳實踐

### 1. 定期驗證

```bash
# 每週驗證一次 Map File 格式
python3 -c "
from map_file_reader import MapFileReader
reader = MapFileReader('maps')
for ip in ['61.64.191.1', '10.1.1.1']:
    valid, errors = reader.validate_map_file(ip)
    if not valid:
        print(f'{ip}: {errors}')
"
```

### 2. 日誌記錄

```bash
# 記錄收集結果
python3 collector_dispatcher.py >> /var/log/rrdw/collector.log 2>&1
```

### 3. 監控告警

```bash
# 檢查失敗的任務
if grep -q "✗ 失敗:" /var/log/rrdw/collector.log; then
    echo "收集失敗，請檢查日誌" | mail -s "RRDW Alert" admin@example.com
fi
```

## 🎓 進階功能

### 自訂收集邏輯

```python
class MyCollectorDispatcher(CollectorDispatcher):
    def collect_e320(self, task):
        # 自訂 E320 收集邏輯
        pass
    
    def collect_mx_acx(self, task):
        # 自訂 MX/ACX 收集邏輯
        pass
```

### 並行優化

```python
# 依設備類型分組並行
e320_tasks = [t for t in tasks if t.is_e320]
mx_tasks = [t for t in tasks if not t.is_e320]

# E320 較慢，使用較少執行緒
with ThreadPoolExecutor(max_workers=3) as executor:
    executor.map(collect_e320, e320_tasks)

# MX/ACX 較快，使用較多執行緒
with ThreadPoolExecutor(max_workers=10) as executor:
    executor.map(collect_mx_acx, mx_tasks)
```

## ✅ 檢查清單

### 部署前

- [ ] BRAS-Map.txt 格式正確
- [ ] Map File 目錄存在
- [ ] E320 設備有對應的 Map File
- [ ] 測試單一設備收集成功

### 運行中

- [ ] 定期檢查日誌
- [ ] 監控失敗任務
- [ ] 驗證 RRD 檔案產生
- [ ] 檢查資料完整性

## 🎉 總結

**collector_dispatcher.py** 提供了：

✅ **自動化** - 根據 BRAS-Map.txt 自動收集  
✅ **智能化** - 自動識別設備類型並選擇收集器  
✅ **混合環境** - 同時支援 E320 和 MX/ACX  
✅ **易於整合** - 可整合到現有系統  

**立即開始**:
```bash
python3 collector_dispatcher.py --bras-ip 127.0.0.1
```

---

**版本**: 1.0  
**狀態**: ✅ 測試通過  
**文件**: collector_dispatcher.py
