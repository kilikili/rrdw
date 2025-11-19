# Core 模組目錄

此目錄存放核心功能模組。

## 核心模組

### config_loader.py
配置載入器，負責：
- 讀取 config.ini
- 讀取 BRAS-Map.txt
- 提供配置參數給其他模組

### snmp_helper.py
SNMP 工具模組，提供：
- SNMP 查詢功能
- Bulk Walking 功能
- 設備專用參數設定
- 連線重試機制
- 介面快取功能

### rrd_manager.py
RRD 管理模組，負責：
- RRD 檔案建立
- RRD 資料更新
- 四層 RRD 架構管理
  - User Layer (用戶層)
  - Sum Layer (速率彙總層)
  - Sum2m Layer (FUP 層)
  - Circuit Layer (電路層)

## 相依關係

```
collectors/*.py
    └── import core.config_loader
    └── import core.snmp_helper
    └── import core.rrd_manager
```

## 開發注意事項

1. 所有模組應該是獨立可測試的
2. 使用標準的 Python logging
3. 完整的錯誤處理
4. 詳細的 docstring
