# RRDW Traffic Collection System

## 專案概述

這是一個完整的 ISP 流量監控系統，支援多種 Juniper 設備（E320、MX240、MX960、ACX7024）的流量數據收集與 RRD 數據庫管理。

**版本**: v2.0  
**最後更新**: 2025-11-19  
**適用**: Project Sigma - ISP Traffic Monitoring System

## 目錄結構

```
rrdw_traffic_collection_system/
├── README.md                      # 完整系統文件
├── INSTALL.md                     # 安裝指南
├── QUICKSTART.md                  # 快速開始
│
├── config/                        # 配置檔案
│   ├── config.ini.example         # 主配置範本
│   ├── BRAS-Map.txt.example       # BRAS 映射範本
│   └── maps/                      # 設備 Map 檔案目錄
│       └── map_template.txt.example
│
├── collectors/                    # 收集器程式目錄
│   ├── collector_e320.py          # E320 收集器
│   ├── collector_mx240.py         # MX240 收集器
│   ├── collector_mx960.py         # MX960 收集器
│   └── collector_acx7024.py       # ACX7024 收集器
│
├── core/                          # 核心模組
│   ├── config_loader.py           # 配置載入器
│   ├── snmp_helper.py             # SNMP 工具
│   └── rrd_manager.py             # RRD 管理器
│
├── orchestrator/                  # 調度器
│   └── dispatcher.py              # 主要調度程式
│
├── tools/                         # 工具腳本
│   ├── setup.sh                   # 快速安裝腳本
│   ├── dependency_check.py        # 相依檢查工具
│   ├── collector_validator.py     # 收集器驗證工具
│   └── generate_map_template.py   # Map 範本產生器
│
├── docs/                          # 文件目錄
│   ├── INDEX.md                   # 文件索引
│   ├── DELIVERY_SUMMARY.md        # 交付總結
│   ├── COLLECTOR_FIXES.md         # 收集器修正指南
│   └── CODE_DEPENDENCIES.md       # 程式碼相依說明
│
├── data/                          # RRD 資料目錄
│   ├── user/                      # Layer 1: 用戶層
│   ├── sum/                       # Layer 2: 速率彙總層
│   ├── sum2m/                     # Layer 3: FUP 層
│   └── circuit/                   # Layer 4: 電路層
│
├── logs/                          # 日誌目錄
│
├── reports/                       # 報表目錄
│   ├── daily/                     # 日報表
│   ├── weekly/                    # 週報表
│   └── monthly/                   # 月報表
│
└── tests/                         # 測試目錄
```

## 快速開始

### 1. 系統安裝

```bash
cd tools
sudo bash setup.sh
```

### 2. 配置系統

```bash
# 複製並編輯配置檔案
cp config/config.ini.example config/config.ini
vim config/config.ini

# 複製並編輯 BRAS 映射
cp config/BRAS-Map.txt.example config/BRAS-Map.txt
vim config/BRAS-Map.txt
```

### 3. 產生 Map 檔案

```bash
cd tools
python3 collector_validator.py template \
  --output ../config/maps/map_61.64.191.74.txt \
  --type 3
```

### 4. 驗證配置

```bash
# 驗證 Map 檔案格式
python3 collector_validator.py validate \
  --map ../config/maps/map_61.64.191.74.txt

# 測試 SNMP 連線
python3 collector_validator.py test \
  --ip 61.64.191.74 \
  --type 3 \
  --map ../config/maps/map_61.64.191.74.txt
```

### 5. 執行收集測試

```bash
python3 collector_validator.py full \
  --ip 61.64.191.74 \
  --type 3 \
  --map ../config/maps/map_61.64.191.74.txt
```

## 重要文件

### 必讀文件
- **README.md** - 完整系統文件，包含所有技術細節
- **docs/INDEX.md** - 文件導覽索引
- **docs/COLLECTOR_FIXES.md** - 收集器開發修正指南

### 安裝部署
- **INSTALL.md** - 詳細安裝指南
- **QUICKSTART.md** - 快速開始指南
- **tools/setup.sh** - 自動安裝腳本

### 工具使用
- **tools/dependency_check.py** - 檢查系統相依
- **tools/collector_validator.py** - 驗證配置和測試連線

## 核心功能

### 四層 RRD 架構
1. **User Layer** - VLAN 級別用戶追蹤
2. **Sum Layer** - 速率檔次彙總統計
3. **Sum2m Layer** - Fair Usage Policy 實作
4. **Circuit Layer** - 電路級別統計分析

### 支援設備
- **E320** (DeviceType=1) - Legacy BRAS
- **MX960** (DeviceType=2) - Dynamic IP, High Capacity
- **MX240** (DeviceType=3) - Dynamic IP with PPPoE
- **ACX7024** (DeviceType=4) - Fixed IP Services

### 關鍵特性
- ✓ 自動設備類型識別
- ✓ SNMP Bulk Walking 優化
- ✓ 並行處理支援
- ✓ 完整錯誤處理
- ✓ 詳細日誌記錄

## Map 檔案格式

**標準格式** (使用底線分隔):
```
UserID,Slot_Port_VPI_VCI,Download_Upload,AccountID
0989703334,1_2_0_3490,35840_6144,587247394
```

**重要**: 
- 使用底線 `_` 分隔，不使用斜線 `/`
- 頻寬單位為 bps
- 第四欄位為電話號碼或用戶 ID

## 系統需求

- **作業系統**: CentOS 7/8 或 Ubuntu 20.04+
- **Python**: 3.6+
- **套件**: rrdtool, pysnmp, configparser
- **網路**: SNMP v2c (UDP 161)

## 部署流程

1. 執行 `tools/setup.sh` 進行系統安裝
2. 配置 `config/config.ini` 和 `config/BRAS-Map.txt`
3. 為每個設備產生 Map 檔案
4. 使用驗證工具測試配置
5. 部署收集器程式（collectors/ 目錄）
6. 設定 cron 或 systemd 定時執行

## 驗證清單

部署前請確認:
- [ ] `tools/dependency_check.py` 所有檢查通過
- [ ] 所有 Map 檔案格式正確（底線分隔）
- [ ] SNMP 連線測試成功
- [ ] 收集流程模擬成功
- [ ] 目錄權限正確設定
- [ ] 日誌可正常寫入

## 監控與維護

### 日常檢查
```bash
# 檢查收集狀態
tail -f logs/collector.log

# 檢查 RRD 檔案
find data/ -name "*.rrd" | wc -l

# 檢查磁碟空間
df -h data/
```

### 定期維護
- 每週清理過期日誌
- 每月備份配置檔案
- 每季驗證 RRD 完整性

## 故障排除

### 常見問題

1. **Map 檔案格式錯誤**
   ```bash
   python3 tools/collector_validator.py validate --map config/maps/your_map.txt
   ```

2. **SNMP 連線失敗**
   - 檢查防火牆規則（UDP 161）
   - 確認 community string
   - 增加 timeout 值（E320 需要 10s）

3. **RRD 更新失敗**
   - 確認系統時間同步
   - 檢查 RRD step 設定
   - 避免重複執行收集器

詳細故障排除請參考 **README.md** 的故障排除章節。

## 技術支援

- **專案負責人**: Jason
- **文件**: 參考 `docs/` 目錄
- **工具使用**: 所有工具都支援 `--help` 參數

## 授權

本專案用於 Project Sigma - ISP Traffic Monitoring System

---

**開始使用**: 建議先閱讀 `docs/INDEX.md` 了解所有文件，然後執行 `tools/setup.sh` 進行安裝。
