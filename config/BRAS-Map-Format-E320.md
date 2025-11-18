# BRAS Map 系統格式規範（基於實際 E320 系統）

## 檔案結構

```
rrdw/
├── BRAS-Map.txt              # 設備和 Circuit 主檔
├── devices_A.tsv             # 設備列表 A 組
├── devices_B.tsv             # 設備列表 B 組
├── maps/
│   ├── map_61.64.191.1.txt   # E320 設備的 Map 檔案
│   ├── map_10.1.1.1.txt      # MX240 設備的 Map 檔案
│   └── ...
└── data/
    ├── 61.64.191.1/          # E320 個別用戶 RRD
    │   ├── 61.64.191.1_1_2_35840_6144_3490.rrd
    │   └── ...
    ├── sum/                  # 彙總 RRD（無限制）
    │   └── 61.64.191.1/
    │       ├── 61.64.191.1_1_2_35840_6144_sum.rrd
    │       └── ...
    └── sum2m/                # 彙總 RRD（有限制）
        └── 61.64.191.1/
            ├── 61.64.191.1_1_2_35840_6144_sum.rrd
            └── ...
```

## 1. BRAS-Map.txt 格式

### 格式說明
```
bras_hostname	device_type	bras_ip	circuit_id	slot	port	circuit_type	bandwidth	if_assign
```

### 欄位定義

| 欄位 | 說明 | 範例 | 備註 |
|-----|------|------|------|
| bras_hostname | BRAS 主機名稱 | center_3 | - |
| device_type | 設備類型代碼 | 3 | 1:MX240, 2:MX960, 3:E320, 4:ACX7024 |
| bras_ip | BRAS IP 位址 | 61.64.191.1 | - |
| circuit_id | Circuit 編號 | 43GD00128 | - |
| slot | 插槽編號 | 1 | - |
| port | 埠號 | 2 | - |
| circuit_type | 電路類型 | GE | GE/FE/XE 等 |
| bandwidth | 頻寬 | 880 | 單位：Mbps |
| if_assign | 介面分配 | 0 | 保留欄位 |

### 範例
```
center_3	3	61.64.191.1	43GD00128	1	2	GE	880	0
north_1	1	10.1.1.1	43GD00129	0	0	XE	10000	0
```

**重要：欄位間使用 TAB 分隔**

## 2. Map File 格式 (maps/map_{IP}.txt)

### 格式說明
```
user_code,slot_port_vpi_vci,download_upload,ifindex
```

### 欄位定義

| 欄位 | 說明 | 格式 | 範例 | 備註 |
|-----|------|------|------|------|
| user_code | 用戶代碼 | 任意字串 | 0989703334 | 電話號碼或用戶ID |
| slot_port_vpi_vci | 介面識別 | slot_port_vpi_vci | 1_2_0_3490 | **用底線分隔** |
| download_upload | 速率規格 | download_upload | 35840_6144 | **kbps，用底線分隔** |
| ifindex | SNMP ifIndex | 整數 | 587247394 | SNMP interface index |

### 範例
```
0989703334,1_2_0_3490,35840_6144,587247394
0981345344,3_1_0_3441,102400_40960,587272279
shinyi64518,3_1_0_57,5120_384,587269635
2738475,3_3_0_200,16384_3072,587238119
```

### 關鍵規則

1. **底線分隔**：所有欄位都使用底線（_）分隔，不使用斜線（/）
   ```
   ✓ 正確: 1_2_0_3490  (slot_port_vpi_vci)
   ✗ 錯誤: 1/2/0/3490
   
   ✓ 正確: 35840_6144  (download_upload)
   ✗ 錯誤: 35840/6144
   ```

2. **VCI 用作 VLAN**：在 E320 系統中，VCI 值直接作為 VLAN ID
   ```python
   # 從 1_2_0_3490 解析
   slot = 1
   port = 2
   vpi = 0
   vci = 3490  # 這就是 VLAN ID
   ```

3. **速率單位**：kbps（千位元/秒）
   ```
   35840_6144 表示下載 35840 kbps，上傳 6144 kbps
   即下載 35 Mbps，上傳 6 Mbps
   ```

4. **ifindex**：SNMP interface index，從 BRAS 查詢得到
   ```bash
   # 查詢 ifindex
   snmpwalk -v2c -c public 61.64.191.1 ifDescr
   ```

## 3. RRD 檔案命名規則

### 個別用戶 RRD
```
格式: {IP}/{IP}_{slot}_{port}_{download}_{upload}_{vlan}.rrd
範例: 61.64.191.1/61.64.191.1_1_2_35840_6144_3490.rrd
```

**注意**：
- 速率使用 kbps（與 Map file 一致）
- VLAN 來自 VCI 值
- 使用底線分隔

### 彙總 RRD (Sum)
```
格式: sum/{IP}/{IP}_{slot}_{port}_{download}_{upload}_sum.rrd
範例: sum/61.64.191.1/61.64.191.1_1_2_35840_6144_sum.rrd
```

### 彙總 RRD (Sum2M - Fair Usage)
```
格式: sum2m/{IP}/{IP}_{slot}_{port}_{download}_{upload}_sum.rrd
範例: sum2m/61.64.191.1/61.64.191.1_1_2_35840_6144_sum.rrd
```

## 4. E320 特殊處理

### SNMP 設定
```ini
[snmp]
timeout = 10          # E320 需要較長 timeout
retries = 2
version = 2c
```

### Interface Index 處理
E320 不使用介面名稱推算 ifindex，而是：
1. 從 Map file 直接讀取 ifindex
2. 使用 SNMP 直接查詢該 ifindex 的流量

```python
# ✓ 正確做法 (E320)
ifindex = 587247394  # 從 Map file 讀取
octets = snmpget(bras_ip, f"ifHCOutOctets.{ifindex}")

# ✗ 錯誤做法
# 不要嘗試從介面名稱推算 ifindex
```

### 介面格式
E320 介面名稱格式：
```
ge-{slot}/{port}.{vci}
例如: ge-1/2.3490
```

但實際收集時不使用介面名稱，而是直接使用 ifindex。

## 5. 與 MX/ACX 的差異

| 項目 | E320 | MX/ACX |
|-----|------|--------|
| **介面格式** | ge-1/2.3490 (兩段式) | xe-1/0/0.400 (三段式) |
| **VLAN 來源** | VCI 值 | VLAN tag |
| **ifindex** | 從 Map file 讀取 | 可從介面名稱查詢 |
| **SNMP timeout** | 10 秒 | 3-5 秒 |
| **分隔符號** | 底線 (_) | 底線 (_) |

## 6. 資料收集流程

### Step 1: 載入 Map File
```python
# 讀取 maps/map_{IP}.txt
users = load_map_file(bras_ip)
# 取得每個用戶的 ifindex
```

### Step 2: SNMP 並行查詢
```python
# 對所有 ifindex 並行查詢
for ifindex in user_ifindexes:
    octets = snmpget(bras_ip, f"ifHCOutOctets.{ifindex}")
```

### Step 3: 寫入個別用戶 RRD
```python
# 格式: {IP}_{slot}_{port}_{download}_{upload}_{vlan}.rrd
rrd_path = f"{IP}/{IP}_{slot}_{port}_{download}_{upload}_{vci}.rrd"
rrdtool.update(rrd_path, f"{timestamp}:{octets}")
```

### Step 4: 讀取速率並彙總
```python
# 從個別 RRD 讀取當前速率
for user in users:
    rate = rrdtool.fetch(user.rrd_path, 'AVERAGE')
    speed_groups[user.speed_key].append(rate)
```

### Step 5: 寫入彙總 RRD
```python
# Sum RRD (無限制)
sum_rrd = f"sum/{IP}/{IP}_{slot}_{port}_{download}_{upload}_sum.rrd"
rrdtool.update(sum_rrd, f"{timestamp}:{total_rate}")

# Sum2M RRD (Fair Usage 限制)
sum2m_rrd = f"sum2m/{IP}/{IP}_{slot}_{port}_{download}_{upload}_sum.rrd"
rrdtool.update(sum2m_rrd, f"{timestamp}:{limited_rate}")
```

## 7. 格式驗證工具

### 驗證 Map File 格式
```python
def validate_map_line(line):
    parts = line.split(',')
    if len(parts) != 4:
        return False, "欄位數量錯誤"
    
    user_code, interface, speed, ifindex = parts
    
    # 驗證 interface 格式
    if_parts = interface.split('_')
    if len(if_parts) != 4:
        return False, f"介面格式錯誤: {interface}，應為 slot_port_vpi_vci"
    
    # 驗證速率格式
    speed_parts = speed.split('_')
    if len(speed_parts) != 2:
        return False, f"速率格式錯誤: {speed}，應為 download_upload"
    
    # 驗證 ifindex 為數字
    if not ifindex.isdigit():
        return False, f"ifindex 必須為數字: {ifindex}"
    
    return True, "OK"
```

### 驗證 RRD 路徑格式
```python
def validate_rrd_path(rrd_path):
    # 個別用戶 RRD 應包含 6 個部分
    filename = os.path.basename(rrd_path)
    parts = filename.replace('.rrd', '').split('_')
    
    if len(parts) != 6:
        return False, f"RRD 檔名格式錯誤: {filename}"
    
    ip, slot, port, download, upload, vlan = parts
    
    # 驗證各部分為數字
    for part in [slot, port, download, upload, vlan]:
        if not part.isdigit():
            return False, f"RRD 檔名包含非數字部分: {part}"
    
    return True, "OK"
```

## 8. 常見錯誤

### 錯誤 1: 使用斜線分隔
```
❌ 錯誤: 1/2/0/3490
✓ 正確: 1_2_0_3490

❌ 錯誤: 35840/6144
✓ 正確: 35840_6144
```

### 錯誤 2: 速率單位錯誤
```
❌ 錯誤: 35_6 (Mbps)
✓ 正確: 35840_6144 (kbps)
```

### 錯誤 3: RRD 路徑格式錯誤
```
❌ 錯誤: 61.64.191.1_1_2_35_6_3490.rrd (速率使用 Mbps)
✓ 正確: 61.64.191.1_1_2_35840_6144_3490.rrd (速率使用 kbps)
```

### 錯誤 4: 嘗試計算 E320 ifindex
```python
❌ 錯誤:
# E320 不應該計算 ifindex
ifindex = calculate_ifindex(slot, port, vlan)

✓ 正確:
# 直接從 Map file 讀取
ifindex = int(parts[3])  # 第 4 欄
```

## 9. 效能優化

### 並行查詢
```python
# 使用 ThreadPoolExecutor 並行查詢
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {
        executor.submit(get_snmp_value, bras_ip, community, ifindex): ifindex
        for ifindex in ifindex_list
    }
```

### 批次處理
```python
# 每 100 個介面輸出進度
if completed % 100 == 0:
    logging.info(f"進度: {completed}/{total}")
```

## 10. 摘要

**最重要的格式規則：**
1. ✅ 使用底線（_）分隔，不使用斜線（/）
2. ✅ 速率單位為 kbps
3. ✅ VCI 用作 VLAN
4. ✅ ifindex 從 Map file 讀取
5. ✅ E320 使用較長的 SNMP timeout

**檔案格式：**
- BRAS-Map.txt: TAB 分隔
- Map file: 逗號分隔，底線分隔內部欄位
- RRD 檔名: 底線分隔所有部分

---

**版本**: 2.0（基於實際運作的 E320 系統）  
**參考**: isp_traffic_collector_e320.py
