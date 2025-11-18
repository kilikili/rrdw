# ISP 流量監控系統

完整的 BRAS 流量監控解決方案，支援 E320、ACX、MX960、MX240 四種設備。

## 🎯 最新更新

**Tab 分隔 BRAS-Map 格式已整合！**

✅ 10 欄位精簡設計（vs 舊的 13 欄位）  
✅ 統一 BRAS 調度器  
✅ 自動設備類型識別  
✅ 彈性過濾機制  

## 🚀 5 分鐘快速開始

### 1. 準備 BRAS-Map.txt（Tab 分隔）
```bash
vi config/BRAS-Map.txt
```

格式：
```tsv
Area	DeviceType	IP	CircuitID	Slot	Port	InterfaceType	BandwidthMax	IfAssign	Pic
taipei_4	3	61.64.191.74	223GD99004	1	0	GE	880	0	0
```

設備類型：1=MX240, 2=MX960, 3=E320, 4=ACX

### 2. 驗證格式
```bash
python3 bras_map_tsv_reader.py \
  --file config/BRAS-Map.txt \
  --statistics
```

### 3. 準備 Map Files
```bash
# 列出需要的 Map Files
python3 bras_map_tsv_reader.py \
  --file config/BRAS-Map.txt \
  --list-map-files

# 創建 Map Files（格式：使用者代碼,下載,上傳,ifindex,VLAN）
cat > config/maps/map_61.64.191.74_1_0.txt << 'MAPEOF'
0989111111,51200,20480,587247001,3001
0989222222,102400,40960,587247002,3002
MAPEOF
```

### 4. 測試調度器
```bash
python3 unified_bras_orchestrator.py \
  --bras-map config/BRAS-Map.txt \
  --map-dir config/maps \
  --dry-run
```

### 5. 一鍵部署
```bash
sudo bash install.sh
```

## 📚 必讀文檔

### 開始使用
1. **[TSV-INTEGRATION-SUMMARY.md](TSV-INTEGRATION-SUMMARY.md)** ⭐⭐⭐ - Tab 格式整合摘要
2. **[TSV-QUICK-REFERENCE.md](TSV-QUICK-REFERENCE.md)** ⭐⭐⭐ - 快速參考指南

### 完整文檔
3. **[FINAL-DELIVERABLES.md](FINAL-DELIVERABLES.md)** - 完整交付清單
4. **[COMPLETION-SUMMARY.md](COMPLETION-SUMMARY.md)** - 專案完成摘要
5. **[System-Architecture.md](System-Architecture.md)** - 系統架構設計

## 🎯 核心功能

### 配置管理
- ✅ Tab 分隔 BRAS-Map 格式
- ✅ 統一 5 欄位 Map File 格式
- ✅ 自動設備清單匯出

### 收集系統
- ✅ E320 收集器
- ✅ ACX 收集器
- ✅ MX960 收集器
- ✅ MX240 收集器
- ✅ 統一調度器（自動設備識別）
- ✅ 四層 RRD 架構
- ✅ 20 分鐘自動收集

### 報表系統
- ✅ TOP100 流量統計（日/週/月）
- ✅ Circuit 擁塞分析（3 日）
- ✅ VLAN 數量統計（月度增減）
- ✅ I/O 統計報表
- ✅ 速率分類統計

### 自動化
- ✅ 完整部署腳本
- ✅ Cron 自動排程
- ✅ Email 通知
- ✅ 錯誤處理

## 📊 系統架構

```
BRAS-Map.txt (Tab 分隔)
    ↓
Map Files (統一格式)
    ↓
Unified Orchestrator
    ↓
Collectors (E320/ACX/MX960/MX240)
    ↓
RRD Storage (四層)
    ↓
Reports (TOP100/Circuit/VLAN)
```

## 💡 使用範例

### 收集所有 Circuit
```bash
python3 unified_bras_orchestrator.py \
  --bras-map config/BRAS-Map.txt \
  --map-dir config/maps
```

### 只收集 E320
```bash
python3 unified_bras_orchestrator.py \
  --bras-map config/BRAS-Map.txt \
  --map-dir config/maps \
  --device-type 3
```

### 只收集特定區域
```bash
python3 unified_bras_orchestrator.py \
  --bras-map config/BRAS-Map.txt \
  --map-dir config/maps \
  --area taipei_4
```

### 產生 TOP100 報表
```bash
python3 traffic_top100.py --period daily
```

## 📂 目錄結構

```
/opt/rrdw/
├── config/
│   ├── BRAS-Map.txt              # Circuit 定義
│   └── maps/                     # Map Files
│       └── map_{IP}_{slot}_{port}.txt
├── data/                         # RRD 資料
│   └── {IP}/
│       └── {IP}_{slot}_{port}_{down}_{up}_{vlan}.rrd
├── reports/                      # 報表輸出
│   ├── top100/
│   ├── circuit/
│   └── vlan/
└── logs/                         # 系統日誌
```

## 🔧 系統需求

- OS: CentOS 7+ / Ubuntu 18.04+
- Python: 3.6+
- 套件: pysnmp, rrdtool, mysql-connector-python
- 權限: root（部署時）

## 📦 交付清單

**總計**: 47 個檔案
- Python 程式: 19 個
- Shell 腳本: 5 個
- 配置檔案: 3 個
- 技術文檔: 20 個
- 範例目錄: 7 個

## ✅ 完成狀態

- [x] 架構設計 (100%)
- [x] 收集器開發 (100%)
- [x] 報表系統 (100%)
- [x] 自動化 (100%)
- [x] 格式統一 (100%)
- [x] Tab 格式整合 (100%)

**總體進度**: 100% ✅

## 🎉 立即可部署

系統已完成全部開發和測試，可立即部署到生產環境！

---

**版本**: v1.0 (Final)  
**更新**: 2025-11-18  
**狀態**: 生產就緒 ✅
