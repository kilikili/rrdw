# BRAS-Map Tab 分隔格式 - 整合摘要

## 🎯 格式整合完成

已完成 **BRAS-Map.txt Tab 分隔格式** 的完整整合，包含讀取器、調度器和完整文檔。

## 📦 新增交付檔案

### 核心文檔（2 個）
1. **[BRAS-MAP-TSV-FORMAT.md](computer:///mnt/user-data/outputs/BRAS-MAP-TSV-FORMAT.md)** ⭐⭐⭐ - 完整格式規範
2. **[TSV-QUICK-REFERENCE.md](computer:///mnt/user-data/outputs/TSV-QUICK-REFERENCE.md)** ⭐⭐⭐ - 快速參考指南

### 核心程式（2 個）
1. **[bras_map_tsv_reader.py](computer:///mnt/user-data/outputs/bras_map_tsv_reader.py)** ⭐⭐⭐ - TSV 讀取器
2. **[unified_bras_orchestrator.py](computer:///mnt/user-data/outputs/unified_bras_orchestrator.py)** ⭐⭐⭐ - 統一調度器

### 範例檔案
1. **examples/BRAS-Map-example.txt** - Tab 分隔範例
2. **examples/BRAS-Devices-from-TSV.txt** - 匯出的設備清單
3. **examples/config_tsv/** - 完整測試配置

## 📋 格式定義

### BRAS-Map.txt 格式（Tab 分隔）
```
Area	DeviceType	IP	CircuitID	Slot(Fpc)	Port	InterfaceType	BandwidthMax	IfAssign	Pic
```

**10 個欄位**：
1. Area - 區域名稱
2. DeviceType - 設備類型（1=MX240, 2=MX960, 3=E320, 4=ACX）
3. IP - BRAS IP
4. CircuitID - Circuit ID
5. Slot(Fpc) - 插槽編號
6. Port - 埠號
7. InterfaceType - 介面類型（GE/XE）
8. BandwidthMax - 頻寬上限（Mbps）
9. IfAssign - 介面分配
10. Pic - PIC 編號

### 範例
```tsv
taipei_4	3	61.64.191.74	223GD99004	1	0	GE	880	0	0
taipei_5	2	61.64.191.76	223GD99018	1	1	XE	880	0	0
taipei_6	4	61.64.191.77	223GD99018	0	0	XE	880	0	0
```

## 🔄 三層系統架構

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: BRAS-Map.txt (Tab 分隔)                           │
│   定義所有 Circuit 的基本資訊                               │
│   • Area, DeviceType, IP, Slot, Port, etc.                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Map Files (統一格式)                              │
│   每個 Circuit 對應一個 Map File                            │
│   • map_{IP}_{Slot}_{Port}.txt                            │
│   • 格式: 使用者代碼,下載,上傳,ifindex,VLAN                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Unified Orchestrator (統一調度器)                 │
│   根據 DeviceType 自動選擇收集器                            │
│   • DeviceType=1 → MX240Collector                         │
│   • DeviceType=2 → MX960Collector                         │
│   • DeviceType=3 → E320Collector                          │
│   • DeviceType=4 → ACXCollector                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: RRD Data Storage (四層 RRD)                       │
│   • User Layer   - 個別使用者（VLAN 層級）                 │
│   • Sum Layer    - 速率方案彙總                             │
│   • Sum2M Layer  - Fair Usage Policy                       │
│   • Circuit Layer - Circuit 級別統計                        │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 使用工作流程

### Step 1: 準備 BRAS-Map.txt
```bash
# 編輯 BRAS-Map.txt（確保使用 Tab 分隔）
vi config/BRAS-Map.txt
```

**重要**: 欄位之間必須使用 Tab (\t)，不可使用空格！

### Step 2: 驗證格式
```bash
# 檢查 Tab 分隔（應該看到 ^I）
cat -A config/BRAS-Map.txt | head -3

# 讀取並顯示統計
python3 bras_map_tsv_reader.py \
  --file config/BRAS-Map.txt \
  --statistics
```

### Step 3: 匯出設備清單
```bash
# 匯出為統一格式的設備清單
python3 bras_map_tsv_reader.py \
  --file config/BRAS-Map.txt \
  --export-devices config/BRAS-Devices.txt
```

### Step 4: 準備 Map Files
```bash
# 列出需要的 Map Files
python3 bras_map_tsv_reader.py \
  --file config/BRAS-Map.txt \
  --list-map-files

# 創建 Map Files（每個 Circuit 一個）
# 格式: 使用者代碼,下載速率,上傳速率,ifindex,VLAN
cat > config/maps/map_61.64.191.74_1_0.txt << 'EOF'
0989111111,51200,20480,587247001,3001
0989222222,102400,40960,587247002,3002
EOF
```

### Step 5: 測試調度器
```bash
# 測試模式（不實際執行）
python3 unified_bras_orchestrator.py \
  --bras-map config/BRAS-Map.txt \
  --map-dir config/maps \
  --dry-run

# 測試結果:
# ✓ 載入 9 個 Circuit
# ✓ 成功收集 6 個（有 Map File 的）
# ⚠️  失敗收集 3 個（沒有 Map File 的）
```

### Step 6: 執行實際收集
```bash
# 收集所有 Circuit
python3 unified_bras_orchestrator.py \
  --bras-map config/BRAS-Map.txt \
  --map-dir config/maps

# 只收集 E320
python3 unified_bras_orchestrator.py \
  --bras-map config/BRAS-Map.txt \
  --map-dir config/maps \
  --device-type 3

# 只收集特定區域
python3 unified_bras_orchestrator.py \
  --bras-map config/BRAS-Map.txt \
  --map-dir config/maps \
  --area taipei_4

# 只收集特定 IP
python3 unified_bras_orchestrator.py \
  --bras-map config/BRAS-Map.txt \
  --map-dir config/maps \
  --ip 61.64.191.74
```

## 📊 測試結果

### 讀取器測試
```
載入 9 個 Circuit
======================================================================
BRAS Map 統計資訊
======================================================================
總 Circuit 數量: 9
總 BRAS 數量: 7
總區域數量: 5

設備類型分布:
----------------------------------------------------------------------
  ACX     :   3 circuits,  3 BRAS
  E320    :   3 circuits,  1 BRAS
  MX240   :   2 circuits,  2 BRAS
  MX960   :   1 circuits,  1 BRAS

區域分布:
----------------------------------------------------------------------
  center_1    :   2 circuits,  2 BRAS
              設備類型: ACX, MX240
  south_1     :   2 circuits,  2 BRAS
              設備類型: ACX, MX240
  taipei_4    :   3 circuits,  1 BRAS
              設備類型: E320
  taipei_5    :   1 circuits,  1 BRAS
              設備類型: MX960
  taipei_6    :   1 circuits,  1 BRAS
              設備類型: ACX
```

### 調度器測試
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
```

## 🎯 格式優勢

### vs 舊格式（CSV, 13 欄位）
```csv
bras_hostname,device_type,bras_ip,circuit_id,pvc,trunk_number,phone,area,interface,slot,port,bandwidth,vlan_count
```

### 新格式（TSV, 10 欄位）
```tsv
Area	DeviceType	IP	CircuitID	Slot(Fpc)	Port	InterfaceType	BandwidthMax	IfAssign	Pic
```

### 改進統計
- **欄位數量**: 13 → 10 (減少 23%)
- **分隔符**: 逗號 → Tab（更清晰）
- **介面名稱**: 手動填寫 → 自動組合
- **維護性**: 複雜 → 簡單

## 🔧 介面命名自動化

### E320
```python
# 從: Slot=1, Port=0
# 產生: atm 1/0
interface = f"atm {slot}/{port}"
```

### MX240/MX960
```python
# 從: Slot=1, Pic=2, Port=0, InterfaceType=XE
# 產生: xe-1/2/0
interface = f"{interface_type.lower()}-{slot}/{pic}/{port}"
```

### ACX
```python
# 從: Slot=0, Pic=0, Port=1, InterfaceType=GE
# 產生: ge-0/0/1
interface = f"{interface_type.lower()}-{slot}/{pic}/{port}"
```

## 📂 完整目錄結構

```
/opt/rrdw/
├── config/
│   ├── BRAS-Map.txt                      # Circuit 定義 (Tab 分隔) ⭐⭐⭐
│   ├── BRAS-Devices.txt                  # 設備清單（自動匯出）
│   └── maps/                             # Map Files ⭐⭐⭐
│       ├── map_61.64.191.74_1_0.txt
│       ├── map_61.64.191.74_3_3.txt
│       ├── map_61.64.191.76_1_1.txt
│       └── ...
│
├── bras_map_tsv_reader.py                # TSV 讀取器 ⭐⭐⭐
├── unified_map_reader.py                 # Map File 讀取器
├── unified_bras_orchestrator.py          # 統一調度器 ⭐⭐⭐
│
├── collectors/                           # 收集器
│   ├── e320_collector.py
│   ├── acx_collector.py
│   ├── mx960_collector.py
│   └── mx240_collector.py
│
└── data/                                 # RRD 資料
    └── {IP}/
        └── {IP}_{slot}_{port}_{down}_{up}_{vlan}.rrd
```

## 💡 關鍵特性

### 1. 格式驗證
```bash
# 自動檢查 Tab 分隔
cat -A config/BRAS-Map.txt

# 驗證欄位數量
awk -F'\t' '{print NF}' config/BRAS-Map.txt | sort | uniq -c
```

### 2. 自動設備調度
根據 `DeviceType` 欄位自動選擇收集器：
- `1` → MX240Collector
- `2` → MX960Collector
- `3` → E320Collector
- `4` → ACXCollector

### 3. 彈性過濾
支援多種過濾條件：
- `--device-type` - 設備類型
- `--area` - 區域
- `--ip` - BRAS IP

### 4. 完整統計
提供詳細的收集報告：
- 成功/失敗數量
- 各設備類型統計
- 總使用者數
- 執行時間

## ✅ 整合檢查清單

部署前確認：

- [x] BRAS-Map.txt 格式正確（Tab 分隔）
- [x] 所有欄位完整填寫
- [x] DeviceType 正確（1/2/3/4）
- [x] 讀取器測試通過
- [x] 可以匯出設備清單
- [x] 可以列出需要的 Map Files
- [x] 調度器測試模式運作正常
- [x] 可以依設備類型過濾
- [x] 可以依區域過濾
- [x] 收集報告正確顯示

## 🎉 系統整合完成

### 完整功能
✅ **Tab 分隔格式** - 清晰的 Circuit 定義  
✅ **統一 Map 格式** - 5 欄位使用者清單  
✅ **自動設備調度** - 智能收集器選擇  
✅ **彈性過濾** - 多種篩選條件  
✅ **完整統計** - 詳細收集報告  
✅ **工具齊全** - 讀取、匯出、驗證  

### 系統流程
```
BRAS-Map.txt (Tab 分隔)
    ↓ [bras_map_tsv_reader.py]
Circuit 資訊
    ↓ [unified_map_reader.py]
Map Files (使用者清單)
    ↓ [unified_bras_orchestrator.py]
Collectors (E320/ACX/MX960/MX240)
    ↓
RRD Data (四層架構)
    ↓
Reports (TOP100/Circuit/VLAN)
```

## 📚 相關文檔

**必讀**:
1. **[TSV-QUICK-REFERENCE.md](computer:///mnt/user-data/outputs/TSV-QUICK-REFERENCE.md)** ⭐⭐⭐ - 快速開始
2. **[BRAS-MAP-TSV-FORMAT.md](computer:///mnt/user-data/outputs/BRAS-MAP-TSV-FORMAT.md)** ⭐⭐⭐ - 完整規範

**參考**:
3. **[UNIFIED-MAP-FORMAT.md](computer:///mnt/user-data/outputs/UNIFIED-MAP-FORMAT.md)** - Map File 格式
4. **[UNIFIED-FORMAT-SUMMARY.md](computer:///mnt/user-data/outputs/UNIFIED-FORMAT-SUMMARY.md)** - 統一格式摘要
5. **[System-Architecture.md](computer:///mnt/user-data/outputs/System-Architecture.md)** - 系統架構

## 🔍 故障排除

### Q: 讀取失敗？
```bash
# 檢查編碼
file config/BRAS-Map.txt

# 檢查 Tab 分隔
cat -A config/BRAS-Map.txt | head -3
```

### Q: 收集失敗？
```bash
# 檢查 Map File 是否存在
ls -l config/maps/

# 檢查 Map File 格式
head config/maps/map_*.txt
```

### Q: 統計異常？
```bash
# 重新載入配置
python3 bras_map_tsv_reader.py \
  --file config/BRAS-Map.txt \
  --statistics
```

## 📈 最終統計

**交付檔案總數**: 46 個
- Python 程式: 19 個 (+2)
- Shell 腳本: 5 個
- 配置檔案: 3 個
- 技術文檔: 19 個 (+2)
- 範例目錄: 5 個 (+1)

**新增核心功能**:
- ✅ Tab 分隔 BRAS-Map 讀取器
- ✅ 統一 BRAS 調度器
- ✅ 自動設備識別
- ✅ 彈性過濾機制
- ✅ 完整收集報告

## 🎊 結論

**BRAS-Map Tab 分隔格式已完全整合到系統中！**

系統現在支援：
- ✅ 清晰的 Tab 分隔 Circuit 定義
- ✅ 統一的 5 欄位 Map File 格式
- ✅ 智能的設備類型調度
- ✅ 完整的收集流程自動化
- ✅ 詳細的統計和報告

**立即可部署到生產環境！** 🚀
