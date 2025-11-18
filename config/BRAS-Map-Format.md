# BRAS-Map.txt 格式規範

## 檔案用途
用於定義 BRAS 設備、Circuit 資訊及介面映射關係，支援 E320 和 MX/ACX 系列設備的差異。

## 設備類別代碼（第二欄）
```
1 = MX240
2 = MX960
3 = E320
4 = ACX7024
```

## 欄位定義

### 基本格式
```
bras_hostname,device_type,bras_ip,access_switch_hostname,access_switch_port_even,access_switch_port_singular,circuit_name,trunk_number,area
```

### 欄位說明
1. **bras_hostname** - BRAS 設備主機名稱（如：center_3）
2. **device_type** - 設備類別代碼（1/2/3/4）
3. **bras_ip** - BRAS IP 位址（如：61.64.214.54）
4. **access_switch_hostname** - 接取交換器主機名稱
5. **access_switch_port_even** - 接取交換器埠號（偶數）
6. **access_switch_port_singular** - 接取交換器埠號（單數）
7. **circuit_name** - 電路名稱
8. **trunk_number** - Trunk 編號（如：43GD10013）
9. **area** - 區域代碼（如：台中交心）

### MX/ACX 系列專用欄位（device_type = 1, 2, 4）
```
...,mx_port,slot,port,vlan,atmf
```
- **mx_port** - MX 埠號（如：xe-1/0/0）
- **slot** - 插槽編號
- **port** - 埠號
- **vlan** - VLAN ID
- **atmf** - ATM 框架編號

### E320 系列專用欄位（device_type = 3）
```
...,e320_interface,slot,port,vlan
```
- **e320_interface** - E320 介面（如：ge-0/0.400）
- **slot** - 插槽編號
- **port** - 埠號
- **vlan** - VLAN ID

## 介面格式差異

### E320 介面格式（兩段式）
```
ge-{slot}/{port}.{vlan}
例：ge-0/0.400
```

### MX/ACX 介面格式（三段式）
```
{interface_type}-{fpc}/{pic}/{port}.{vlan}
例：xe-1/0/0.100
    ge-0/0/1.200
```

### 介面類型對照
- **xe** = 10 Gigabit Ethernet
- **ge** = Gigabit Ethernet
- **et** = 100 Gigabit Ethernet

## 完整格式範例

### MX240 範例
```
center_3,1,61.64.214.54,TC7520-0,2,-,Circuit-001,43GD10013,台中交心,xe-1/0/0,1,0,400,1
```

### MX960 範例
```
north_bras1,2,10.1.1.1,TP-SW-01,4,3,Circuit-N01,43GD20001,台北,ge-0/0/1,0,0,100,2
```

### E320 範例
```
old_erx,3,61.64.191.1,KH-SW-02,6,-,Circuit-S01,43GD30001,高雄,ge-0/0.500,0,0,500,-
```

### ACX7024 範例
```
south_acx,4,10.1.1.4,KH-ACX-01,8,7,Circuit-S02,43GD40001,高雄,ge-0/0/2,0,0,200,3
```

## 收集器使用注意事項

### 介面名稱處理
```python
def get_interface_name(device_type, slot, port, vlan):
    if device_type == 3:  # E320
        return f"ge-{slot}/{port}.{vlan}"
    else:  # MX240/MX960/ACX7024
        # 需從 mx_port 或其他來源取得 interface_type
        return f"xe-{slot}/{port}/{port}.{vlan}"
```

### SNMP OID 對應
- **E320**: ifDescr 使用兩段式介面名
- **MX/ACX**: ifDescr 使用三段式介面名

### 資料收集優化
- 依設備類別分組收集
- E320 使用較長的 timeout 值
- MX/ACX 可並行收集

## 欄位擴充建議

若需新增欄位支援收集器差異處理：

1. **timeout_multiplier** - 針對 E320 設定較高的逾時倍數
2. **snmp_version** - SNMP 版本（預設 v2c）
3. **community_string** - SNMP Community（若不同）
4. **collection_priority** - 收集優先序（E320 較低）
5. **interface_pattern** - 介面名稱格式樣式

擴充格式範例：
```
bras_hostname,device_type,bras_ip,...,timeout_multiplier,collection_priority
center_3,1,61.64.214.54,...,1,1
old_erx,3,61.64.191.1,...,3,3
```
