# ISP 流量監控系統 - 完整架構設計

## 📋 系統需求總覽

### 1. 收集器需求

| 設備類型 | IP 類型 | 收集器 | 格式參考 |
|---------|---------|--------|---------|
| **E320** | 固定/動態 | ✅ isp_traffic_collector_e320.py | 已完成 |
| **ACX** | 固定 | 🔨 isp_traffic_collector_acx.py | 依 E320 格式 |
| **MX960** | 動態 | 🔨 isp_traffic_collector_mx960.py | 依 E320 格式 |
| **MX240** | 動態 | 🔨 isp_traffic_collector_mx240.py | 依 E320 格式 |

### 2. RRD 結構設計

#### 現有結構（E320）
```
Layer 1 (User): {IP}_{slot}_{port}_{download}_{upload}_{vlan}.rrd
Layer 2 (Sum): {IP}_{slot}_{port}_{download}_{upload}_sum.rrd
Layer 3 (Sum2M): {IP}_{slot}_{port}_{download}_{upload}_sum.rrd (Fair Usage)
```

#### 新增結構（Circuit 層級）
```
Layer 4 (Circuit): {IP}_{circuit_interface}_circuit.rrd
範例:
  - 61.64.191.1_ge-1-2_circuit.rrd
  - 10.1.1.1_xe-0-0-1_circuit.rrd
```

### 3. 完整 RRD 架構

```
data/
├── {IP}/                           # Layer 1: 個別用戶 (VLAN)
│   ├── {IP}_{s}_{p}_{d}_{u}_{vlan}.rrd
│   └── ...
├── sum/{IP}/                       # Layer 2: 速率彙總（無限制）
│   ├── {IP}_{s}_{p}_{d}_{u}_sum.rrd
│   └── ...
├── sum2m/{IP}/                     # Layer 3: 速率彙總（Fair Usage）
│   ├── {IP}_{s}_{p}_{d}_{u}_sum.rrd
│   └── ...
└── circuit/{IP}/                   # Layer 4: Circuit 彙總 ⭐ 新增
    ├── {IP}_ge-1-2_circuit.rrd    # E320: ge-1/2
    ├── {IP}_xe-0-0-1_circuit.rrd  # MX: xe-0/0/1
    └── ...
```

### 4. 收集頻率

```bash
# Cron 設定 - 每 20 分鐘執行一次
*/20 * * * * /usr/bin/python3 /opt/rrdw/collector_dispatcher.py
```

**RRD Step**: 1200 秒（20 分鐘）

### 5. 統計報表需求

#### 5.1 客戶流量統計
```
報表: top100_traffic_report.py
頻率: 每日/每週/每月
內容:
  - TOP 100 客戶流量排名
  - 下載/上傳流量
  - 平均速率
  - 尖峰速率
  - 速率方案
```

#### 5.2 Circuit 速率統計（最近三日）
```
報表: circuit_congestion_report.py
頻率: 每日
內容:
  - Circuit 名稱（ip+介面）
  - 連續擁塞時數
  - 流量上限（頻寬）
  - 實際流量（平均/尖峰）
  - 使用率 (%)
  - 擁塞時段
```

#### 5.3 Circuit 流入/流出統計
```
報表: circuit_io_statistics.py
頻率: 每日/每週/每月
內容:
  - 各 Circuit 流入流量
  - 各 Circuit 流出流量
  - 流入/流出比例
  - 時段分布
```

#### 5.4 Circuit 速率分類統計
```
報表: circuit_speed_classification.py
頻率: 每日/每週/每月
內容:
  - 各 Circuit 下載速率分類
    * 5M/384K
    * 16M/3M
    * 35M/6M
    * 100M/40M
  - 各速率用戶數
  - 各速率總流量
```

#### 5.5 Circuit VLAN 數量統計
```
報表: circuit_vlan_statistics.py
頻率: 每月
內容:
  - 各 Circuit VLAN 數量
  - 上月/本月對比
  - 增減數量
  - 依分區 Group
  - 成長率分析
```

## 🏗️ 系統架構

### 資料流程

```
Step 1: 資料收集（每 20 分鐘）
    ↓
BRAS-Map.txt → collector_dispatcher.py
    ↓
依設備類型調度:
  - E320 → isp_traffic_collector_e320.py
  - ACX → isp_traffic_collector_acx.py
  - MX960 → isp_traffic_collector_mx960.py
  - MX240 → isp_traffic_collector_mx240.py
    ↓
SNMP 收集 → 寫入 RRD
  - Layer 1: User VLAN
  - Layer 2: Speed Sum
  - Layer 3: Speed Sum2M
  - Layer 4: Circuit ⭐
    ↓
Step 2: 報表產生（定時）
    ↓
讀取 RRD → 分析統計 → 產生報表
  - HTML 報表
  - CSV 匯出
  - 圖表視覺化
```

### 目錄結構

```
rrdw/
├── config/
│   ├── config.ini              # 主設定檔
│   └── cron.d/
│       ├── collector.cron      # 收集器 cron
│       └── reports.cron        # 報表 cron
├── collectors/
│   ├── collector_dispatcher.py      # 調度器
│   ├── isp_traffic_collector_e320.py   # E320 收集器
│   ├── isp_traffic_collector_acx.py    # ACX 收集器 ⭐ 新增
│   ├── isp_traffic_collector_mx960.py  # MX960 收集器 ⭐ 新增
│   └── isp_traffic_collector_mx240.py  # MX240 收集器 ⭐ 新增
├── lib/
│   ├── bras_map_reader.py      # BRAS Map 讀取器
│   ├── map_file_reader.py      # Map File 讀取器
│   └── rrd_helper.py           # RRD 輔助工具 ⭐ 新增
├── reports/
│   ├── top100_traffic_report.py           # TOP100 流量報表 ⭐ 新增
│   ├── circuit_congestion_report.py       # Circuit 擁塞報表 ⭐ 新增
│   ├── circuit_io_statistics.py           # Circuit I/O 統計 ⭐ 新增
│   ├── circuit_speed_classification.py    # 速率分類統計 ⭐ 新增
│   └── circuit_vlan_statistics.py         # VLAN 統計 ⭐ 新增
├── data/
│   ├── {IP}/           # Layer 1: User
│   ├── sum/{IP}/       # Layer 2: Speed Sum
│   ├── sum2m/{IP}/     # Layer 3: Speed Sum2M
│   └── circuit/{IP}/   # Layer 4: Circuit ⭐ 新增
├── output/
│   ├── reports/        # HTML 報表
│   ├── csv/            # CSV 匯出
│   └── graphs/         # 圖表
├── maps/
│   └── map_{IP}.txt    # Map Files
├── BRAS-Map.txt
└── README.md
```

## 🔧 收集器設計

### E320 收集器（已有）

**特點**:
- 使用 Map File + ifindex
- 支援固定/動態 IP
- 三層 RRD 結構

**新增 Circuit 層級**:
```python
# 在現有基礎上新增
def create_circuit_rrd(self, bras_ip, slot, port, bandwidth):
    """建立 Circuit RRD"""
    circuit_name = f"ge-{slot}-{port}"
    rrd_path = f"circuit/{bras_ip}/{bras_ip}_{circuit_name}_circuit.rrd"
    
    # 建立 GAUGE 類型 RRD
    rrdtool.create(
        rrd_path,
        '--step', '1200',
        'DS:in_bits:GAUGE:2400:0:U',
        'DS:out_bits:GAUGE:2400:0:U',
        'RRA:AVERAGE:0.5:1:4465',    # 20min for 62 days
        'RRA:AVERAGE:0.5:72:730',    # 1 day for 2 years
        'RRA:MAX:0.5:1:4465',
        'RRA:MAX:0.5:72:730'
    )

def update_circuit_rrd(self, bras_ip, slot, port, total_in_bits, total_out_bits):
    """更新 Circuit RRD"""
    circuit_name = f"ge-{slot}-{port}"
    rrd_path = f"circuit/{bras_ip}/{bras_ip}_{circuit_name}_circuit.rrd"
    
    timestamp = int(time.time())
    timestamp = timestamp - (timestamp % 1200)
    
    rrdtool.update(rrd_path, f"{timestamp}:{total_in_bits}:{total_out_bits}")
```

### MX/ACX 收集器（新增）

**共同特點**:
- 使用 SNMP Walk 取得所有介面
- 介面名稱三段式 (xe-0/0/1 或 ge-0/0/1)
- 支援動態/固定 IP
- 四層 RRD 結構（含 Circuit）

**實作邏輯**:
```python
class MXACXCollector:
    def collect_device(self, bras_ip, slot, port):
        # 1. SNMP Walk 取得所有介面
        interfaces = self.snmp_walk_interfaces(bras_ip)
        
        # 2. 篩選指定 slot/port 的介面
        target_interfaces = self.filter_interfaces(
            interfaces, slot, port
        )
        
        # 3. 收集流量資料
        traffic_data = {}
        for interface in target_interfaces:
            vlan = self.parse_vlan(interface)
            in_octets, out_octets = self.get_traffic(bras_ip, interface)
            traffic_data[vlan] = (in_octets, out_octets)
        
        # 4. 從資料庫查詢速率資訊
        users = self.load_users_from_db(bras_ip, slot, port)
        
        # 5. 寫入四層 RRD
        self.write_user_rrd(traffic_data, users)      # Layer 1
        self.write_speed_sum_rrd(traffic_data, users) # Layer 2 & 3
        self.write_circuit_rrd(traffic_data)           # Layer 4 ⭐
```

## 📊 報表系統設計

### 報表架構

```python
# reports/base_report.py
class BaseReport:
    """報表基類"""
    
    def __init__(self, rrd_base_dir):
        self.rrd_base_dir = rrd_base_dir
    
    def read_rrd_data(self, rrd_path, start_time, end_time):
        """讀取 RRD 資料"""
        pass
    
    def generate_html(self, data, output_file):
        """產生 HTML 報表"""
        pass
    
    def generate_csv(self, data, output_file):
        """產生 CSV 報表"""
        pass
    
    def generate_graph(self, data, output_file):
        """產生圖表"""
        pass
```

### 報表 1: TOP100 客戶流量

```python
# reports/top100_traffic_report.py
class Top100TrafficReport(BaseReport):
    """TOP100 客戶流量報表"""
    
    def generate(self, period='daily'):
        """
        產生 TOP100 報表
        
        Args:
            period: 'daily', 'weekly', 'monthly'
        """
        # 1. 讀取所有用戶 RRD
        all_users = self.scan_user_rrds()
        
        # 2. 計算每個用戶的總流量
        user_traffic = []
        for user_rrd in all_users:
            total_in, total_out = self.calculate_traffic(
                user_rrd, period
            )
            user_traffic.append({
                'user': self.parse_user_code(user_rrd),
                'download': total_in,
                'upload': total_out,
                'total': total_in + total_out,
                'speed_plan': self.parse_speed(user_rrd)
            })
        
        # 3. 排序取 TOP100
        top100 = sorted(
            user_traffic,
            key=lambda x: x['total'],
            reverse=True
        )[:100]
        
        # 4. 產生報表
        self.generate_html(top100, f'top100_{period}.html')
        self.generate_csv(top100, f'top100_{period}.csv')
        
        return top100
```

### 報表 2: Circuit 擁塞分析

```python
# reports/circuit_congestion_report.py
class CircuitCongestionReport(BaseReport):
    """Circuit 擁塞報表（最近三日）"""
    
    def generate(self):
        """產生擁塞報表"""
        # 1. 讀取所有 Circuit RRD（最近三日）
        circuits = self.scan_circuit_rrds()
        
        # 2. 分析每個 Circuit
        congestion_data = []
        for circuit_rrd in circuits:
            # 讀取三日資料
            data = self.read_rrd_data(
                circuit_rrd,
                start_time='-3d',
                end_time='now'
            )
            
            # 取得 Circuit 資訊
            bras_ip, interface = self.parse_circuit_rrd(circuit_rrd)
            bandwidth = self.get_circuit_bandwidth(bras_ip, interface)
            
            # 分析擁塞
            analysis = self.analyze_congestion(data, bandwidth)
            
            congestion_data.append({
                'circuit': f"{bras_ip}_{interface}",
                'bandwidth': bandwidth,
                'avg_usage': analysis['avg_usage'],
                'peak_usage': analysis['peak_usage'],
                'congestion_hours': analysis['congestion_hours'],
                'congestion_periods': analysis['periods']
            })
        
        # 3. 產生報表
        self.generate_html(congestion_data, 'circuit_congestion_3days.html')
        
        return congestion_data
    
    def analyze_congestion(self, data, bandwidth):
        """分析擁塞情況"""
        threshold = bandwidth * 0.8  # 80% 為擁塞
        
        congestion_count = 0
        congestion_periods = []
        
        for timestamp, value in data:
            if value > threshold:
                congestion_count += 1
                congestion_periods.append(timestamp)
        
        return {
            'avg_usage': sum(v for _, v in data) / len(data),
            'peak_usage': max(v for _, v in data),
            'congestion_hours': congestion_count * 20 / 60,  # 20分鐘 -> 小時
            'periods': congestion_periods
        }
```

### 報表 3: Circuit I/O 統計

```python
# reports/circuit_io_statistics.py
class CircuitIOStatistics(BaseReport):
    """Circuit 流入/流出統計"""
    
    def generate(self, period='daily'):
        """產生 I/O 統計"""
        circuits = self.scan_circuit_rrds()
        
        io_stats = []
        for circuit_rrd in circuits:
            # 讀取資料
            data = self.read_rrd_data(
                circuit_rrd,
                period=period
            )
            
            # 計算流入/流出
            total_in = sum(d['in_bits'] for d in data) / 8 / 1024 / 1024 / 1024  # GB
            total_out = sum(d['out_bits'] for d in data) / 8 / 1024 / 1024 / 1024
            
            io_stats.append({
                'circuit': self.parse_circuit_name(circuit_rrd),
                'inbound_gb': total_in,
                'outbound_gb': total_out,
                'ratio': total_in / total_out if total_out > 0 else 0
            })
        
        self.generate_html(io_stats, f'circuit_io_{period}.html')
        return io_stats
```

### 報表 4: 速率分類統計

```python
# reports/circuit_speed_classification.py
class CircuitSpeedClassification(BaseReport):
    """Circuit 速率分類統計"""
    
    SPEED_CLASSES = {
        '5M/384K': (5120, 384),
        '16M/3M': (16384, 3072),
        '35M/6M': (35840, 6144),
        '100M/40M': (102400, 40960)
    }
    
    def generate(self, period='monthly'):
        """產生速率分類統計"""
        # 從 BRAS-Map 和資料庫取得所有 Circuit
        circuits = self.get_all_circuits()
        
        classification = {}
        for circuit_id, circuit_info in circuits.items():
            # 查詢該 Circuit 的所有用戶
            users = self.get_circuit_users(circuit_id)
            
            # 依速率分類
            for speed_class, (down, up) in self.SPEED_CLASSES.items():
                if speed_class not in classification:
                    classification[speed_class] = {
                        'circuits': {},
                        'total_users': 0,
                        'total_traffic': 0
                    }
                
                # 篩選該速率的用戶
                speed_users = [
                    u for u in users
                    if u['download'] == down and u['upload'] == up
                ]
                
                if speed_users:
                    # 計算流量
                    traffic = self.calculate_users_traffic(
                        speed_users, period
                    )
                    
                    classification[speed_class]['circuits'][circuit_id] = {
                        'user_count': len(speed_users),
                        'traffic_gb': traffic
                    }
                    classification[speed_class]['total_users'] += len(speed_users)
                    classification[speed_class]['total_traffic'] += traffic
        
        self.generate_html(classification, f'speed_classification_{period}.html')
        return classification
```

### 報表 5: VLAN 數量統計

```python
# reports/circuit_vlan_statistics.py
class CircuitVLANStatistics(BaseReport):
    """Circuit VLAN 數量統計"""
    
    def generate(self):
        """產生 VLAN 統計（月對月）"""
        # 1. 取得本月和上月的 VLAN 數量
        current_month = self.count_vlans('current_month')
        last_month = self.count_vlans('last_month')
        
        # 2. 計算差異
        vlan_stats = []
        for circuit_id in set(current_month.keys()) | set(last_month.keys()):
            current = current_month.get(circuit_id, 0)
            last = last_month.get(circuit_id, 0)
            
            vlan_stats.append({
                'circuit': circuit_id,
                'area': self.get_circuit_area(circuit_id),
                'last_month_vlans': last,
                'current_month_vlans': current,
                'change': current - last,
                'growth_rate': ((current - last) / last * 100) if last > 0 else 0
            })
        
        # 3. 依分區 Group
        grouped_stats = self.group_by_area(vlan_stats)
        
        self.generate_html(grouped_stats, 'vlan_statistics_monthly.html')
        return grouped_stats
    
    def count_vlans(self, period):
        """計算 VLAN 數量"""
        vlan_counts = {}
        
        # 掃描所有用戶 RRD
        user_rrds = self.scan_user_rrds()
        
        for rrd in user_rrds:
            # 解析 Circuit
            bras_ip, slot, port = self.parse_user_rrd(rrd)
            circuit_id = f"{bras_ip}_{slot}_{port}"
            
            # 檢查該 RRD 在指定期間是否有資料
            if self.has_data_in_period(rrd, period):
                vlan_counts[circuit_id] = vlan_counts.get(circuit_id, 0) + 1
        
        return vlan_counts
```

## ⏰ 定時任務設定

### 收集器 Cron

```bash
# /etc/cron.d/isp_traffic_collector

# 每 20 分鐘執行一次收集
*/20 * * * * rrdw /usr/bin/python3 /opt/rrdw/collectors/collector_dispatcher.py >> /var/log/rrdw/collector.log 2>&1
```

### 報表 Cron

```bash
# /etc/cron.d/isp_traffic_reports

# TOP100 報表
0 1 * * * rrdw /usr/bin/python3 /opt/rrdw/reports/top100_traffic_report.py --period daily >> /var/log/rrdw/reports.log 2>&1
0 2 * * 0 rrdw /usr/bin/python3 /opt/rrdw/reports/top100_traffic_report.py --period weekly >> /var/log/rrdw/reports.log 2>&1
0 3 1 * * rrdw /usr/bin/python3 /opt/rrdw/reports/top100_traffic_report.py --period monthly >> /var/log/rrdw/reports.log 2>&1

# Circuit 擁塞報表（每日）
30 1 * * * rrdw /usr/bin/python3 /opt/rrdw/reports/circuit_congestion_report.py >> /var/log/rrdw/reports.log 2>&1

# Circuit I/O 統計
0 4 * * * rrdw /usr/bin/python3 /opt/rrdw/reports/circuit_io_statistics.py --period daily >> /var/log/rrdw/reports.log 2>&1
0 5 * * 0 rrdw /usr/bin/python3 /opt/rrdw/reports/circuit_io_statistics.py --period weekly >> /var/log/rrdw/reports.log 2>&1
0 6 1 * * rrdw /usr/bin/python3 /opt/rrdw/reports/circuit_io_statistics.py --period monthly >> /var/log/rrdw/reports.log 2>&1

# 速率分類統計
0 7 * * 0 rrdw /usr/bin/python3 /opt/rrdw/reports/circuit_speed_classification.py --period weekly >> /var/log/rrdw/reports.log 2>&1
0 8 1 * * rrdw /usr/bin/python3 /opt/rrdw/reports/circuit_speed_classification.py --period monthly >> /var/log/rrdw/reports.log 2>&1

# VLAN 統計（每月）
0 9 1 * * rrdw /usr/bin/python3 /opt/rrdw/reports/circuit_vlan_statistics.py >> /var/log/rrdw/reports.log 2>&1
```

## 📈 資料保留策略

### RRD 資料保留

```python
# config/rrd_retention.py

RRD_RETENTION = {
    # 20 分鐘粒度，保留 62 天
    'detail': {
        'step': 1200,
        'rows': 4465  # 1200s * 4465 = 62 days
    },
    
    # 1 天粒度，保留 2 年
    'daily': {
        'step': 86400,
        'rows': 730   # 730 days = 2 years
    }
}
```

### 報表保留

```bash
# 報表保留策略
HTML 報表: 保留 90 天
CSV 檔案: 保留 180 天
圖表: 保留 30 天
```

## 🎯 總結

### 完成項目

✅ **RRD 四層結構設計**
- Layer 1: User VLAN
- Layer 2: Speed Sum
- Layer 3: Speed Sum2M
- Layer 4: Circuit ⭐

✅ **收集器架構**
- E320（已有）
- ACX/MX960/MX240（待實作）

✅ **報表系統設計**
- TOP100 流量
- Circuit 擁塞
- Circuit I/O
- 速率分類
- VLAN 統計

✅ **定時任務規劃**
- 20 分鐘收集
- 定時報表產生

### 下一步實作順序

1. **實作 Circuit RRD** - 擴充現有 E320 收集器
2. **實作 MX/ACX 收集器** - 參考 E320 格式
3. **實作報表基礎類別** - BaseReport
4. **實作五個報表系統** - 依優先序
5. **設定 Cron 定時任務**
6. **測試和驗證**

---

**版本**: 1.0  
**狀態**: 📋 設計完成，待實作  
**預計完成時間**: 依模組分階段實作
