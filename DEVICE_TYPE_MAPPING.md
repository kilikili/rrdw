# 設備類型對照表

## 正確的 DeviceType 對應

| DeviceType | 設備型號 | 介面格式 | SNMP Timeout | 備註 |
|------------|---------|---------|--------------|------|
| **1** | **MX240** | ge-fpc/pic/port:vci | 5 秒 | PPPoE 支援 |
| **2** | **MX960** | ge-fpc/pic/port:vci | 5 秒 | High Capacity |
| **3** | **E320** | ge-slot/port/pic.vci | 10 秒 | Legacy BRAS |
| **4** | **ACX7024** | ge-fpc/pic/port:vci | 5 秒 | Fixed IP Services |

## 介面格式轉換

### MX240 (DeviceType=1)
- **Map 格式**: `Slot_Port_VPI_VCI` → 例如: `1_2_0_3490`
- **Junos 格式**: `ge-fpc/pic/port:vci` → 例如: `ge-1/0/2:3490`
- **轉換規則**: Slot→FPC, VPI→PIC

### MX960 (DeviceType=2)
- **Map 格式**: `Slot_Port_VPI_VCI` → 例如: `1_2_0_3490`
- **Junos 格式**: `ge-fpc/pic/port:vci` → 例如: `ge-1/0/2:3490`
- **轉換規則**: Slot→FPC, VPI→PIC

### E320 (DeviceType=3)
- **Map 格式**: `Slot_Port_VPI_VCI` → 例如: `1_2_0_3490`
- **Junos 格式**: `ge-slot/port/pic.vci` → 例如: `ge-1/2/0.3490`
- **轉換規則**: 直接對應

### ACX7024 (DeviceType=4)
- **Map 格式**: `Slot_Port_VPI_VCI` → 例如: `0_0_0_100`
- **Junos 格式**: `ge-fpc/pic/port:vci` → 例如: `ge-0/0/0:100`
- **轉換規則**: Slot→FPC, VPI→PIC

## 收集器對應

| 收集器檔案 | DeviceType | 設備型號 |
|-----------|-----------|---------|
| collector_mx240.py | 1 | MX240 |
| collector_mx960.py | 2 | MX960 |
| collector_e320.py | 3 | E320 |
| collector_acx7024.py | 4 | ACX7024 |

## BRAS-Map.txt 範例

```
# Area	DeviceType	IP	CircuitID	...
North	1	61.64.191.74	CIRCUIT_N_MX240_01	...
North	2	61.64.191.80	CIRCUIT_N_MX960_01	...
North	3	61.64.191.78	CIRCUIT_N_E320_01	...
Central	4	61.64.192.90	CIRCUIT_C_ACX7024_01	...
```

## 使用範例

### 產生 Map 檔案

```bash
# MX240
python3 generate_map_template.py --host 61.64.191.74 --type 1 --output map_61.64.191.74.txt

# MX960
python3 generate_map_template.py --host 61.64.191.80 --type 2 --output map_61.64.191.80.txt

# E320
python3 generate_map_template.py --host 61.64.191.78 --type 3 --output map_61.64.191.78.txt

# ACX7024
python3 generate_map_template.py --host 61.64.192.90 --type 4 --output map_61.64.192.90.txt
```

### 執行收集器

```bash
# MX240
python3 collector_mx240.py --ip 61.64.191.74 --map ../config/maps/map_61.64.191.74.txt

# MX960
python3 collector_mx960.py --ip 61.64.191.80 --map ../config/maps/map_61.64.191.80.txt

# E320
python3 collector_e320.py --ip 61.64.191.78 --map ../config/maps/map_61.64.191.78.txt

# ACX7024
python3 collector_acx7024.py --ip 61.64.192.90 --map ../config/maps/map_61.64.192.90.txt
```

---

**版本**: v2.1 (已修正設備類型對應)  
**最後更新**: 2025-11-19
