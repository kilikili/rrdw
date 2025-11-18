# BRAS-Map Tab 分隔格式 - 快速參考

## 🎯 新格式概述

### 格式標準
```
Area	DeviceType	IP	CircuitID	Slot(Fpc)	Port	InterfaceType	BandwidthMax	IfAssign	Pic
```

- **分隔符**: Tab (\t)
- **編碼**: UTF-8
- **檔名**: BRAS-Map.txt
- **欄位數**: 10 個

### 設備類型代碼
| 代碼 | 設備 |
|-----|------|
| 1 | MX240 |
| 2 | MX960 |
| 3 | E320 |
| 4 | ACX |

## 📋 完整範例

```tsv
Area	DeviceType	IP	CircuitID	Slot(Fpc)	Port	InterfaceType	BandwidthMax	IfAssign	Pic
taipei_4	3	61.64.191.74	223GD99004	1	0	GE	880	0	0
taipei_5	2	61.64.191.76	223GD99018	1	1	XE	880	0	0
taipei_6	4	61.64.191.77	223GD99018	0	0	XE	880	0	0
south_1	1	61.64.191.78	223GD99019	1	2	XE	880	0	2
```

## 🔄 三層架構

### 1. BRAS-Map.txt (Circuit 定義)
定義所有 Circuit 的基本資訊。

### 2. Map Files (使用者清單)
每個 Circuit 對應一個 Map File：
```
map_{IP}_{Slot}_{Port}.txt
```

格式：
```
使用者代碼,下載速率(Kbps),上傳速率(Kbps),ifindex,VLAN
```

### 3. 收集器調度
根據 DeviceType 自動選擇：
- DeviceType=1 → MX240Collector
- DeviceType=2 → MX960Collector  
- DeviceType=3 → E320Collector
- DeviceType=4 → ACXCollector

## 🚀 使用流程

### Step 1: 準備 BRAS-Map.txt
```bash
# 編輯 BRAS-Map.txt（Tab 分隔）
vi config/BRAS-Map.txt
```

### Step 2: 驗證格式
```bash
# 檢查是否為 Tab 分隔
cat -A config/BRAS-Map.txt | head -3

# 應該看到 ^I 表示 Tab
```

### Step 3: 讀取 Circuit 資訊
```bash
# 顯示統計
python3 bras_map_tsv_reader.py \
  --file config/BRAS-Map.txt \
  --statistics

# 查詢特定 IP
python3 bras_map_tsv_reader.py \
  --file config/BRAS-Map.txt \
  --ip 61.64.191.74

# 查詢特定區域
python3 bras_map_tsv_reader.py \
  --file config/BRAS-Map.txt \
  --area taipei_4
```

### Step 4: 匯出設備清單
```bash
# 匯出為統一格式
python3 bras_map_tsv_reader.py \
  --file config/BRAS-Map.txt \
  --export-devices config/BRAS-Devices.txt
```

### Step 5: 準備 Map Files
```bash
# 列出需要的 Map Files
python3 bras_map_tsv_reader.py \
  --file config/BRAS-Map.txt \
  --list-map-files

# 創建 Map Files（範例）
cat > config/maps/map_61.64.191.74_1_0.txt << 'EOF'
# E320 taipei_4, Slot 1 Port 0
0989111111,51200,20480,587247001,3001
0989222222,102400,40960,587247002,3002
EOF
```

### Step 6: 執行收集
```bash
# 測試模式（不實際執行）
python3 unified_bras_orchestrator.py \
  --bras-map config/BRAS-Map.txt \
  --map-dir config/maps \
  --dry-run

# 只收集 E320
python3 unified_bras_orchestrator.py \
  --bras-map config/BRAS-Map.txt \
  --map-dir config/maps \
  --device-type 3 \
  --dry-run

# 只收集特定區域
python3 unified_bras_orchestrator.py \
  --bras-map config/BRAS-Map.txt \
  --map-dir config/maps \
  --area taipei_4 \
  --dry-run

# 只收集特定 IP
python3 unified_bras_orchestrator.py \
  --bras-map config/BRAS-Map.txt \
  --map-dir config/maps \
  --ip 61.64.191.74 \
  --dry-run

# 實際執行（移除 --dry-run）
python3 unified_bras_orchestrator.py \
  --bras-map config/BRAS-Map.txt \
  --map-dir config/maps
```

## 📊 收集報告範例

```
======================================================================
收集統計報告
======================================================================
開始時間: 2025-11-18 06:21:03
結束時間: 2025-11-18 06:21:03
執行時間: 0.0 秒

總 Circuit 數: 9
成功收集: 6
失敗收集: 3
總使用者數: 9

各設備統計:
----------------------------------------------------------------------
  ACX     :   1 成功,   2 失敗,     1 使用者
  E320    :   3 成功,   0 失敗,     5 使用者
  MX240   :   1 成功,   1 失敗,     1 使用者
  MX960   :   1 成功,   0 失敗,     2 使用者
======================================================================
```

## 🔧 介面命名規則

### E320
```
格式: atm {Slot}/{Port}
範例: atm 1/0
```

### MX240/MX960
```
格式: {type}-{Slot}/{Pic}/{Port}
範例: xe-1/2/0 (10G)
      ge-1/0/1 (1G)
```

### ACX
```
格式: {type}-{Slot}/{Pic}/{Port}
範例: xe-0/0/0 (10G)
      ge-0/0/1 (1G)
```

## 📂 目錄結構

```
/opt/rrdw/
├── config/
│   ├── BRAS-Map.txt                      # Circuit 定義 (Tab 分隔)
│   └── maps/                             # Map Files
│       ├── map_61.64.191.74_1_0.txt
│       ├── map_61.64.191.74_3_3.txt
│       └── ...
│
├── bras_map_tsv_reader.py                # TSV 讀取器 ⭐⭐⭐
├── unified_map_reader.py                 # Map File 讀取器 ⭐⭐⭐
├── unified_bras_orchestrator.py          # 統一調度器 ⭐⭐⭐
│
└── data/                                 # RRD 資料
    └── {IP}/
        ├── {IP}_{slot}_{port}_{down}_{up}_{vlan}.rrd
        └── ...
```

## 💡 重要提醒

### Tab 分隔驗證
```bash
# 確認是 Tab 而不是空格
cat -A BRAS-Map.txt | head -3

# 正確：應該看到 ^I
# 錯誤：如果看到空格，需要轉換
```

### 欄位驗證
每行必須有 10 個欄位：
1. Area
2. DeviceType (1/2/3/4)
3. IP (IPv4)
4. CircuitID
5. Slot(Fpc) (數字)
6. Port (數字)
7. InterfaceType (GE/XE)
8. BandwidthMax (數字)
9. IfAssign (數字)
10. Pic (數字)

### Map File 必須存在
每個 Circuit 都需要對應的 Map File：
```
map_{IP}_{Slot}_{Port}.txt
```

如果 Map File 不存在，收集會失敗。

## 🎯 與舊格式的差異

### 舊格式 (CSV, 13 欄位)
```csv
bras_hostname,device_type,bras_ip,circuit_id,pvc,trunk_number,phone,area,interface,slot,port,bandwidth,vlan_count
```

### 新格式 (TSV, 10 欄位)
```tsv
Area	DeviceType	IP	CircuitID	Slot(Fpc)	Port	InterfaceType	BandwidthMax	IfAssign	Pic
```

### 優勢
✅ **精簡欄位** - 10 vs 13 欄位  
✅ **標準格式** - Tab 分隔更清晰  
✅ **易於解析** - 標準 TSV 格式  
✅ **統一介面** - 介面名稱由程式自動組合  

## 📚 相關文檔

- **[BRAS-MAP-TSV-FORMAT.md](computer:///mnt/user-data/outputs/BRAS-MAP-TSV-FORMAT.md)** - 完整格式規範
- **[UNIFIED-MAP-FORMAT.md](computer:///mnt/user-data/outputs/UNIFIED-MAP-FORMAT.md)** - Map File 格式
- **[UNIFIED-FORMAT-SUMMARY.md](computer:///mnt/user-data/outputs/UNIFIED-FORMAT-SUMMARY.md)** - 統一格式摘要

## 🔍 故障排除

### 問題: 載入失敗
```bash
# 檢查檔案編碼
file config/BRAS-Map.txt

# 檢查分隔符
cat -A config/BRAS-Map.txt | head
```

### 問題: 欄位數不正確
```bash
# 檢查每行的欄位數
awk -F'\t' '{print NF}' config/BRAS-Map.txt | sort | uniq -c
```

### 問題: 找不到 Map File
```bash
# 列出需要的 Map Files
python3 bras_map_tsv_reader.py \
  --file config/BRAS-Map.txt \
  --list-map-files

# 檢查實際存在的 Map Files
ls -1 config/maps/
```

## ✅ 檢查清單

部署前檢查：

- [ ] BRAS-Map.txt 使用 Tab 分隔
- [ ] 所有欄位都已填寫
- [ ] DeviceType 正確 (1/2/3/4)
- [ ] IP 格式正確
- [ ] 所有 Map Files 都已創建
- [ ] Map Files 格式正確（5 欄位）
- [ ] 測試模式運作正常
- [ ] 收集報告正確

## 🎉 總結

**Tab 分隔格式的優勢**：

✅ 清晰的欄位分隔  
✅ 精簡的 10 欄位設計  
✅ 標準 TSV 格式  
✅ 自動設備調度  
✅ 完整的工具支援  

**系統流程**：

```
BRAS-Map.txt (Circuit) 
    ↓
Map Files (使用者)
    ↓
Collectors (收集器)
    ↓
RRD (時序資料)
```

簡單、清晰、高效！
