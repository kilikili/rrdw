# 專案目錄結構說明

## 完整結構

```
rrdw_traffic_collection_system/
│
├── 📄 PROJECT_OVERVIEW.md         專案總覽
├── 📄 README.md                   完整系統文件
├── 📄 INSTALL.md                  安裝指南
├── 📄 QUICKSTART.md               快速開始
├── 📄 GETTING_STARTED.md          上手指南
├── 📄 STRUCTURE.md                本檔案
├── 📄 CHANGELOG.md                變更日誌
├── 📄 LICENSE                     授權說明
├── 📄 .gitignore                  Git 忽略檔案
│
├── 📁 config/                     配置檔案目錄
│   ├── config.ini.example         主配置範本
│   ├── BRAS-Map.txt.example       BRAS 設備映射範本
│   └── maps/                      設備 Map 檔案
│       └── map_template.txt.example
│
├── 📁 collectors/                 收集器程式目錄
│   ├── README.md                  目錄說明
│   ├── collector_e320.py          E320 收集器 (待開發)
│   ├── collector_mx240.py         MX240 收集器 (待開發)
│   ├── collector_mx960.py         MX960 收集器 (待開發)
│   └── collector_acx7024.py       ACX7024 收集器 (待開發)
│
├── 📁 core/                       核心模組目錄
│   ├── README.md                  目錄說明
│   ├── config_loader.py           配置載入器 (待開發)
│   ├── snmp_helper.py             SNMP 工具 (待開發)
│   └── rrd_manager.py             RRD 管理器 (待開發)
│
├── 📁 orchestrator/               調度器目錄
│   ├── README.md                  目錄說明
│   └── dispatcher.py              主調度器 (待開發)
│
├── 📁 tools/                      工具腳本目錄
│   ├── setup.sh                   ✅ 快速安裝腳本
│   ├── dependency_check.py        ✅ 相依檢查工具
│   ├── collector_validator.py     ✅ 收集器驗證工具
│   └── generate_map_template.py   ✅ Map 範本產生器
│
├── 📁 docs/                       文件目錄
│   ├── INDEX.md                   文件索引
│   ├── DELIVERY_SUMMARY.md        交付總結
│   ├── COLLECTOR_FIXES.md         收集器修正指南
│   └── CODE_DEPENDENCIES.md       程式碼相依說明
│
├── 📁 data/                       RRD 資料目錄
│   ├── user/                      Layer 1: 用戶層 RRD
│   ├── sum/                       Layer 2: 速率彙總層 RRD
│   ├── sum2m/                     Layer 3: FUP 層 RRD
│   └── circuit/                   Layer 4: 電路層 RRD
│
├── 📁 logs/                       日誌目錄
│   └── collector.log              收集器日誌 (自動產生)
│
├── 📁 reports/                    報表目錄
│   ├── daily/                     日報表
│   ├── weekly/                    週報表
│   └── monthly/                   月報表
│
└── 📁 tests/                      測試目錄
    └── README.md                  測試說明
```

## 目錄用途

### 配置相關
- **config/** - 所有配置檔案，包含系統設定和設備映射
- **config/maps/** - 各設備的用戶映射檔案

### 程式碼
- **collectors/** - 各設備類型的流量收集器
- **core/** - 可重用的核心功能模組
- **orchestrator/** - 收集任務的調度和管理

### 工具
- **tools/** - 安裝、驗證、測試等輔助工具

### 資料
- **data/** - RRD 時序資料庫檔案（四層架構）
- **logs/** - 系統運行日誌
- **reports/** - 產生的統計報表

### 文件
- **docs/** - 技術文件和開發指南
- **根目錄** - 專案總覽和使用說明

## 檔案狀態說明

- ✅ **已完成** - 可直接使用的檔案
- 📝 **範本** - 需要根據環境調整的範本
- 🔧 **待開發** - 需要根據需求開發的檔案
- 📖 **文件** - 說明文件

## 開發順序建議

1. ✅ 完成系統安裝 (`tools/setup.sh`)
2. 📝 配置系統設定 (`config/config.ini`)
3. 📝 設定設備映射 (`config/BRAS-Map.txt`)
4. 🔧 開發核心模組 (`core/`)
5. 🔧 開發收集器 (`collectors/`)
6. 🔧 開發調度器 (`orchestrator/`)
7. ✅ 驗證和測試 (`tools/collector_validator.py`)
8. 🚀 部署到生產環境

## 重要檔案位置

### 立即可用
- `tools/setup.sh` - 自動安裝
- `tools/dependency_check.py` - 環境檢查
- `tools/collector_validator.py` - 配置驗證

### 需要調整
- `config/config.ini.example` → `config/config.ini`
- `config/BRAS-Map.txt.example` → `config/BRAS-Map.txt`
- `config/maps/map_template.txt.example` → 各設備的實際 map 檔案

### 需要開發
- `collectors/` - 收集器主程式
- `core/` - 核心功能模組
- `orchestrator/` - 調度器程式

---

從 `PROJECT_OVERVIEW.md` 開始閱讀，了解專案全貌！
