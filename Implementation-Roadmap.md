# ISP 流量監控系統 - 實作路線圖

## 📋 需求總覽

### 已完成 ✅
1. **E320 收集器** - isp_traffic_collector_e320.py（參考）
2. **BRAS Map 系統** - 智能調度器
3. **Map File 讀取器** - 100% E320 相容
4. **基礎收集器類** - base_collector.py（四層 RRD 架構）
5. **TOP100 流量報表** - traffic_ranking_report.py

### 待實作 🔨

#### 1. 收集器實作（2-3 週）
- [ ] **isp_traffic_collector_acx.py** - ACX7024 固定 IP 收集器
- [ ] **isp_traffic_collector_mx960.py** - MX960 動態 IP 收集器
- [ ] **isp_traffic_collector_mx240.py** - MX240 動態 IP 收集器
- [ ] **整合測試** - 四種設備統一測試

#### 2. RRD 架構擴充（1 週）
- [x] **Layer 4: Circuit RRD** - 已在 base_collector.py 實作
- [ ] **Circuit 資料彙總** - 測試和驗證
- [ ] **VLAN 數量追蹤** - 實作統計功能

#### 3. 統計報表系統（2-3 週）
- [x] **TOP100 流量統計** - 已完成（日/週/月）
- [ ] **Circuit 擁塞分析** - 最近 3 日連續擁塞分析
- [ ] **Circuit I/O 統計** - 流入/流出統計
- [ ] **速率分類統計** - 依速率方案分類
- [ ] **VLAN 數量統計** - 月度增減分析

#### 4. 自動化與部署（1 週）
- [ ] **Cron 定時執行** - 20 分鐘收集
- [ ] **報表自動產生** - 日/週/月自動排程
- [ ] **Email 報表寄送** - 自動寄送給相關人員
- [ ] **監控告警** - 收集失敗、擁塞告警

## 🎯 Phase 1: 收集器實作（2-3 週）

### Week 1-2: ACX/MX 收集器

#### ACX7024 收集器特點
```python
# isp_traffic_collector_acx.py

class ACXCollector(BaseCollector):
    """ACX7024 固定 IP 收集器"""
    
    def load_users(self, device_ip, slot, port):
        """從固定 IP 配置載入使用者"""
        # ACX 通常用於固定 IP 服務
        # 可能需要不同的配置檔案格式
        pass
    
    def snmp_collect(self, device_ip, users):
        """SNMP 收集（與 MX 類似）"""
        # 使用 SNMP Walk
        # 三段式介面名稱: ge-0/0/2.200
        pass
    
    def get_interface_name(self, slot, port):
        """介面名稱: ge-{slot}/{pic}/{port}"""
        return f"ge-{slot}-0-{port}"  # ACX 通常 pic=0
```

#### MX960 收集器特點
```python
# isp_traffic_collector_mx960.py

class MX960Collector(BaseCollector):
    """MX960 動態 IP 收集器"""
    
    def load_users(self, device_ip, slot, port):
        """從動態 IP 配置載入（PPPoE）"""
        # 支援 PPPoE 動態分配
        # 需要從 RADIUS 或其他來源取得當前分配
        pass
    
    def snmp_collect(self, device_ip, users):
        """SNMP Walk 收集"""
        # 三段式介面: ge-0/0/1.100
        pass
    
    def get_interface_name(self, slot, port):
        """介面名稱: ge-{slot}/{pic}/{port}"""
        return f"ge-{slot}-0-{port}"
```

#### MX240 收集器特點
```python
# isp_traffic_collector_mx240.py

class MX240Collector(BaseCollector):
    """MX240 動態 IP 收集器（PPPoE 支援）"""
    
    def load_users(self, device_ip, slot, port):
        """PPPoE 使用者載入"""
        # 與 MX960 類似，但可能有不同的卡槽配置
        pass
    
    def snmp_collect(self, device_ip, users):
        """SNMP Walk 收集"""
        # 三段式介面: xe-1/0/0.400（10G 介面）
        pass
    
    def get_interface_name(self, slot, port):
        """介面名稱: xe-{slot}/{pic}/{port}"""
        return f"xe-{slot}-0-{port}"
```

### Week 3: 整合與測試

#### 統一調度器擴充
```python
# collector_dispatcher.py 擴充

class CollectorDispatcher:
    def dispatch_task(self, task):
        if task.device_type == DEVICE_TYPE_E320:
            from isp_traffic_collector_e320 import E320Collector
            collector = E320Collector(...)
        elif task.device_type == DEVICE_TYPE_ACX7024:
            from isp_traffic_collector_acx import ACXCollector
            collector = ACXCollector(...)
        elif task.device_type == DEVICE_TYPE_MX960:
            from isp_traffic_collector_mx960 import MX960Collector
            collector = MX960Collector(...)
        elif task.device_type == DEVICE_TYPE_MX240:
            from isp_traffic_collector_mx240 import MX240Collector
            collector = MX240Collector(...)
        
        return collector.collect_device(...)
```

## 🎯 Phase 2: 報表系統實作（2-3 週）

### Week 1: Circuit 擁塞分析

#### 功能需求
- 最近 3 日的 Circuit 流量分析
- 識別連續擁塞時段（>15 分鐘）
- 計算擁塞時數和占比
- 輸出 HTML/CSV/Text 格式

#### 實作要點
```python
# circuit_congestion_analysis.py

class CongestionAnalyzer:
    def analyze_circuit(self, circuit_rrd, days=3):
        """分析 Circuit 擁塞情況"""
        # 1. 讀取最近 N 天的 Circuit RRD
        # 2. 取得頻寬上限（從 BRAS-Map.txt）
        # 3. 計算每個時段的流量占比
        # 4. 識別擁塞時段（>95%）
        # 5. 統計連續擁塞時數
        pass
    
    def is_congested(self, rate_mbps, limit_mbps, threshold=0.95):
        """判斷是否擁塞"""
        return (rate_mbps / limit_mbps) >= threshold
    
    def calculate_congestion_hours(self, data_points):
        """計算連續擁塞時數"""
        continuous_hours = 0
        current_streak = 0
        
        for point in data_points:
            if self.is_congested(point.rate, point.limit):
                current_streak += point.step / 3600  # 轉為小時
            else:
                if current_streak >= 0.25:  # 至少 15 分鐘
                    continuous_hours += current_streak
                current_streak = 0
        
        return continuous_hours
```

### Week 2: Circuit I/O 與速率統計

#### Circuit I/O 統計
```python
# circuit_io_statistics.py

class CircuitIOStatistics:
    def collect_circuit_stats(self, period='monthly'):
        """收集 Circuit I/O 統計"""
        # 1. 掃描所有 Circuit RRD
        # 2. 計算總流入/流出
        # 3. 依區域分組
        # 4. 計算 I/O 比例
        pass
    
    def calculate_io_ratio(self, inbound_gb, outbound_gb):
        """計算 I/O 比例"""
        if inbound_gb == 0:
            return "N/A"
        ratio = outbound_gb / inbound_gb
        return f"1:{ratio:.1f}"
```

#### 速率分類統計
```python
# speed_classification_statistics.py

class SpeedClassificationStats:
    def analyze_circuit_by_speed(self, circuit_id, period='monthly'):
        """依速率方案分析 Circuit"""
        # 1. 取得該 Circuit 的所有 Sum RRD
        # 2. 依速率方案分組
        # 3. 計算各方案的總流量
        # 4. 計算占比
        pass
    
    def generate_speed_distribution(self, circuit_id):
        """產生速率分布圖"""
        # 可選：產生圖表
        pass
```

### Week 3: VLAN 數量統計

#### VLAN 統計功能
```python
# vlan_statistics.py

class VLANStatistics:
    def track_vlan_count(self):
        """追蹤 VLAN 數量"""
        # 1. 從 Circuit RRD 讀取 vlan_count DS
        # 2. 記錄每日/每月的 VLAN 數量
        # 3. 儲存到資料庫或檔案
        pass
    
    def compare_monthly(self, current_month, last_month):
        """比較月度 VLAN 數量"""
        # 1. 取得上月和本月的 VLAN 數量
        # 2. 計算增減
        # 3. 依分區分組
        pass
    
    def generate_area_report(self):
        """產生分區 VLAN 統計報表"""
        # 依 BRAS-Map.txt 中的 area 欄位分組
        pass
```

## 🎯 Phase 3: 自動化與部署（1 週）

### Cron 排程設定

#### 收集排程
```cron
# /etc/cron.d/isp_traffic_collector

# 每 20 分鐘執行收集
*/20 * * * * /usr/bin/python3 /opt/rrdw/collector_dispatcher.py >> /var/log/rrdw/collector.log 2>&1

# 檢查收集狀態
25 * * * * /opt/rrdw/bin/check_collection_status.sh
```

#### 報表排程
```cron
# /etc/cron.d/isp_traffic_reports

# 每日報表（凌晨 2:00）
0 2 * * * /opt/rrdw/bin/generate_daily_reports.sh >> /var/log/rrdw/reports.log 2>&1

# 週報（每週一 3:00）
0 3 * * 1 /opt/rrdw/bin/generate_weekly_reports.sh >> /var/log/rrdw/reports.log 2>&1

# 月報（每月 1 日 4:00）
0 4 1 * * /opt/rrdw/bin/generate_monthly_reports.sh >> /var/log/rrdw/reports.log 2>&1

# 擁塞分析（每日 5:00）
0 5 * * * /usr/bin/python3 /opt/rrdw/reports/circuit_congestion_analysis.py --days 3 >> /var/log/rrdw/congestion.log 2>&1
```

### 自動報表寄送

#### Email 寄送腳本
```bash
#!/bin/bash
# send_reports.sh

REPORT_DATE=$(date +%Y%m%d)
REPORT_DIR="/opt/rrdw/reports"
EMAIL_TO="network-team@example.com"

# 日報
mail -s "ISP 流量監控 - 日報 ${REPORT_DATE}" \
     -a "${REPORT_DIR}/top100_daily_${REPORT_DATE}.html" \
     ${EMAIL_TO} < ${REPORT_DIR}/daily_summary.txt

# 擁塞警告
CONGESTION_COUNT=$(grep "擁塞" ${REPORT_DIR}/congestion_${REPORT_DATE}.txt | wc -l)
if [ $CONGESTION_COUNT -gt 0 ]; then
    mail -s "⚠️ Circuit 擁塞警告 - ${REPORT_DATE}" \
         -a "${REPORT_DIR}/congestion_${REPORT_DATE}.html" \
         ${EMAIL_TO} < ${REPORT_DIR}/congestion_${REPORT_DATE}.txt
fi
```

### 監控告警

#### 收集監控
```python
# monitor_collection.py

class CollectionMonitor:
    def check_collection_status(self):
        """檢查收集狀態"""
        # 1. 檢查最後收集時間
        # 2. 如果超過 30 分鐘未收集，發送告警
        # 3. 檢查收集成功率
        # 4. 如果失敗率 > 10%，發送告警
        pass
    
    def send_alert(self, message):
        """發送告警"""
        # Email
        # SMS
        # Slack
        pass
```

#### 擁塞告警
```python
# congestion_alert.py

class CongestionAlert:
    def check_congestion_threshold(self):
        """檢查擁塞閾值"""
        # 1. 掃描所有 Circuit
        # 2. 檢查即時流量
        # 3. 如果 > 95% 持續 30 分鐘，發送告警
        pass
```

## 📁 完整檔案結構

```
rrdw/
├── bin/                                 # 執行腳本
│   ├── collect_all.sh                   # 總收集腳本
│   ├── generate_daily_reports.sh        # 日報產生
│   ├── generate_weekly_reports.sh       # 週報產生
│   ├── generate_monthly_reports.sh      # 月報產生
│   └── send_reports.sh                  # 報表寄送
│
├── collectors/                          # 收集器
│   ├── base_collector.py               # ✅ 基類
│   ├── e320_collector.py               # ✅ E320（參考現有）
│   ├── acx_collector.py                # 🔨 ACX7024
│   ├── mx960_collector.py              # 🔨 MX960
│   └── mx240_collector.py              # 🔨 MX240
│
├── reports/                            # 報表系統
│   ├── traffic_ranking_report.py       # ✅ TOP100 流量
│   ├── circuit_congestion_analysis.py  # 🔨 擁塞分析
│   ├── circuit_io_statistics.py        # 🔨 I/O 統計
│   ├── speed_classification_stats.py   # 🔨 速率分類
│   └── vlan_statistics.py              # 🔨 VLAN 統計
│
├── monitoring/                         # 監控
│   ├── collection_monitor.py           # 收集監控
│   └── congestion_alert.py             # 擁塞告警
│
├── config/                             # 設定
│   ├── config.ini                      # 主設定檔
│   └── BRAS-Map.txt                    # 設備對應表
│
├── maps/                               # Map Files
│   └── map_{IP}.txt                    # 各設備 Map File
│
├── data/                               # RRD 資料
│   ├── {IP}/                           # Layer 1: User
│   ├── sum/{IP}/                       # Layer 2: Sum
│   ├── sum2m/{IP}/                     # Layer 3: Sum2M
│   └── circuit/{IP}/                   # Layer 4: Circuit
│
├── logs/                               # 日誌
│   ├── collector.log
│   ├── reports.log
│   └── congestion.log
│
└── utils/                              # 工具
    ├── rrd_helper.py
    ├── report_helper.py
    └── email_helper.py
```

## 📊 資料流程圖

```
[BRAS-Map.txt] ────┐
                   │
[Map Files]  ──────┼───→ [Collector Dispatcher]
                   │             │
[RADIUS DB]  ──────┘             │
                                 ↓
                    ┌────────────────────────┐
                    │  Device Collectors      │
                    │  - E320 (Map File)      │
                    │  - ACX  (Config)        │
                    │  - MX960 (SNMP Walk)    │
                    │  - MX240 (SNMP Walk)    │
                    └────────────────────────┘
                                 │
                                 ↓
                    ┌────────────────────────┐
                    │  Four-Layer RRD        │
                    │  Layer 1: User (VLAN)  │
                    │  Layer 2: Sum (Speed)  │
                    │  Layer 3: Sum2M (FUP)  │
                    │  Layer 4: Circuit      │
                    └────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ↓                         ↓
          ┌──────────────────┐      ┌──────────────────┐
          │  Report System    │      │  Monitoring      │
          │  - TOP100         │      │  - Collection    │
          │  - Congestion     │      │  - Congestion    │
          │  - I/O Stats      │      │  - Alerts        │
          │  - Speed Class    │      └──────────────────┘
          │  - VLAN Count     │
          └──────────────────┘
                    │
                    ↓
          ┌──────────────────┐
          │  Email Reports    │
          │  - Daily          │
          │  - Weekly         │
          │  - Monthly        │
          └──────────────────┘
```

## ⏱️ 時間估算

### Phase 1: 收集器（2-3 週）
- ACX 收集器: 3 天
- MX960 收集器: 3 天
- MX240 收集器: 3 天
- 整合測試: 3 天
- 緩衝時間: 2 天

### Phase 2: 報表系統（2-3 週）
- 擁塞分析: 3 天
- I/O 統計: 2 天
- 速率分類: 2 天
- VLAN 統計: 3 天
- 測試與調整: 4 天

### Phase 3: 自動化（1 週）
- Cron 設定: 1 天
- Email 寄送: 1 天
- 監控告警: 2 天
- 文件撰寫: 1 天
- 部署測試: 2 天

**總計: 5-7 週**

## ✅ 驗收標準

### 收集器驗收
- [ ] 所有設備類型能正常收集
- [ ] 20 分鐘收集週期穩定
- [ ] 失敗率 < 1%
- [ ] 收集時間 < 10 分鐘
- [ ] RRD 檔案正確產生

### 報表系統驗收
- [ ] TOP100 報表每日自動產生
- [ ] 擁塞分析準確識別問題 Circuit
- [ ] I/O 統計數據正確
- [ ] 速率分類統計完整
- [ ] VLAN 統計月度比較正確

### 自動化驗收
- [ ] Cron 排程正常執行
- [ ] 報表自動寄送
- [ ] 監控告警及時觸發
- [ ] 日誌記錄完整

## 🚀 快速開始（開發人員）

### 1. 環境準備
```bash
cd /opt/rrdw
pip3 install -r requirements.txt
```

### 2. 設定檔案
```bash
cp config/config.ini.example config/config.ini
cp config/BRAS-Map.txt.example config/BRAS-Map.txt
# 編輯設定檔
```

### 3. 測試收集
```bash
# 測試單一設備
python3 collectors/e320_collector.py 61.64.191.1 1 2

# 測試調度器
python3 collector_dispatcher.py --bras-ip 61.64.191.1
```

### 4. 測試報表
```bash
# 產生 TOP100 報表
python3 reports/traffic_ranking_report.py --period daily --format html
```

### 5. 部署到生產
```bash
# 安裝 Cron 任務
sudo cp cron.d/* /etc/cron.d/

# 檢查狀態
sudo systemctl status cron
```

## 📞 支援

- **文件**: System-Architecture.md
- **收集器**: base_collector.py
- **報表**: traffic_ranking_report.py
- **調度器**: collector_dispatcher.py

---

**狀態**: 📋 Phase 1 規劃完成，核心組件已實作  
**下一步**: 實作 ACX/MX 收集器  
**預計完成**: 5-7 週
