# 快速上手指南

## 3 步驟開始使用

### 步驟 1: 解壓縮並安裝

```bash
# 解壓縮
unzip rrdw_traffic_collection_system.zip
cd rrdw_traffic_collection_system

# 執行自動安裝
cd tools
sudo bash setup.sh
```

### 步驟 2: 配置系統

```bash
# 返回專案根目錄
cd ..

# 複製配置範本
cp config/config.ini.example config/config.ini
cp config/BRAS-Map.txt.example config/BRAS-Map.txt

# 編輯配置（使用您慣用的編輯器）
vim config/config.ini
vim config/BRAS-Map.txt
```

**重要配置項目**:
- `config.ini` 中的 `root_path`, `snmp` 參數
- `BRAS-Map.txt` 中的設備資訊

### 步驟 3: 產生並驗證 Map 檔案

```bash
cd tools

# 為每個設備產生 Map 檔案範本
python3 collector_validator.py template \
  --output ../config/maps/map_61.64.191.74.txt \
  --type 3

# 編輯 Map 檔案，填入實際用戶資料
vim ../config/maps/map_61.64.191.74.txt

# 驗證格式
python3 collector_validator.py validate \
  --map ../config/maps/map_61.64.191.74.txt

# 測試 SNMP 連線
python3 collector_validator.py test \
  --ip 61.64.191.74 \
  --type 3 \
  --map ../config/maps/map_61.64.191.74.txt
```

## 完成！

系統已就緒，您可以：

1. **手動執行收集器測試**
   ```bash
   python3 collector_validator.py full \
     --ip 61.64.191.74 \
     --type 3 \
     --map ../config/maps/map_61.64.191.74.txt
   ```

2. **部署收集器程式**
   - 將您的收集器程式放入 `collectors/` 目錄
   - 將調度器放入 `orchestrator/` 目錄
   - 將核心模組放入 `core/` 目錄

3. **設定定時執行**
   - 系統已自動設定 cron（如果安裝時選擇）
   - 手動檢查: `crontab -l`

4. **監控運行狀態**
   ```bash
   # 查看日誌
   tail -f logs/collector.log
   
   # 檢查 RRD 檔案
   ls -lh data/user/
   ```

## 需要幫助？

- 📖 閱讀 `README.md` 了解完整功能
- 📖 查看 `docs/INDEX.md` 瀏覽所有文件
- 🔧 使用工具的 `--help` 查看詳細用法
- 📝 參考 `docs/COLLECTOR_FIXES.md` 進行收集器開發

## 常見問題

**Q: Map 檔案格式應該是什麼？**
A: 使用底線分隔：`UserID,1_2_0_3490,35840_6144,AccountID`

**Q: SNMP 連線失敗怎麼辦？**
A: 檢查防火牆、community string、設備 SNMP 設定

**Q: 如何查看收集狀態？**
A: `tail -f logs/collector.log`

---

開始您的流量監控之旅！🚀
