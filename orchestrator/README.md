# Orchestrator 目錄

此目錄存放調度器程式。

## dispatcher.py

主要調度器，負責：
- 讀取 BRAS-Map.txt
- 自動識別設備類型
- 調度適當的收集器
- 管理收集流程
- 記錄收集結果

## 使用方式

```bash
# 執行完整收集
python3 dispatcher.py

# 指定特定區域
python3 dispatcher.py --area taipei

# 乾跑模式（不實際收集）
python3 dispatcher.py --dry-run

# 指定配置檔案
python3 dispatcher.py --config /path/to/config.ini
```

## 排程設定

### Cron 方式
```bash
# 每 20 分鐘執行
*/20 * * * * cd /opt/isp_monitor && python3 orchestrator/dispatcher.py >> logs/cron.log 2>&1
```

### Systemd 方式
參考 `tools/setup.sh` 中的 systemd 服務設定。

## 工作流程

1. 讀取 BRAS-Map.txt
2. 解析設備資訊（IP, Type, Circuit）
3. 檢查對應的 Map 檔案是否存在
4. 根據設備類型選擇收集器
5. 執行收集器
6. 記錄結果和錯誤
7. 產生統計報告
