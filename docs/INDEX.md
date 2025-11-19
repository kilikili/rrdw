# RRDW 系統文件索引

## 📋 總覽

本次交付包含完整的 RRDW Traffic Collection System 文件和工具，專注於收集器的程式碼校正和驗證。

## 📁 檔案清單

### 1. 主要文件

#### **README.md** (14 KB)
完整的系統文件，包含：
- 系統架構說明
- 四層 RRD 架構
- 設備類型與收集器對照
- 配置檔案格式詳解
- 安裝部署指南
- 使用指南
- 故障排除
- 監控與維護

**用途**: 系統的完整參考手冊

---

### 2. 程式碼修正與驗證

#### **COLLECTOR_FIXES.md** (18 KB)
收集器程式碼修正指南，包含：
- Map 檔案格式標準化（底線分隔符）
- 介面名稱轉換修正
- SNMP 連線優化
- RRD 更新邏輯修正
- 錯誤處理機制
- 驗證清單
- 常見錯誤修正

**用途**: 收集器開發和修正的核心參考文件

#### **collector_validator.py** (21 KB)
收集器驗證工具，提供：
- Map 檔案格式驗證
- SNMP 連線測試
- 介面查詢測試
- 收集流程模擬
- Map 檔案範本產生

**使用範例**:
```bash
# 驗證 map 檔案
python3 collector_validator.py validate --map config/maps/map_61.64.191.74.txt

# 測試 SNMP 連線
python3 collector_validator.py test --ip 61.64.191.74 --type 3 --map config/maps/map_61.64.191.74.txt

# 產生範本
python3 collector_validator.py template --output test_map.txt --type 3

# 完整測試
python3 collector_validator.py full --ip 61.64.191.74 --type 3 --map config/maps/map_61.64.191.74.txt
```

---

### 3. 系統部署工具

#### **setup.sh** (9 KB)
快速設置腳本，自動執行：
- 系統套件安裝
- Python 相依套件安裝
- 目錄結構建立
- 配置檔案部署
- Cron 排程設定

**使用方式**:
```bash
sudo bash setup.sh
```

#### **dependency_check.py** (12 KB)
相依關係檢查工具，驗證：
- Python 版本
- Python 套件
- 系統工具
- 目錄結構
- 配置檔案
- Map 檔案格式

**使用方式**:
```bash
# 基本檢查
python3 dependency_check.py

# 完整檢查（含檔案系統）
python3 dependency_check.py /opt/isp_monitor config/maps/map_61.64.191.74.txt
```

---

### 4. 配置範本

#### **config.ini.template** (2.2 KB)
標準配置檔案範本，包含：
- 基礎路徑設定
- 資料庫設定
- SNMP 參數
- RRD 配置
- 收集參數
- 日誌設定
- Fair Usage Policy
- 效能調校

**部署方式**:
```bash
cp config.ini.template /opt/isp_monitor/config/config.ini
vim /opt/isp_monitor/config/config.ini
```

---

## 🚀 快速開始流程

### 步驟 1: 系統安裝
```bash
# 執行快速設置腳本
sudo bash setup.sh
```

### 步驟 2: 配置系統
```bash
# 編輯主配置檔案
vim /opt/isp_monitor/config/config.ini

# 編輯 BRAS 映射檔案
vim /opt/isp_monitor/config/BRAS-Map.txt
```

### 步驟 3: 產生 Map 檔案
```bash
# 為每個設備產生 map 檔案範本
python3 collector_validator.py template \
  --output /opt/isp_monitor/config/maps/map_61.64.191.74.txt \
  --type 3
```

### 步驟 4: 驗證配置
```bash
# 驗證 map 檔案格式
python3 collector_validator.py validate \
  --map /opt/isp_monitor/config/maps/map_61.64.191.74.txt

# 測試 SNMP 連線
python3 collector_validator.py test \
  --ip 61.64.191.74 \
  --type 3 \
  --map /opt/isp_monitor/config/maps/map_61.64.191.74.txt
```

### 步驟 5: 執行測試收集
```bash
# 完整測試流程
python3 collector_validator.py full \
  --ip 61.64.191.74 \
  --type 3 \
  --map /opt/isp_monitor/config/maps/map_61.64.191.74.txt
```

---

## 🔍 重要注意事項

### Map 檔案格式

**務必使用底線 (_) 分隔符，不要使用斜線 (/)**

```
# ✓ 正確格式
0989703334,1_2_0_3490,35840_6144,587247394
0981345344,3_1_0_3441,102400_40960,587272279

# ✗ 錯誤格式
0989703334,1/2/0/3490,35840/6144,587247394
0981345344,3/1/0/3441,102400/40960,587272279
```

格式說明:
- 欄位 1: 用戶 ID（電話號碼或用戶名稱）
- 欄位 2: Slot_Port_VPI_VCI（底線分隔）
- 欄位 3: Download_Upload（bps，底線分隔）
- 欄位 4: 帳號 ID

### 設備類型代碼

```
1 = E320 (Legacy BRAS)
2 = MX960 (Dynamic IP, High Capacity)
3 = MX240 (Dynamic IP with PPPoE)
4 = ACX7024 (Fixed IP Services)
```

### 常用頻寬設定（bps）

```
100M/40M:  102400_40960
50M/10M:   51200_10240
25M/5M:    25600_5120
10M/2M:    10240_2048
5M/1M:     5120_1024
```

---

## 📊 驗證清單

在部署到生產環境前，請確認：

- [ ] Python 版本 >= 3.6
- [ ] rrdtool 已安裝
- [ ] pysnmp 套件已安裝
- [ ] 所有目錄已建立
- [ ] config.ini 已正確設定
- [ ] BRAS-Map.txt 已填寫
- [ ] 所有 map 檔案格式正確（使用底線分隔）
- [ ] SNMP 連線測試通過
- [ ] 介面查詢測試通過
- [ ] 收集流程模擬成功
- [ ] RRD 檔案可以正常建立和更新

---

## 🛠️ 故障排除

### 問題 1: Map 檔案格式錯誤

**症狀**: ValueError: not enough values to unpack

**解決**:
```bash
python3 collector_validator.py validate --map your_map_file.txt
```

### 問題 2: SNMP 連線失敗

**症狀**: Timeout: No response received

**檢查**:
1. 防火牆規則（UDP 161）
2. SNMP community string
3. 設備 SNMP 設定

**測試**:
```bash
snmpget -v 2c -c public 61.64.191.74 1.3.6.1.2.1.1.1.0
```

### 問題 3: RRD 更新失敗

**症狀**: illegal attempt to update

**解決**:
1. 確認系統時間同步
2. 檢查 RRD step 設定
3. 避免同時執行多個收集器

---

## 📝 開發參考

### 新增收集器

參考 **COLLECTOR_FIXES.md** 中的範例程式碼，實作：
1. Map 檔案解析
2. 介面名稱轉換
3. SNMP 資料收集
4. RRD 檔案更新
5. 錯誤處理

### 程式碼風格

- 遵循 PEP 8
- 使用 type hints
- 完整的 docstring
- 適當的錯誤處理
- 詳細的日誌記錄

---

## 📞 支援資訊

- **專案**: Project Sigma - ISP Traffic Monitoring
- **文件版本**: v2.0
- **最後更新**: 2025-11-19

---

## 📦 檔案結構總覽

```
outputs/
├── README.md                    # 完整系統文件
├── COLLECTOR_FIXES.md          # 收集器修正指南
├── collector_validator.py      # 驗證工具
├── dependency_check.py         # 相依檢查工具
├── setup.sh                    # 快速設置腳本
├── config.ini.template         # 配置檔案範本
└── INDEX.md                    # 本檔案（索引）
```

---

**開始使用**: 建議先閱讀 README.md 了解系統架構，然後執行 setup.sh 進行安裝，最後使用 collector_validator.py 進行驗證測試。
