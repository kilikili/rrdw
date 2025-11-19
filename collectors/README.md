# Collectors 目錄

此目錄存放各設備類型的收集器程式。

## 收集器清單

- **collector_e320.py** - E320 設備收集器
  - DeviceType: 1
  - 特性: Legacy BRAS, 較長 SNMP timeout (10s)
  - 介面格式: ge-slot/port/pic.vci

- **collector_mx960.py** - MX960 設備收集器
  - DeviceType: 2
  - 特性: Dynamic IP, High Capacity
  - 介面格式: ge-fpc/pic/port:vci

- **collector_mx240.py** - MX240 設備收集器
  - DeviceType: 3
  - 特性: Dynamic IP with PPPoE
  - 介面格式: ge-fpc/pic/port:vci

- **collector_acx7024.py** - ACX7024 設備收集器
  - DeviceType: 4
  - 特性: Fixed IP Services
  - 介面格式: ge-fpc/pic/port:vci

## 開發指南

請參考 `../docs/COLLECTOR_FIXES.md` 了解收集器開發的最佳實踐。

## 使用方式

```bash
# 手動執行單一收集器
python3 collector_mx240.py --ip 61.64.191.74 --map ../config/maps/map_61.64.191.74.txt

# 通過 dispatcher 自動調度
cd ../orchestrator
python3 dispatcher.py
```
