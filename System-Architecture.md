# ISP 流量監控系統 - 完整架構設計

## 系統概述

### 目標
建立一個完整的 ISP 流量監控系統，支援多種 BRAS 設備，提供多層級資料分析和豐富的統計報表。

### 設備支援
| 設備 | IP 類型 | 收集器 | 狀態 |
|-----|---------|--------|------|
| E320 | 固定+動態 | isp_traffic_collector_e320.py | ✅ 已完成 |
| ACX7024 | 固定 | isp_traffic_collector_acx.py | 🔨 待實作 |
| MX960 | 動態 | isp_traffic_collector_mx960.py | 🔨 待實作 |
| MX240 | 動態 | isp_traffic_collector_mx240.py | 🔨 待實作 |

## RRD 架構設計

### 四層架構

```
Layer 1: User Layer (VLAN 層級)
  └─ {IP}/{IP}_{slot}_{port}_{download}_{upload}_{vlan}.rrd
     用途: 個別使用者流量追蹤

Layer 2: Sum Layer (速率彙總 - 無限制)
  └─ sum/{IP}/{IP}_{slot}_{port}_{download}_{upload}_sum.rrd
     用途: 相同速率方案的總流量

Layer 3: Sum2M Layer (速率彙總 - Fair Usage)
  └─ sum2m/{IP}/{IP}_{slot}_{port}_{download}_{upload}_sum.rrd
     用途: 套用 Fair Usage Policy 後的流量

Layer 4: Circuit Layer (新增 - Circuit 彙總)
  └─ circuit/{IP}/{IP}_{interface}_circuit.rrd
     例如: circuit/61.64.191.1/61.64.191.1_ge-1-2_circuit.rrd
           circuit/10.1.1.1/10.1.1.1_xe-1-0-0_circuit.rrd
     用途: 整個 Circuit 的總流量（跨所有速率方案）
```

### RRD 檔案結構

#### Layer 1: User Layer
```bash
檔名: {IP}_{slot}_{port}_{download}_{upload}_{vlan}.rrd
範例: 61.64.191.1_1_2_35840_6144_3490.rrd

DS (Data Source):
  - 名稱: {download}_{upload}
  - 類型: COUNTER
  - 資料: ifHCOutOctets (出流量)

RRA (Round Robin Archives):
  - AVERAGE:0.5:1:4465    # 20分鐘 x 4465 = 62天
  - AVERAGE:0.5:24:564    # 8小時 x 564 = 6個月  
  - AVERAGE:0.5:144:1096  # 2天 x 1096 = 3年
  - MAX:0.5:1:4465        # 最大值，同上
  - MAX:0.5:24:564
  - MAX:0.5:144:1096
```

#### Layer 4: Circuit Layer (新增)
```bash
檔名: {IP}_{interface}_circuit.rrd
範例: 
  - 61.64.191.1_ge-1-2_circuit.rrd      (E320)
  - 10.1.1.1_xe-1-0-0_circuit.rrd       (MX)

DS (Data Source):
  - 名稱: total_traffic
  - 類型: GAUGE
  - 資料: 該 Circuit 所有用戶的總流量（bps）

額外 DS:
  - vlan_count: GAUGE (VLAN 數量)
  - user_count: GAUGE (使用者數量)
  - peak_rate: GAUGE (尖峰速率)
  - avg_rate: GAUGE (平均速率)

RRA: 同 Layer 1
```

## 收集頻率

### 時間設定
```ini
[collection]
interval = 1200           # 20 分鐘 = 1200 秒
step = 1200              # RRD step
heartbeat = 2400         # 2 x step
```

### Cron 設定
```cron
# 每 20 分鐘執行一次
*/20 * * * * /usr/bin/python3 /opt/rrdw/collector_dispatcher.py >> /var/log/rrdw/collector.log 2>&1
```

## 統計報表系統

### 報表架構

```
reports/
├── traffic_ranking/              # TOP100 流量統計
│   ├── daily_top100.py
│   ├── weekly_top100.py
│   └── monthly_top100.py
├── circuit_analysis/             # Circuit 分析
│   ├── congestion_analysis.py   # 擁塞分析
│   ├── io_statistics.py         # I/O 統計
│   └── speed_classification.py  # 速率分類
└── vlan_statistics/              # VLAN 統計
    └── vlan_count_analysis.py
```

### 報表 1: TOP100 流量統計

**功能**: 列出流量最高的 100 個使用者

**輸出格式**:
```
TOP100 客戶流量統計 - 2024年11月（月報）
========================================================================
排名  用戶代碼      BRAS            速率方案       下載流量(GB)  上傳流量(GB)
========================================================================
1     0989703334   61.64.191.1    35840_6144      1,234.56      123.45
2     0981345344   61.64.191.1    102400_40960    1,123.45      112.34
3     shinyi64518  61.64.191.1    5120_384          987.65       98.76
...
100   ...
========================================================================
```

**參數**:
- 時間範圍：日/週/月
- 排序方式：總流量/下載/上傳
- 分區過濾：可選

### 報表 2: Circuit 擁塞分析

**功能**: 分析最近 3 日的 Circuit 擁塞情況

**輸出格式**:
```
Circuit 擁塞分析報告 - 2024/11/15-17
========================================================================
Circuit          頻寬上限   實際尖峰   擁塞時數   擁塞率   平均流量
========================================================================
61.64.191.1      880 Mbps   876 Mbps   12.5 hr    17.4%    654 Mbps
ge-1/2
------------------------------------------------------------------------
  11/15 (五)     876 Mbps   4.0 hr     5.6%      645 Mbps
  11/16 (六)     823 Mbps   3.5 hr     4.9%      612 Mbps
  11/17 (日)     854 Mbps   5.0 hr     6.9%      705 Mbps
========================================================================

擁塞定義: 流量 > 頻寬上限的 95%
擁塞時數: 連續超過 15 分鐘計為擁塞
```

### 報表 3: Circuit I/O 統計

**功能**: 各 Circuit 的流入/流出統計

**輸出格式**:
```
Circuit I/O 統計報告 - 2024年11月（月報）
========================================================================
Circuit          區域      流入(TB)   流出(TB)   總計(TB)   I/O比例
========================================================================
61.64.191.1      台中      12.34      123.45     135.79     1:10
ge-1/2
------------------------------------------------------------------------
10.1.1.1         台北      23.45      234.56     258.01     1:10
xe-1/0/0
------------------------------------------------------------------------
...
========================================================================
```

### 報表 4: 速率分類統計

**功能**: 依速率方案分類的流量統計

**輸出格式**:
```
Circuit 速率分類統計 - 2024年11月（月報）
========================================================================
Circuit: 61.64.191.1 ge-1/2 (台中)
========================================================================
速率方案           用戶數   總流量(TB)   平均流量/戶   占比
========================================================================
102400_40960      150      45.67        304.47 GB     45.2%
35840_6144        200      32.45        162.25 GB     32.1%
16384_3072        300      18.90         63.00 GB     18.7%
5120_384          50        4.01         80.20 GB      4.0%
------------------------------------------------------------------------
總計              700     101.03        144.33 GB    100.0%
========================================================================
```

### 報表 5: VLAN 數量統計

**功能**: 統計各 Circuit 的 VLAN 數量變化

**輸出格式**:
```
Circuit VLAN 數量統計
========================================================================
分區: 台中
========================================================================
Circuit          上月      本月      增減      變化率
========================================================================
61.64.191.1      650       700       +50       +7.7%
ge-1/2
------------------------------------------------------------------------
10.1.1.2         450       445       -5        -1.1%
xe-1/0/1
========================================================================
總計             1,100     1,145     +45       +4.1%
========================================================================

分區: 台北
========================================================================
Circuit          上月      本月      增減      變化率
========================================================================
10.1.1.1         1,200     1,250     +50       +4.2%
ge-0/0/1
========================================================================
總計             1,200     1,250     +50       +4.2%
========================================================================

全區總計         2,300     2,395     +95       +4.1%
========================================================================
```

## 實作計劃

### Phase 1: 收集器擴充（2-3 週）

**Week 1-2: ACX/MX 收集器**
- [ ] isp_traffic_collector_acx.py
- [ ] isp_traffic_collector_mx960.py
- [ ] isp_traffic_collector_mx240.py
- [ ] 統一介面和格式
- [ ] 測試驗證

**Week 3: Circuit Layer**
- [ ] Circuit RRD 建立
- [ ] Circuit 資料彙總
- [ ] 與現有系統整合

### Phase 2: 報表系統（2-3 週）

**Week 1: 基礎報表**
- [ ] TOP100 流量統計
- [ ] Circuit I/O 統計

**Week 2: 進階分析**
- [ ] 擁塞分析
- [ ] 速率分類統計

**Week 3: VLAN 統計**
- [ ] VLAN 數量追蹤
- [ ] 分區統計

### Phase 3: 自動化與優化（1 週）

- [ ] Cron 定時執行
- [ ] Email 報表寄送
- [ ] 效能優化
- [ ] 監控告警

## 技術細節

### 收集器統一介面

```python
class BaseCollector:
    """統一的收集器基類"""
    
    def collect_device(self, device_ip, slot, port):
        """收集設備資料"""
        # 1. 載入使用者對應
        users = self.load_users()
        
        # 2. SNMP 收集
        traffic_data = self.snmp_collect(users)
        
        # 3. 寫入 Layer 1 (User)
        self.write_user_rrd(traffic_data)
        
        # 4. 寫入 Layer 2/3 (Sum/Sum2M)
        self.write_sum_rrd(traffic_data)
        
        # 5. 寫入 Layer 4 (Circuit) ← 新增
        self.write_circuit_rrd(traffic_data)
```

### Circuit 資料彙總

```python
def write_circuit_rrd(self, traffic_data):
    """寫入 Circuit RRD"""
    # 彙總該 Circuit 的所有流量
    total_rate = sum(user['rate'] for user in traffic_data)
    vlan_count = len(set(user['vlan'] for user in traffic_data))
    user_count = len(traffic_data)
    peak_rate = max(user['rate'] for user in traffic_data)
    avg_rate = total_rate / user_count if user_count > 0 else 0
    
    # 更新 Circuit RRD
    circuit_rrd = self.get_circuit_rrd_path()
    rrdtool.update(circuit_rrd, 
        f"N:{total_rate}:{vlan_count}:{user_count}:{peak_rate}:{avg_rate}")
```

### 報表資料查詢

```python
def get_top100_users(period='monthly'):
    """取得 TOP100 使用者"""
    users = []
    
    # 查詢所有 User RRD
    for rrd_file in glob.glob(f"{RRD_BASE}/**/*.rrd", recursive=True):
        # 讀取指定期間的資料
        data = rrdtool.fetch(rrd_file, 'AVERAGE', 
                            '--start', start_time, 
                            '--end', end_time)
        
        # 計算總流量
        total = calculate_total(data)
        users.append({'file': rrd_file, 'traffic': total})
    
    # 排序並取 TOP 100
    users.sort(key=lambda x: x['traffic'], reverse=True)
    return users[:100]
```

## 資料庫設計（輔助）

### 統計資料表

```sql
-- TOP100 歷史記錄
CREATE TABLE traffic_ranking (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_date DATE,
    period_type ENUM('daily', 'weekly', 'monthly'),
    rank INT,
    user_code VARCHAR(50),
    bras_ip VARCHAR(15),
    speed_profile VARCHAR(20),
    download_gb DECIMAL(12,2),
    upload_gb DECIMAL(12,2),
    total_gb DECIMAL(12,2)
);

-- Circuit 擁塞記錄
CREATE TABLE circuit_congestion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    record_date DATE,
    circuit_id VARCHAR(50),
    bandwidth_limit_mbps INT,
    peak_rate_mbps INT,
    congestion_hours DECIMAL(4,2),
    congestion_percentage DECIMAL(5,2),
    avg_rate_mbps INT
);

-- VLAN 數量歷史
CREATE TABLE vlan_statistics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    record_month DATE,
    circuit_id VARCHAR(50),
    area VARCHAR(20),
    vlan_count INT,
    user_count INT
);
```

## 檔案結構

```
rrdw/
├── collectors/                   # 收集器
│   ├── base_collector.py        # 基類
│   ├── e320_collector.py        # E320
│   ├── acx_collector.py         # ACX
│   ├── mx960_collector.py       # MX960
│   └── mx240_collector.py       # MX240
├── reports/                     # 報表
│   ├── traffic_ranking.py
│   ├── circuit_analysis.py
│   ├── congestion_analysis.py
│   └── vlan_statistics.py
├── data/                        # RRD 資料
│   ├── {IP}/                    # User Layer
│   ├── sum/{IP}/                # Sum Layer
│   ├── sum2m/{IP}/              # Sum2M Layer
│   └── circuit/{IP}/            # Circuit Layer (新)
├── config/
│   ├── config.ini
│   └── BRAS-Map.txt
└── utils/
    ├── rrd_helper.py
    └── report_helper.py
```

## 執行流程

### 收集流程（每 20 分鐘）

```bash
# Cron 執行
*/20 * * * * /opt/rrdw/bin/collect_all.sh

# collect_all.sh 內容
#!/bin/bash
python3 /opt/rrdw/collector_dispatcher.py >> /var/log/rrdw/collector.log 2>&1
```

### 報表流程（每日）

```bash
# 每日報表（凌晨 2:00）
0 2 * * * /opt/rrdw/bin/generate_daily_reports.sh

# generate_daily_reports.sh
#!/bin/bash
python3 /opt/rrdw/reports/traffic_ranking.py --period daily
python3 /opt/rrdw/reports/circuit_analysis.py --days 3
python3 /opt/rrdw/reports/congestion_analysis.py --days 3
```

### 週報/月報

```bash
# 週報（每週一 3:00）
0 3 * * 1 python3 /opt/rrdw/reports/traffic_ranking.py --period weekly

# 月報（每月 1 日 4:00）
0 4 1 * * python3 /opt/rrdw/reports/traffic_ranking.py --period monthly
0 4 1 * * python3 /opt/rrdw/reports/vlan_statistics.py --period monthly
```

## 效能估算

### 資料量

```
假設：60,000 使用者，15 個 BRAS

Layer 1 (User):    60,000 RRD × 220 KB = 13.2 GB
Layer 2 (Sum):     ~100 RRD × 220 KB = 22 MB
Layer 3 (Sum2M):   ~100 RRD × 220 KB = 22 MB  
Layer 4 (Circuit): 15 RRD × 220 KB = 3.3 MB

總計：約 13.3 GB
```

### 收集時間

```
E320 (較慢):  10 秒/port × 10 ports = 100 秒
MX/ACX (快):  3 秒/port × 20 ports = 60 秒

總收集時間：< 3 分鐘（並行）
```

### 報表產生時間

```
TOP100:           < 30 秒
Circuit 分析:     < 60 秒
VLAN 統計:        < 30 秒

總報表時間：< 2 分鐘
```

## 監控與告警

### 收集監控

```python
# 檢查收集是否成功
if collection_failed:
    send_alert("收集失敗: {device_ip}")

# 檢查收集時間
if collection_time > 600:  # 超過 10 分鐘
    send_alert("收集時間過長: {collection_time}s")
```

### 擁塞告警

```python
# 檢查 Circuit 擁塞
if congestion_rate > 0.95:  # 95% 以上
    if congestion_hours > 2:
        send_alert("Circuit 擁塞: {circuit_id}, 持續 {hours} 小時")
```

## 總結

這是一個完整的四層架構流量監控系統：

**收集層**:
- ✅ E320 收集器（已完成）
- 🔨 ACX 收集器（待實作）
- 🔨 MX960 收集器（待實作）
- 🔨 MX240 收集器（待實作）

**儲存層**:
- Layer 1: User (VLAN 級)
- Layer 2: Sum (速率級 - 無限制)
- Layer 3: Sum2M (速率級 - Fair Usage)
- Layer 4: Circuit (設備級) ← 新增

**分析層**:
- TOP100 流量統計
- Circuit 擁塞分析
- I/O 統計
- 速率分類統計
- VLAN 數量統計

**自動化**:
- 20 分鐘自動收集
- 日/週/月自動報表
- 告警通知

---

**下一步**: 開始實作 ACX/MX 收集器和 Circuit Layer
