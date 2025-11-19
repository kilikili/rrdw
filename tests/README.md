# Tests 目錄

此目錄存放測試程式和測試資料。

## 測試類型

### 單元測試
- 測試個別模組功能
- 使用 unittest 或 pytest

### 整合測試
- 測試模組間的互動
- 測試完整收集流程

### 驗證測試
- Map 檔案格式驗證
- SNMP 連線測試
- RRD 操作測試

## 執行測試

```bash
# 使用 collector_validator 工具
cd ../tools
python3 collector_validator.py full --ip <device_ip> --type <device_type> --map <map_file>

# 執行 dependency 檢查
python3 dependency_check.py /opt/isp_monitor
```

## 測試資料

測試用的 Map 檔案和配置應放在此目錄，避免影響生產環境。
