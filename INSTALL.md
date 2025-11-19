# ISP Traffic Monitor - 快速安裝指南

## 安裝前檢查

### 系統需求
- OS: CentOS 7+ / RHEL 7+ / Ubuntu 18.04+
- Python: 3.6+
- 磁碟空間: 至少 50GB (用於RRD資料)
- 記憶體: 至少 4GB
- 網路: 可連線到所有監控設備

## 快速安裝步驟

### 步驟 1: 下載並解壓縮

```bash
# 假設您已經下載了安裝包
cd /tmp
tar xzf isp_monitor_v2.0.tar.gz
cd isp_monitor_v2.0
```

### 步驟 2: 執行相依關係檢查

```bash
# 檢查系統相依關係
python3 dependency_checker.py

# 如果有缺少的套件，生成並執行安裝腳本
python3 dependency_checker.py --generate-install-script
sudo ./install_dependencies.sh
```

### 步驟 3: 安裝系統套件 (手動安裝)

如果上述自動安裝腳本無法執行，請手動安裝：

```bash
# CentOS/RHEL
sudo yum install -y python3 python3-pip python3-devel
sudo yum install -y rrdtool rrdtool-python rrdtool-devel
sudo yum install -y net-snmp net-snmp-utils net-snmp-devel
sudo yum install -y gcc mariadb-devel

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-dev
sudo apt-get install -y rrdtool python3-rrdtool librrd-dev
sudo apt-get install -y snmp snmp-mibs-downloader libsnmp-dev
sudo apt-get install -y gcc libmariadb-dev
```

### 步驟 4: 安裝Python套件

```bash
# 升級pip
sudo pip3 install --upgrade pip

# 安裝必要套件
sudo pip3 install pysnmp>=4.4.0
sudo pip3 install pymysql
sudo pip3 install configparser
```

### 步驟 5: 建立目錄結構

```bash
# 建立主目錄
sudo mkdir -p /opt/isp_monitor

# 建立子目錄
sudo mkdir -p /opt/isp_monitor/config/maps
sudo mkdir -p /opt/isp_monitor/collectors
sudo mkdir -p /opt/isp_monitor/lib
sudo mkdir -p /opt/isp_monitor/reports
sudo mkdir -p /opt/isp_monitor/data/{sum,sum2m,circuit}
sudo mkdir -p /opt/isp_monitor/logs
sudo mkdir -p /opt/isp_monitor/tools

# 建立日誌目錄
sudo mkdir -p /var/log/isp_traffic

# 建立監控用戶 (可選)
sudo useradd -r -s /bin/bash -d /opt/isp_monitor monitor
```

### 步驟 6: 複製程式檔案

```bash
# 複製所有程式到目標目錄
sudo cp -r collectors/* /opt/isp_monitor/collectors/
sudo cp -r lib/* /opt/isp_monitor/lib/
sudo cp -r reports/* /opt/isp_monitor/reports/
sudo cp -r tools/* /opt/isp_monitor/tools/

# 設定執行權限
sudo chmod +x /opt/isp_monitor/collectors/*.py
sudo chmod +x /opt/isp_monitor/reports/*.py
sudo chmod +x /opt/isp_monitor/tools/*.py
```

### 步驟 7: 配置設定檔

```bash
# 複製配置範例檔案
sudo cp config.ini.example /opt/isp_monitor/config/config.ini
sudo cp BRAS-Map.txt.example /opt/isp_monitor/config/BRAS-Map.txt

# 編輯配置檔案
sudo vi /opt/isp_monitor/config/config.ini
```

#### config.ini 必要設定項目

```ini
[base]
root_path = /opt/isp_monitor

[snmp]
default_community = public  # 修改為您的SNMP community
timeout = 5
retries = 2

[rrd]
base_dir = /opt/isp_monitor/data
sum_dir = /opt/isp_monitor/data/sum
sum2m_dir = /opt/isp_monitor/data/sum2m
circuit_dir = /opt/isp_monitor/data/circuit
step = 1200  # 20分鐘

[logging]
log_dir = /var/log/isp_traffic
log_level = INFO
```

### 步驟 8: 準備BRAS-Map.txt

編輯 `/opt/isp_monitor/config/BRAS-Map.txt`，填入您的設備資訊：

```
Area	DeviceType	IP	CircuitID	Slot(Fpc)	Port	InterfaceType	BandwidthMax	IfAssign	Pic
taipei_4	3	61.64.191.74	223GD99004	1	0	GE	880	0	0
taipei_5	2	61.64.191.76	223GD99018	1	1	XE	880	0	0
south_1	1	61.64.191.78	223GD99019	1	2	XE	880	0	2
center_1	4	61.64.191.81	223GD99020	0	0	XE	880	0	0
```

**DeviceType對應表**:
- 1 = MX960
- 2 = MX240
- 3 = E320
- 4 = ACX7024

### 步驟 9: 生成Map檔案範本

```bash
# 使用工具自動生成所有設備的map檔案範本
cd /opt/isp_monitor
python3 tools/generate_map_template.py \
    -b config/BRAS-Map.txt \
    -o config/maps/ \
    -n 10
```

這會為每個設備IP生成對應的 `map_{ip}.txt` 檔案範本。

### 步驟 10: 編輯Map檔案

為每個設備編輯map檔案，填入實際用戶資料：

```bash
sudo vi /opt/isp_monitor/config/maps/map_61.64.191.74.txt
```

格式範例：
```
username,slot_port_vpi_vci,downstream_upstream,user_id
0989703334,1_2_0_3490,35840_6144,587247394
0981345344,3_1_0_3441,102400_40960,587272279
```

**重要**: 
- 使用底線 `_` 分隔，不使用斜線 `/`
- 頻寬單位為 kbps

### 步驟 11: 驗證配置

```bash
# 執行完整驗證
cd /opt/isp_monitor
python3 tools/collector_validator.py --full

# 驗證特定map檔案
python3 tools/collector_validator.py \
    --map-file config/maps/map_61.64.191.74.txt

# 測試SNMP連線
python3 tools/collector_validator.py \
    --test-snmp 61.64.191.74 \
    --test-interfaces
```

### 步驟 12: 測試收集器

```bash
# 手動執行一次收集
cd /opt/isp_monitor
python3 collectors/collector_dispatcher.py

# 查看日誌
tail -f /var/log/isp_traffic/collector.log

# 檢查RRD檔案是否生成
ls -lh data/*.rrd
ls -lh data/sum/*.rrd
ls -lh data/sum2m/*.rrd
ls -lh data/circuit/*.rrd
```

### 步驟 13: 設定權限

```bash
# 設定目錄擁有者
sudo chown -R monitor:monitor /opt/isp_monitor
sudo chown -R monitor:monitor /var/log/isp_traffic

# 設定目錄權限
sudo chmod 755 /opt/isp_monitor
sudo chmod 755 /opt/isp_monitor/collectors
sudo chmod 755 /opt/isp_monitor/lib
sudo chmod 755 /opt/isp_monitor/reports
sudo chmod 775 /opt/isp_monitor/data
sudo chmod 775 /opt/isp_monitor/data/sum
sudo chmod 775 /opt/isp_monitor/data/sum2m
sudo chmod 775 /opt/isp_monitor/data/circuit
sudo chmod 775 /opt/isp_monitor/logs
sudo chmod 775 /var/log/isp_traffic

# 設定配置檔案權限
sudo chmod 640 /opt/isp_monitor/config/config.ini
sudo chmod 640 /opt/isp_monitor/config/BRAS-Map.txt
sudo chmod 640 /opt/isp_monitor/config/maps/*.txt
```

### 步驟 14: 設定自動執行 (Crontab)

```bash
# 切換到monitor用戶
sudo su - monitor

# 編輯crontab
crontab -e

# 加入以下內容 (每20分鐘執行一次)
*/20 * * * * cd /opt/isp_monitor && python3 collectors/collector_dispatcher.py >> /var/log/isp_traffic/cron.log 2>&1

# 儲存並退出
```

### 步驟 15: 驗證自動執行

```bash
# 等待20分鐘後檢查
tail -f /var/log/isp_traffic/cron.log

# 檢查RRD檔案更新時間
ls -lht /opt/isp_monitor/data/*.rrd | head -10

# 查看收集統計
grep "Collection completed" /var/log/isp_traffic/collector.log
```

## 效能調優建議

### 針對大量用戶 (>10,000)

編輯 `config.ini`:

```ini
[collection]
fork_threshold = 5000
max_processes = 8

[snmp]
timeout = 10
retries = 3
```

### 針對E320設備

```ini
[device_timeouts]
e320 = 10
e320_bulk_size = 20
```

### 針對MX/ACX設備

```ini
[device_timeouts]
mx240 = 5
mx960 = 5
acx7024 = 5

[collection]
mx960_max_workers = 8
mx240_max_workers = 4
acx_max_workers = 4
```

## 常見問題排除

### Q1: SNMP連線失敗

```bash
# 檢查網路連線
ping 61.64.191.74

# 測試SNMP
snmpwalk -v2c -c public 61.64.191.74 sysDescr.0

# 檢查防火牆
sudo iptables -L | grep 161
```

### Q2: RRD檔案沒有生成

```bash
# 檢查目錄權限
ls -ld /opt/isp_monitor/data

# 檢查磁碟空間
df -h /opt/isp_monitor

# 查看錯誤日誌
tail -50 /var/log/isp_traffic/collector.log | grep ERROR
```

### Q3: Map檔案格式錯誤

```bash
# 驗證格式
python3 tools/collector_validator.py \
    --map-file config/maps/map_61.64.191.74.txt

# 檢查分隔符號是否使用底線
grep "/" config/maps/map_61.64.191.74.txt
# 應該沒有任何輸出
```

### Q4: 收集效能緩慢

```bash
# 查看收集時間
grep "Collection completed in" /var/log/isp_traffic/collector.log

# 如果超過5分鐘，調整並行參數
vi /opt/isp_monitor/config/config.ini
# 增加 max_processes

# 檢查系統資源
top
htop
```

## 監控與維護

### 每日檢查

```bash
# 檢查收集器狀態
grep "ERROR" /var/log/isp_traffic/collector.log

# 檢查最新的RRD檔案
find /opt/isp_monitor/data -name "*.rrd" -mtime -1 | wc -l
```

### 每週維護

```bash
# 清理舊日誌 (保留30天)
find /var/log/isp_traffic -name "*.log.*" -mtime +30 -delete

# 備份配置
tar czf /backup/isp_monitor_config_$(date +%Y%m%d).tar.gz \
    /opt/isp_monitor/config/
```

### 每月維護

```bash
# 檢查磁碟使用量
du -sh /opt/isp_monitor/data/*

# 生成效能報告
python3 reports/report_system_health.py
```

## 下一步

1. **設定報表系統**: 請參閱 README.md 的報表系統章節
2. **整合FreeRADIUS**: 如需認證整合，請參閱 FreeRADIUS 整合指南
3. **設定告警**: 配置閾值告警和郵件通知
4. **建立圖表**: 設定Web介面展示流量圖表

## 取得幫助

- **技術文件**: 詳見 README.md
- **故障排除**: 詳見 README.md 的故障排除章節
- **聯絡支援**: jason@sonet-tw.net.tw

---

**安裝完成！**

您的ISP Traffic Monitor系統現在應該已經開始收集流量資料了。
請檢查 `/var/log/isp_traffic/collector.log` 確認收集正常運作。
