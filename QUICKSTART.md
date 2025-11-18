# BRAS Map 系統 - 快速開始指南

## 🚀 5 分鐘快速開始

### 步驟 1: 下載檔案

所有檔案已準備就緒：

```bash
# 檔案清單
BRAS-Map.txt                    # Circuit 資料（需要根據實際環境修改）
bras_map_reader.py              # 核心讀取器
bras_map_collector.py           # 資料收集器
interface_mapping_generator.py  # 介面對照表產生器
test_bras_map.py               # 測試套件
deploy.sh                      # 一鍵部署腳本
README.md                      # 完整文件
PROJECT_SUMMARY.md             # 專案總結
BRAS-Map-Format.md             # 格式規範
```

### 步驟 2: 一鍵部署

```bash
# 給予執行權限
chmod +x deploy.sh

# 執行部署
./deploy.sh

# 選擇選項 1 進行完整部署
```

### 步驟 3: 驗證系統

```bash
# 快速測試
python3 test_bras_map.py

# 預期看到
✓ 檔案存在: BRAS-Map.txt
✓ 成功載入 12 筆 Circuit 資料
✓ 所有測試通過！
```

### 步驟 4: 產生介面對照表

```bash
# 產生所有格式的對照表
python3 interface_mapping_generator.py

# 產生的檔案
interface_mapping.csv           # 統一格式
interface_mapping_MX240.csv     # MX240 專用
interface_mapping_MX960.csv     # MX960 專用
interface_mapping_E320.csv      # E320 專用
interface_mapping_ACX7024.csv   # ACX7024 專用
interface_mapping_台中交心.csv  # 區域分類
```

## 📋 重要提醒

### 1. BRAS-Map.txt 格式

**關鍵欄位（必填）：**

```
bras_hostname    - BRAS 主機名稱
device_type      - 設備類型 (1:MX240, 2:MX960, 3:E320, 4:ACX7024)
bras_ip          - BRAS IP 位址
interface_info   - 介面資訊
slot             - 插槽
port             - 埠號
vlan             - VLAN ID
```

**範例：**

```
# MX240 (device_type = 1)
center_3,1,61.64.214.54,TC7520-0,2,-,Circuit-TC-001,43GD10013,台中交心,xe-1/0/0,1,0,400,1

# E320 (device_type = 3)  
old_erx_1,3,61.64.191.1,KH-SW-02,6,-,Circuit-KH-001,43GD30001,高雄,ge-0/0,0,0,500,-
```

### 2. 介面格式差異

**E320 (兩段式):**
```
ge-0/0.500    ← 介面名稱.VLAN
```

**MX/ACX (三段式):**
```
xe-1/0/0.400  ← 介面名稱.VLAN
```

### 3. 速率格式

**重要：使用底線（_）分隔，不是斜線（/）**

```
✓ 正確: 61440_20480
✗ 錯誤: 61440/20480
```

這符合正式環境格式！

## 🔧 常用操作

### 查看統計資訊

```python
from bras_map_reader import BRASMapReader

reader = BRASMapReader("BRAS-Map.txt")
reader.load()
reader.print_statistics()
```

### 查詢特定 BRAS

```python
# 依主機名稱
circuits = reader.get_circuits_by_bras("center_3")

# 依 IP
circuits = reader.get_circuits_by_ip("61.64.214.54")

# 依區域
circuits = reader.get_circuits_by_area("台中交心")
```

### 執行資料收集

```python
from bras_map_collector import BRASMapCollector

collector = BRASMapCollector("BRAS-Map.txt")
collector.load_bras_map()
collector.collect_all_data(max_workers=5)
```

## 📊 設備類型說明

| 代碼 | 設備 | 介面格式 | Timeout | 優先序 |
|-----|------|---------|---------|--------|
| 1 | MX240 | xe-1/0/0.400 | 3s | 高 |
| 2 | MX960 | ge-0/0/1.100 | 3s | 高 |
| 3 | E320 | ge-0/0.500 | 10s | 低 |
| 4 | ACX7024 | ge-0/0/2.200 | 3s | 中 |

**重點：**
- E320 較慢，系統自動使用較長的 timeout
- 新設備 (MX/ACX) 優先收集
- 支援混合環境同時運作

## 🎯 下一步建議

### 立即執行

1. ✅ **修改 BRAS-Map.txt**
   - 填入實際的 BRAS IP
   - 設定正確的 VLAN
   - 確認設備類型

2. ✅ **執行測試**
   ```bash
   ./deploy.sh
   選項 2: 快速測試
   ```

3. ✅ **產生對照表**
   ```bash
   ./deploy.sh
   選項 3: 產生介面對照表
   ```

### 後續整合

4. **資料庫設定**
   - 在 `bras_map_collector.py` 中設定資料庫連線
   - 測試從 FreeRADIUS 載入使用者對應

5. **SNMP 測試**
   ```bash
   # 測試 SNMP 連線
   snmpwalk -v2c -c public <BRAS_IP> ifDescr
   ```

6. **試運行**
   - 選擇小範圍測試（例如：10 個使用者）
   - 驗證收集到的資料正確性
   - 比對與舊系統的差異

## ⚠️ 注意事項

### 正式環境前檢查

- [ ] BRAS-Map.txt 內容完整正確
- [ ] 所有 BRAS IP 可 ping 通
- [ ] SNMP community 設定正確
- [ ] 資料庫連線測試通過
- [ ] 介面名稱格式驗證
- [ ] VLAN 範圍檢查 (1-4094)

### 效能調整

```python
# 小型環境 (<10 BRAS)
collector.collect_all_data(max_workers=3)

# 中型環境 (10-30 BRAS)
collector.collect_all_data(max_workers=5)

# 大型環境 (>30 BRAS)
collector.collect_all_data(max_workers=10)
```

## 📞 取得協助

### 查看文件

- **完整文件**: README.md
- **專案總結**: PROJECT_SUMMARY.md
- **格式規範**: BRAS-Map-Format.md

### 常見問題

**Q: E320 收集逾時怎麼辦？**
```python
# 在 bras_map_collector.py 增加 timeout
if device_type == DEVICE_TYPE_E320:
    timeout = 15  # 從 10 秒增加到 15 秒
```

**Q: 介面名稱不匹配？**
```bash
# 檢查實際的介面名稱
snmpwalk -v2c -c public <BRAS_IP> ifDescr

# 確認 BRAS-Map.txt 中的 interface_info 欄位正確
```

**Q: 如何驗證資料正確性？**
```bash
# 執行完整測試
python3 test_bras_map.py

# 檢查產生的資料
head -20 traffic_data.txt
```

## 🎓 學習資源

### 範例檔案

系統附帶完整範例：
- BRAS-Map.txt 包含各種設備類型範例
- 涵蓋北中南三區設定
- 新舊設備混合環境範例

### 測試資料

```bash
# 使用範例資料測試
python3 test_bras_map.py         # 驗證格式
python3 interface_mapping_generator.py  # 產生對照表
```

---

**開始使用**: `./deploy.sh`  
**問題回報**: 執行測試套件並檢視錯誤訊息  
**更多資訊**: 參閱 README.md

Good luck! 🚀
