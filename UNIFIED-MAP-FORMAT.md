# BRAS Map 統一格式規範（基於 E320）

## 格式說明

### 統一採用 E320 Map File 格式

所有設備（E320/ACX/MX960/MX240）統一使用相同的 Map File 格式，簡化系統管理。

## 檔案格式

### 檔名規則
```
map_{BRAS_IP}_{slot}_{port}.txt
```

範例：
- `map_61.64.191.1_1_2.txt`  （E320: slot=1, port=2）
- `map_10.1.1.1_0_0.txt`     （ACX: slot=0, port=0）
- `map_10.1.1.2_1_0.txt`     （MX960: slot=1, port=0）

### 內容格式
```
使用者代碼,下載速率(Kbps),上傳速率(Kbps),ifindex,VLAN
```

**欄位說明**：
1. **使用者代碼**: 電話號碼或使用者帳號（字串）
2. **下載速率**: 單位 Kbps（整數）
3. **上傳速率**: 單位 Kbps（整數）
4. **ifindex**: SNMP ifindex（整數）
5. **VLAN**: VLAN ID（整數）

## 格式範例

### E320 設備
```
# map_61.64.191.1_1_2.txt
# E320 設備，slot=1, port=2
0989703334,35840,6144,587247394,3490
0981234567,102400,40960,587247395,3491
shinyi64518,5120,384,587247396,3492
```

### ACX7024 設備
```
# map_10.1.1.1_0_0.txt
# ACX7024 設備，slot=0, port=0
user001,51200,20480,1024,100
user002,102400,40960,1025,101
user003,51200,20480,1026,102
```

### MX960 設備（PPPoE）
```
# map_10.1.1.2_1_0.txt
# MX960 設備，slot=1, port=0
user@isp.com,102400,40960,2048,200
test@isp.com,51200,20480,2049,201
demo@isp.com,35840,6144,2050,202
```

### MX240 設備（PPPoE）
```
# map_10.1.1.3_1_0.txt
# MX240 設備，slot=1, port=0（10G 介面）
pppoe_user1,204800,102400,3072,300
pppoe_user2,102400,40960,3073,301
pppoe_user3,51200,20480,3074,302
```

## 設備清單檔案

### BRAS-Devices.txt

用於記錄所有 BRAS 設備的基本資訊：

```
BRAS_IP,設備類型,主機名稱,區域,頻寬上限(Mbps)
```

**設備類型代碼**：
- `E320` - Juniper E320/ERX
- `ACX` - Juniper ACX7024
- `MX960` - Juniper MX960
- `MX240` - Juniper MX240

**範例**：
```
# BRAS-Devices.txt
61.64.191.1,E320,TC-BRAS-01,台中,880
10.1.1.1,ACX,KH-ACX-01,高雄,1000
10.1.1.2,MX960,TP-MX960-01,台北,10000
10.1.1.3,MX240,TC-MX240-01,台中交心,10000
```

## 目錄結構

```
/opt/rrdw/
├── config/
│   ├── BRAS-Devices.txt                    # 設備清單
│   └── maps/                               # Map File 目錄
│       ├── map_61.64.191.1_1_2.txt        # E320
│       ├── map_10.1.1.1_0_0.txt           # ACX
│       ├── map_10.1.1.2_1_0.txt           # MX960
│       └── map_10.1.1.3_1_0.txt           # MX240
```

## 與原有格式的差異

### 原有格式（複雜）
```
bras_hostname,device_type,bras_ip,circuit_id,pvc,trunk_number,phone,area,interface,slot,port,bandwidth,vlan_count
```

### 統一格式（簡化）
```
使用者代碼,下載速率,上傳速率,ifindex,VLAN
```

**優點**：
1. ✅ **格式統一** - 所有設備使用相同格式
2. ✅ **簡化管理** - 只需要維護 Map File
3. ✅ **E320 相容** - 100% 相容現有 E320 系統
4. ✅ **易於維護** - 格式簡單清晰
5. ✅ **自動發現** - 透過檔名識別設備和埠口

## 收集器行為

### 自動載入流程

```python
# 1. 掃描 maps 目錄
for map_file in glob("maps/map_*.txt"):
    # 2. 解析檔名
    # map_61.64.191.1_1_2.txt
    parts = map_file.split('_')
    bras_ip = parts[1]  # 61.64.191.1
    slot = int(parts[2])  # 1
    port = int(parts[3].replace('.txt', ''))  # 2
    
    # 3. 查詢設備類型
    device_type = get_device_type(bras_ip)  # 從 BRAS-Devices.txt
    
    # 4. 選擇對應收集器
    if device_type == 'E320':
        collector = E320Collector()
    elif device_type == 'ACX':
        collector = ACXCollector()
    # ...
    
    # 5. 執行收集
    collector.collect(bras_ip, slot, port)
```

## 產生 Map File

### E320 設備
直接使用現有的 Map File，格式已經符合標準。

### ACX/MX 設備
需要建立 Map File：

**方式 1: 手動建立**
```bash
# 建立 ACX Map File
cat > maps/map_10.1.1.1_0_0.txt << EOF
user001,51200,20480,1024,100
user002,102400,40960,1025,101
EOF
```

**方式 2: 從 RADIUS 匯出（PPPoE）**
```bash
# 匯出 MX960 PPPoE 使用者
python3 export_pppoe_users.py \
  --bras-ip 10.1.1.2 \
  --slot 1 \
  --port 0 \
  --output maps/map_10.1.1.2_1_0.txt
```

**方式 3: 從 SNMP 自動發現**
```bash
# ACX 自動發現
python3 discover_interfaces.py \
  --bras-ip 10.1.1.1 \
  --slot 0 \
  --port 0 \
  --output maps/map_10.1.1.1_0_0.txt
```

## ifindex 欄位說明

### E320
- ifindex 是 SNMP IF-MIB 的 ifIndex
- 格式：587247394（大整數）
- 查詢：`snmpwalk -v2c -c public 61.64.191.1 ifIndex`

### ACX/MX
- ifindex 也是 SNMP IF-MIB 的 ifIndex
- 格式：1024, 2048（較小整數）
- 可透過 SNMP Walk 自動取得

### ifindex 對照表

| 設備 | 介面格式 | ifindex 範例 | 查詢方式 |
|-----|---------|-------------|---------|
| E320 | atm 1/2.3490 | 587247394 | Map File |
| ACX | ge-0/0/0.100 | 1024 | SNMP Walk |
| MX960 | ge-1/0/0.200 | 2048 | SNMP Walk |
| MX240 | xe-1/0/0.300 | 3072 | SNMP Walk |

## 收集流程統一

### 所有設備統一流程

```
1. 讀取 BRAS-Devices.txt → 取得設備類型
2. 讀取 maps/map_{IP}_{slot}_{port}.txt → 取得使用者列表
3. 使用 ifindex 執行 SNMP 查詢 → 取得流量
4. 寫入四層 RRD：
   - Layer 1: User (VLAN 層級)
   - Layer 2: Sum (速率彙總)
   - Layer 3: Sum2M (Fair Usage)
   - Layer 4: Circuit (設備級)
```

### 不同設備的差異

| 設備 | Map File 來源 | ifindex 取得 | 特殊處理 |
|-----|--------------|-------------|---------|
| E320 | 現有系統 | Map File 直接提供 | 無 |
| ACX | 手動/匯出 | SNMP Walk 對照 | 固定 IP |
| MX960 | RADIUS 匯出 | SNMP Walk 對照 | PPPoE 動態 |
| MX240 | RADIUS 匯出 | SNMP Walk 對照 | PPPoE 10G |

## 遷移指南

### 從舊格式遷移

如果你有舊的 BRAS-Map.txt 格式，可以使用轉換工具：

```bash
# 轉換舊格式到新格式
python3 convert_bras_map.py \
  --input BRAS-Map.txt \
  --output-dir maps/
```

這會產生：
- `BRAS-Devices.txt` - 設備清單
- `maps/map_*.txt` - 各設備的 Map File

### 驗證格式

```bash
# 驗證 Map File 格式
python3 validate_map_files.py maps/

# 驗證 BRAS-Devices.txt 格式
python3 validate_bras_devices.py BRAS-Devices.txt
```

## 完整範例

### BRAS-Devices.txt
```
# BRAS 設備清單
# BRAS_IP,設備類型,主機名稱,區域,頻寬上限(Mbps)
61.64.191.1,E320,TC-BRAS-OLD,台中,880
61.64.191.10,E320,TC-BRAS-OLD-02,台中,880
10.1.1.1,ACX,KH-ACX-01,高雄,1000
10.1.1.2,MX960,TP-MX960-01,台北,10000
10.1.1.3,MX240,TC-MX240-01,台中交心,10000
```

### map_61.64.191.1_1_2.txt (E320)
```
# E320 台中 BRAS，Slot 1 Port 2
# 使用者代碼,下載(Kbps),上傳(Kbps),ifindex,VLAN
0989703334,35840,6144,587247394,3490
0981234567,102400,40960,587247395,3491
0912345678,51200,20480,587247396,3492
shinyi64518,5120,384,587247397,3493
```

### map_10.1.1.1_0_0.txt (ACX)
```
# ACX7024 高雄，Slot 0 Port 0
# 使用者代碼,下載(Kbps),上傳(Kbps),ifindex,VLAN
fixedip001,51200,20480,1024,100
fixedip002,102400,40960,1025,101
fixedip003,51200,20480,1026,102
```

### map_10.1.1.2_1_0.txt (MX960)
```
# MX960 台北，Slot 1 Port 0
# 使用者代碼,下載(Kbps),上傳(Kbps),ifindex,VLAN
user01@isp.com,102400,40960,2048,200
user02@isp.com,51200,20480,2049,201
user03@isp.com,35840,6144,2050,202
```

## 總結

**統一格式的優勢**：

1. ✅ **格式統一** - 所有設備使用相同的 5 欄位格式
2. ✅ **E320 相容** - 100% 相容現有 E320 Map File
3. ✅ **簡化維護** - 只需維護 Map File 和設備清單
4. ✅ **自動識別** - 透過檔名自動識別設備和埠口
5. ✅ **易於擴充** - 新增設備只需加入 Map File

**格式標準**：
```
使用者代碼,下載速率(Kbps),上傳速率(Kbps),ifindex,VLAN
```

這個格式簡單、清晰，適用於所有 BRAS 設備！
