# ISP Traffic Monitor - 檢查清單與快速開始

## 📋 本次交付檔案清單

### 主要文檔
- ✅ **README.md** (16KB) - 完整系統文檔
  - 系統架構說明
  - 配置檔案格式
  - 使用說明
  - 報表系統
  - 故障排除

- ✅ **INSTALL.md** (9KB) - 快速安裝指南
  - 系統需求
  - 15步安裝流程
  - 效能調優
  - 常見問題排除

- ✅ **CODE_DEPENDENCIES.md** (18KB) - 程式碼相依關係
  - 系統架構圖
  - 模組說明
  - 資料流程
  - 相依套件版本
  - 匯入關係

### 工具程式
- ✅ **dependency_checker.py** (12KB) - 相依關係檢查工具
  - 檢查Python版本
  - 檢查必要套件
  - 檢查系統命令
  - 生成安裝腳本

- ✅ **generate_map_template.py** (12KB) - Map檔案範本產生工具
  - 讀取BRAS-Map.txt
  - 自動生成map檔案範本
  - 支援SNMP查詢驗證
  - 支援E320和MX/ACX格式

- ✅ **collector_validator.py** (19KB) - 收集器驗測工具
  - 驗證map檔案格式
  - 驗證BRAS-Map.txt格式
  - 測試SNMP連線
  - 測試介面查詢
  - 檢查RRD目錄和檔案

### 範本檔案
- ✅ **map_template.txt** (2KB) - Map檔案格式範本
  - E320格式範例
  - MX/ACX格式範例
  - 速度方案參考
  - 格式說明

## 🚀 快速開始流程

### 第一步: 環境準備 (5分鐘)

```bash
# 1. 檢查相依關係
python3 dependency_checker.py

# 2. 如果有缺少的套件，生成安裝腳本
python3 dependency_checker.py --generate-install-script

# 3. 執行安裝腳本
sudo ./install_dependencies.sh
```

### 第二步: 安裝系統 (10分鐘)

```bash
# 1. 建立目錄結構
sudo mkdir -p /opt/isp_monitor/{config/maps,collectors,lib,reports,data/{sum,sum2m,circuit},logs}
sudo mkdir -p /var/log/isp_traffic

# 2. 複製程式檔案到目標目錄
# (假設您的收集器程式已經準備好)
sudo cp -r collectors/* /opt/isp_monitor/collectors/
sudo cp -r lib/* /opt/isp_monitor/lib/
sudo cp -r reports/* /opt/isp_monitor/reports/

# 3. 複製配置範例
sudo cp config.ini.example /opt/isp_monitor/config/config.ini

# 4. 設定權限
sudo chown -R monitor:monitor /opt/isp_monitor
```

### 第三步: 配置檔案 (15分鐘)

```bash
# 1. 編輯主配置檔案
sudo vi /opt/isp_monitor/config/config.ini
# 重點設定:
# - SNMP community
# - 路徑設定
# - 超時參數

# 2. 準備BRAS-Map.txt
sudo vi /opt/isp_monitor/config/BRAS-Map.txt
# 填入所有設備資訊:
# Area	DeviceType	IP	CircuitID	Slot	Port	InterfaceType	BandwidthMax	IfAssign	Pic

# 3. 驗證BRAS-Map.txt格式
python3 collector_validator.py --bras-map /opt/isp_monitor/config/BRAS-Map.txt
```

### 第四步: 生成Map檔案 (10分鐘)

```bash
# 1. 自動生成所有設備的map檔案範本
cd /opt/isp_monitor
python3 tools/generate_map_template.py \
    -b config/BRAS-Map.txt \
    -o config/maps/ \
    -n 10

# 2. 編輯map檔案，填入實際用戶資料
sudo vi config/maps/map_61.64.191.74.txt

# 3. 驗證map檔案格式
python3 collector_validator.py \
    --map-file config/maps/map_61.64.191.74.txt
```

### 第五步: 測試連線 (5分鐘)

```bash
# 1. 測試SNMP連線
python3 collector_validator.py \
    --test-snmp 61.64.191.74 \
    --community public

# 2. 測試介面查詢
python3 collector_validator.py \
    --test-snmp 61.64.191.74 \
    --test-interfaces

# 3. 對所有設備重複測試
```

### 第六步: 執行收集器 (5分鐘)

```bash
# 1. 手動執行一次收集
cd /opt/isp_monitor
python3 collectors/collector_dispatcher.py

# 2. 查看日誌
tail -f /var/log/isp_traffic/collector.log

# 3. 檢查RRD檔案
ls -lh data/*.rrd | head -10
ls -lh data/sum/*.rrd | head -5
ls -lh data/sum2m/*.rrd | head -5
ls -lh data/circuit/*.rrd | head -5
```

### 第七步: 設定自動執行 (2分鐘)

```bash
# 1. 編輯crontab
crontab -e

# 2. 加入排程 (每20分鐘執行)
*/20 * * * * cd /opt/isp_monitor && python3 collectors/collector_dispatcher.py >> /var/log/isp_traffic/cron.log 2>&1

# 3. 驗證crontab設定
crontab -l
```

### 第八步: 完整驗證 (5分鐘)

```bash
# 1. 執行完整驗證
cd /opt/isp_monitor
python3 tools/collector_validator.py --full

# 2. 等待20分鐘後檢查自動執行
tail -f /var/log/isp_traffic/cron.log

# 3. 檢查RRD檔案更新時間
ls -lht data/*.rrd | head -20
```

## ✅ 驗證檢查清單

### 環境檢查
- [ ] Python 3.6+ 已安裝
- [ ] pysnmp >= 4.4.0 已安裝
- [ ] rrdtool 已安裝
- [ ] net-snmp-utils 已安裝
- [ ] 所有必要目錄已建立
- [ ] 目錄權限正確設定

### 配置檢查
- [ ] config.ini 已正確配置
  - [ ] SNMP community 正確
  - [ ] 路徑設定正確
  - [ ] 超時參數合理
- [ ] BRAS-Map.txt 格式正確
  - [ ] 所有設備都已列出
  - [ ] DeviceType 正確對應
  - [ ] IP位址可達
- [ ] map_{ip}.txt 格式正確
  - [ ] 使用底線分隔
  - [ ] 頻寬單位為kbps
  - [ ] 所有欄位完整

### 連線檢查
- [ ] 所有設備SNMP連線成功
  - [ ] E320設備 (Type 3)
  - [ ] MX240設備 (Type 2)
  - [ ] MX960設備 (Type 1)
  - [ ] ACX7024設備 (Type 4)
- [ ] SNMP介面查詢正常
- [ ] 網路路由可達

### 收集檢查
- [ ] 收集器手動執行成功
- [ ] RRD檔案正確生成
  - [ ] User層檔案存在
  - [ ] Speed層檔案存在
  - [ ] FUP層檔案存在
  - [ ] Circuit層檔案存在
- [ ] 日誌無ERROR訊息
- [ ] 收集時間合理 (<5分鐘)

### 自動執行檢查
- [ ] Crontab設定正確
- [ ] 自動執行成功
- [ ] RRD檔案持續更新
- [ ] 日誌檔案正常輪換

## 🔧 常見問題快速解決

### Q1: SNMP連線失敗
```bash
# 檢查網路
ping 61.64.191.74

# 測試SNMP
snmpwalk -v2c -c public 61.64.191.74 sysDescr.0

# 檢查防火牆
sudo iptables -L | grep 161
```

### Q2: Map檔案格式錯誤
```bash
# 使用驗證工具
python3 collector_validator.py --map-file config/maps/map_61.64.191.74.txt

# 檢查是否使用斜線 (應該使用底線)
grep "/" config/maps/map_61.64.191.74.txt
```

### Q3: RRD檔案沒有生成
```bash
# 檢查目錄權限
ls -ld /opt/isp_monitor/data

# 檢查磁碟空間
df -h /opt/isp_monitor

# 查看錯誤日誌
tail -50 /var/log/isp_traffic/collector.log | grep ERROR
```

### Q4: 收集效能緩慢
```bash
# 查看收集時間
grep "Collection completed in" /var/log/isp_traffic/collector.log

# 調整並行參數
vi /opt/isp_monitor/config/config.ini
# 增加 max_processes

# 檢查系統資源
top
htop
```

## 📊 效能基準參考

### 收集時間
- 5,000用戶: ~1分鐘
- 10,000用戶: ~2分鐘
- 30,000用戶: ~5分鐘
- 60,000用戶: ~10分鐘 (使用並行處理)

### 資源使用
- CPU: 20-40% (單核心)
- 記憶體: 200-500MB
- 磁碟I/O: 中等
- 網路: ~50Kbps平均

### 檔案數量
- 60,000用戶 x 4層 = 240,000個RRD檔案
- 每個RRD檔案: ~100KB
- 總磁碟空間: ~24GB

## 📚 後續步驟

1. **報表系統設定**
   - 參閱 README.md 的報表系統章節
   - 設定 TOP100 流量排名
   - 設定電路壅塞分析
   - 設定速度分類統計

2. **FreeRADIUS整合**
   - 安裝 FreeRADIUS 3.0
   - 匯入認證資料庫
   - 設定設備同步

3. **監控告警**
   - 設定閾值告警
   - 配置郵件通知
   - 建立告警規則

4. **Web介面**
   - 安裝Web伺服器
   - 部署圖表介面
   - 設定用戶查詢

## 📞 支援資訊

- **完整文檔**: README.md
- **安裝指南**: INSTALL.md
- **程式架構**: CODE_DEPENDENCIES.md
- **技術支援**: jason@sonet-tw.net.tw

---

**預估總安裝時間**: 約 60 分鐘  
**建議**: 先在測試環境完成安裝和驗證，再部署到生產環境

**最後更新**: 2025-11-19  
**文件版本**: 2.0.0
