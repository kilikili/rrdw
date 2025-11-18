# BRAS-Map.txt 格式規範（Tab 分隔）

## 格式說明

### 檔案格式
- **分隔符**: Tab (\t)
- **編碼**: UTF-8
- **檔名**: BRAS-Map.txt

### 欄位定義

```
Area	DeviceType	IP	CircuitID	Slot(Fpc)	Port	InterfaceType	BandwidthMax	IfAssign	Pic
```

| 欄位 | 說明 | 範例 | 備註 |
|-----|------|------|------|
| Area | 區域名稱 | taipei_4 | 機房或地區代碼 |
| DeviceType | 設備類型 | 3 | 1=MX240, 2=MX960, 3=E320, 4=ACX |
| IP | BRAS IP | 61.64.191.74 | IPv4 位址 |
| CircuitID | Circuit ID | 223GD99004 | 電路識別碼 |
| Slot(Fpc) | 插槽編號 | 1 | FPC 編號 |
| Port | 埠號 | 0 | Port 編號 |
| InterfaceType | 介面類型 | GE | GE=Gigabit, XE=10G |
| BandwidthMax | 頻寬上限 | 880 | 單位: Mbps |
| IfAssign | 介面分配 | 0 | 保留欄位 |
| Pic | PIC 編號 | 0 | Physical Interface Card |

## 設備類型代碼

| 代碼 | 設備 | 說明 |
|-----|------|------|
| 1 | MX240 | Juniper MX240 (動態 IP, PPPoE) |
| 2 | MX960 | Juniper MX960 (動態 IP, PPPoE) |
| 3 | E320 | Juniper E320/ERX (固定+動態 IP) |
| 4 | ACX | Juniper ACX7024 (固定 IP) |

## 介面類型

| 類型 | 說明 | 速度 |
|-----|------|------|
| GE | Gigabit Ethernet | 1 Gbps |
| XE | 10 Gigabit Ethernet | 10 Gbps |

## 完整範例

```tsv
Area	DeviceType	IP	CircuitID	Slot(Fpc)	Port	InterfaceType	BandwidthMax	IfAssign	Pic
taipei_4	3	61.64.191.74	223GD99004	1	0	GE	880	0	0
taipei_4	3	61.64.191.74	223GD99006	3	3	GE	880	0	0
taipei_4	3	61.64.191.74	223GD99016	5	2	GE	880	0	0
taipei_5	2	61.64.191.76	223GD99018	1	1	XE	880	0	0
taipei_6	4	61.64.191.77	223GD99018	0	0	XE	880	0	0
south_1	1	61.64.191.78	223GD99019	1	2	XE	880	0	2
south_1	4	61.64.191.79	223GD99019	0	0	XE	880	0	0
center_1	1	61.64.191.80	223GD99020	2	0	XE	880	0	0
center_1	4	61.64.191.81	223GD99020	0	0	XE	880	0	0
```

## 介面命名規則

根據 DeviceType 和欄位值組合介面名稱：

### E320 (DeviceType=3)
```
格式: atm {Slot}/{Port}
範例: atm 1/0
```

### MX240/MX960 (DeviceType=1,2)
```
格式: xe-{Slot}/{Pic}/{Port} (10G)
       ge-{Slot}/{Pic}/{Port} (1G)
範例: xe-1/2/0, ge-1/0/1
```

### ACX (DeviceType=4)
```
格式: xe-{Slot}/{Pic}/{Port} (10G)
       ge-{Slot}/{Pic}/{Port} (1G)
範例: ge-0/0/0, xe-0/0/1
```

## 與 Map File 的對應

### 產生 Map File 路徑
```python
# 格式: map_{IP}_{Slot}_{Port}.txt
map_filename = f"map_{IP}_{Slot}_{Port}.txt"

# 範例
# 61.64.191.74, Slot=1, Port=0
# -> map_61.64.191.74_1_0.txt
```

### Map File 內容格式
Map File 仍然使用統一的 5 欄位格式：
```
使用者代碼,下載速率(Kbps),上傳速率(Kbps),ifindex,VLAN
```

## 查詢範例

### 查詢特定區域的所有 Circuit
```python
# 讀取 BRAS-Map.txt
circuits = load_bras_map("BRAS-Map.txt")

# 篩選台北區域
taipei_circuits = [c for c in circuits if c['Area'].startswith('taipei')]
```

### 查詢特定 IP 的所有 Circuit
```python
# 篩選特定 IP
ip_circuits = [c for c in circuits if c['IP'] == '61.64.191.74']
```

### 查詢特定設備類型
```python
# 篩選 E320 設備
e320_circuits = [c for c in circuits if c['DeviceType'] == 3]
```

## 檔案位置

```
/opt/rrdw/
├── config/
│   ├── BRAS-Map.txt              # 主設備清單（Tab 分隔）
│   └── maps/                     # Map Files 目錄
│       ├── map_61.64.191.74_1_0.txt
│       ├── map_61.64.191.74_3_3.txt
│       └── ...
```

## 注意事項

1. **Tab 分隔**: 欄位之間必須使用 Tab (\t)，不可使用空格
2. **編碼**: 必須使用 UTF-8 編碼
3. **表頭**: 第一行必須是欄位名稱
4. **註解**: 不支援註解行，除了表頭外每行都是資料
5. **空值**: 不允許空欄位，最少填 0 或 - 

## 驗證

### 檢查格式
```bash
# 檢查是否為 Tab 分隔
cat -A BRAS-Map.txt | head -5

# 應該看到 ^I 表示 Tab
Area^IDeviceType^IIP^I...
taipei_4^I3^I61.64.191.74^I...
```

### 欄位數量
每行應該有 10 個欄位（包含表頭）

### 必要欄位
- Area: 不可空白
- DeviceType: 必須是 1, 2, 3, 4
- IP: 必須是有效的 IPv4
- Slot(Fpc): 必須是數字
- Port: 必須是數字

## 與舊格式的對應

### 舊格式 (CSV, 13 欄位)
```
bras_hostname,device_type,bras_ip,circuit_id,pvc,trunk_number,phone,area,interface,slot,port,bandwidth,vlan_count
```

### 新格式 (TSV, 10 欄位)
```
Area	DeviceType	IP	CircuitID	Slot(Fpc)	Port	InterfaceType	BandwidthMax	IfAssign	Pic
```

### 欄位對應表

| 舊格式 | 新格式 | 說明 |
|--------|--------|------|
| area | Area | 區域名稱 |
| device_type | DeviceType | 設備類型 |
| bras_ip | IP | BRAS IP |
| circuit_id | CircuitID | Circuit ID |
| slot | Slot(Fpc) | 插槽編號 |
| port | Port | 埠號 |
| - | InterfaceType | 新增：介面類型 |
| bandwidth | BandwidthMax | 頻寬上限 |
| - | IfAssign | 新增：介面分配 |
| - | Pic | 新增：PIC 編號 |

**移除的欄位**:
- bras_hostname (可從 IP 查詢)
- pvc (不需要)
- trunk_number (在 Map File 中)
- phone (在 Map File 中)
- interface (可從其他欄位組合)
- vlan_count (可從 Map File 統計)

## 轉換工具

### 從舊格式轉換
```bash
python3 convert_to_tsv.py \
  --input old-BRAS-Map.txt \
  --output BRAS-Map.txt
```

### 驗證新格式
```bash
python3 validate_bras_map.py \
  --file BRAS-Map.txt
```

## 總結

**新格式特點**：

✅ **Tab 分隔** - 更清晰的欄位分隔  
✅ **精簡欄位** - 10 欄位（vs 舊的 13 欄位）  
✅ **標準化** - 統一的命名和格式  
✅ **易於解析** - 標準 TSV 格式  
✅ **易於維護** - 清晰的結構  

這個格式是 **BRAS-Map.txt 的標準格式**，所有工具都應該支援這個格式。
