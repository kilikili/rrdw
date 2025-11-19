# 收集器程式碼修正指南

## 目標

本文件專注於收集器的程式碼校正和驗證，確保：
1. Map 檔案格式正確 (使用底線分隔符)
2. SNMP 連線穩定可靠
3. 介面名稱轉換正確
4. RRD 更新邏輯完善
5. 錯誤處理機制健全

## 核心修正項目

### 1. Map 檔案格式標準化

#### 問題
之前的實作可能混用斜線 (/) 和底線 (_) 分隔符，導致格式不一致。

#### 解決方案
**強制使用底線分隔符**

```python
# ✗ 錯誤格式
"0989703334,1/2/0/3490,35840/6144,587247394"

# ✓ 正確格式
"0989703334,1_2_0_3490,35840_6144,587247394"
```

#### 實作範例

```python
def parse_map_line(line: str) -> Dict:
    """
    解析 map 檔案的單行資料
    
    格式: UserID,Slot_Port_VPI_VCI,Download_Upload,AccountID
    """
    parts = line.strip().split(',')
    if len(parts) != 4:
        raise ValueError(f"格式錯誤: 需要 4 個欄位，實際 {len(parts)} 個")
    
    username, interface, bandwidth, account = parts
    
    # 驗證介面格式
    if '/' in interface:
        raise ValueError(f"介面格式錯誤: 應使用底線(_)而非斜線(/): {interface}")
    
    iface_parts = interface.split('_')
    if len(iface_parts) != 4:
        raise ValueError(f"介面格式錯誤: 應為 Slot_Port_VPI_VCI: {interface}")
    
    try:
        slot, port, vpi, vci = [int(x) for x in iface_parts]
    except ValueError:
        raise ValueError(f"介面欄位應為數字: {interface}")
    
    # 驗證頻寬格式
    if '/' in bandwidth:
        raise ValueError(f"頻寬格式錯誤: 應使用底線(_)而非斜線(/): {bandwidth}")
    
    bw_parts = bandwidth.split('_')
    if len(bw_parts) != 2:
        raise ValueError(f"頻寬格式錯誤: 應為 Download_Upload: {bandwidth}")
    
    try:
        download, upload = [int(x) for x in bw_parts]
    except ValueError:
        raise ValueError(f"頻寬欄位應為數字: {bandwidth}")
    
    return {
        'username': username,
        'slot': slot,
        'port': port,
        'vpi': vpi,
        'vci': vci,
        'download': download,
        'upload': upload,
        'account': account
    }
```

### 2. 介面名稱轉換修正

#### 問題
不同設備的介面命名格式不同，需要正確轉換。

#### 解決方案
根據設備類型使用不同的轉換邏輯。

```python
def build_interface_name(slot: int, port: int, vpi: int, vci: int, 
                        device_type: int, interface_type: str = 'GE') -> str:
    """
    根據設備類型建立 Junos 介面名稱
    
    Args:
        slot: FPC/Slot 編號
        port: Port 編號
        vpi: VPI (E320 為 PIC)
        vci: VCI
        device_type: 設備類型 (1=E320, 2=MX960, 3=MX240, 4=ACX7024)
        interface_type: 介面類型 (GE/XE)
    
    Returns:
        Junos 介面名稱
    """
    iface_prefix = interface_type.lower()
    
    if device_type == 1:  # E320
        # 格式: ge-slot/port/pic.vci
        return f"{iface_prefix}-{slot}/{port}/{vpi}.{vci}"
    else:  # MX240, MX960, ACX7024
        # 格式: ge-fpc/pic/port:vci
        return f"{iface_prefix}-{slot}/{vpi}/{port}:{vci}"
```

#### 測試案例

```python
# 測試 E320
assert build_interface_name(1, 2, 0, 3490, 1, 'GE') == 'ge-1/2/0.3490'
assert build_interface_name(1, 2, 2, 3490, 1, 'XE') == 'xe-1/2/2.3490'

# 測試 MX240/MX960/ACX7024
assert build_interface_name(1, 0, 0, 3490, 3, 'GE') == 'ge-1/0/0:3490'
assert build_interface_name(1, 1, 0, 3490, 2, 'XE') == 'xe-1/0/1:3490'
```

### 3. SNMP 連線優化

#### 問題
- E320 設備回應較慢，需要較長的 timeout
- 需要處理 SNMP 連線失敗的情況
- 缺少重試機制

#### 解決方案

```python
import time
from pysnmp.hlapi import *

class SNMPCollector:
    """SNMP 資料收集器"""
    
    def __init__(self, device_ip: str, device_type: int, community: str = 'public'):
        self.device_ip = device_ip
        self.device_type = device_type
        self.community = community
        
        # 根據設備類型設定參數
        if device_type == 1:  # E320
            self.timeout = 10
            self.retries = 3
        else:
            self.timeout = 5
            self.retries = 2
    
    def get_counter(self, oid: str, max_retries: int = None) -> Optional[int]:
        """
        取得 SNMP Counter 值，帶重試機制
        
        Args:
            oid: SNMP OID
            max_retries: 最大重試次數，None 則使用預設值
        
        Returns:
            Counter 值，失敗則返回 None
        """
        if max_retries is None:
            max_retries = self.retries
        
        for attempt in range(max_retries + 1):
            try:
                errorIndication, errorStatus, errorIndex, varBinds = next(
                    getCmd(
                        SnmpEngine(),
                        CommunityData(self.community, mpModel=1),  # SNMPv2c
                        UdpTransportTarget((self.device_ip, 161), 
                                         timeout=self.timeout, 
                                         retries=1),
                        ContextData(),
                        ObjectType(ObjectIdentity(oid))
                    )
                )
                
                if errorIndication:
                    if attempt < max_retries:
                        time.sleep(1)  # 等待後重試
                        continue
                    else:
                        raise Exception(f"SNMP Error: {errorIndication}")
                
                if errorStatus:
                    raise Exception(f"SNMP Error: {errorStatus.prettyPrint()}")
                
                # 成功取得值
                for varBind in varBinds:
                    return int(varBind[1])
                
            except Exception as e:
                if attempt < max_retries:
                    time.sleep(1)
                    continue
                else:
                    print(f"錯誤: 無法取得 {oid} from {self.device_ip}: {e}")
                    return None
        
        return None
    
    def bulk_walk(self, oid: str, max_repetitions: int = 50) -> Dict[str, int]:
        """
        使用 SNMP Bulk Walking 取得多個值
        
        Args:
            oid: 起始 OID
            max_repetitions: 每次請求的最大重複數
        
        Returns:
            OID -> 值的字典
        """
        results = {}
        
        try:
            for (errorIndication, errorStatus, errorIndex, varBinds) in bulkCmd(
                SnmpEngine(),
                CommunityData(self.community, mpModel=1),
                UdpTransportTarget((self.device_ip, 161), 
                                 timeout=self.timeout, 
                                 retries=self.retries),
                ContextData(),
                0, max_repetitions,  # non-repeaters, max-repetitions
                ObjectType(ObjectIdentity(oid)),
                lexicographicMode=False
            ):
                if errorIndication:
                    print(f"錯誤: {errorIndication}")
                    break
                
                if errorStatus:
                    print(f"錯誤: {errorStatus.prettyPrint()}")
                    break
                
                for varBind in varBinds:
                    oid_str = str(varBind[0])
                    value = int(varBind[1])
                    results[oid_str] = value
            
        except Exception as e:
            print(f"Bulk Walk 失敗: {e}")
        
        return results
```

### 4. RRD 更新邏輯修正

#### 問題
- 需要確保 RRD 檔案存在
- 需要正確處理時間戳記
- 需要避免重複更新

#### 解決方案

```python
import rrdtool
import time
import os
from typing import Optional

class RRDManager:
    """RRD 檔案管理器"""
    
    def __init__(self, base_dir: str, step: int = 1200):
        self.base_dir = base_dir
        self.step = step
        self.heartbeat = step * 2
    
    def create_user_rrd(self, username: str) -> str:
        """
        建立用戶 RRD 檔案
        
        Args:
            username: 用戶名稱
        
        Returns:
            RRD 檔案路徑
        """
        rrd_path = os.path.join(self.base_dir, 'user', f'{username}.rrd')
        
        if os.path.exists(rrd_path):
            return rrd_path
        
        # 確保目錄存在
        os.makedirs(os.path.dirname(rrd_path), exist_ok=True)
        
        # 建立 RRD 檔案
        rrdtool.create(
            rrd_path,
            '--step', str(self.step),
            '--start', str(int(time.time()) - self.step),
            f'DS:inbound:COUNTER:{self.heartbeat}:0:U',
            f'DS:outbound:COUNTER:{self.heartbeat}:0:U',
            'RRA:AVERAGE:0.5:1:2160',    # 20分鐘 * 2160 = 30天
            'RRA:AVERAGE:0.5:6:1460',    # 2小時 * 1460 = ~4個月
            'RRA:AVERAGE:0.5:72:1095',   # 1天 * 1095 = ~3年
            'RRA:MAX:0.5:1:2160',
            'RRA:MAX:0.5:6:1460',
            'RRA:MAX:0.5:72:1095'
        )
        
        return rrd_path
    
    def update_user_rrd(self, username: str, inbound: int, outbound: int, 
                       timestamp: Optional[int] = None) -> bool:
        """
        更新用戶 RRD 檔案
        
        Args:
            username: 用戶名稱
            inbound: 入站流量 (bytes)
            outbound: 出站流量 (bytes)
            timestamp: 時間戳記，None 則使用當前時間
        
        Returns:
            是否成功
        """
        if timestamp is None:
            timestamp = int(time.time())
        
        try:
            # 確保 RRD 存在
            rrd_path = self.create_user_rrd(username)
            
            # 更新 RRD
            rrdtool.update(
                rrd_path,
                f'{timestamp}:{inbound}:{outbound}'
            )
            return True
            
        except Exception as e:
            print(f"更新 RRD 失敗 ({username}): {e}")
            return False
    
    def create_sum_rrd(self, device_ip: str, bandwidth: str) -> str:
        """
        建立 Sum Layer RRD 檔案
        
        Args:
            device_ip: 設備 IP
            bandwidth: 頻寬字串 (例如: "102400_40960")
        
        Returns:
            RRD 檔案路徑
        """
        # 清理 IP 中的點號
        ip_str = device_ip.replace('.', '_')
        rrd_filename = f'{ip_str}_{bandwidth}.rrd'
        rrd_path = os.path.join(self.base_dir, 'sum', rrd_filename)
        
        if os.path.exists(rrd_path):
            return rrd_path
        
        os.makedirs(os.path.dirname(rrd_path), exist_ok=True)
        
        rrdtool.create(
            rrd_path,
            '--step', str(self.step),
            '--start', str(int(time.time()) - self.step),
            f'DS:inbound:COUNTER:{self.heartbeat}:0:U',
            f'DS:outbound:COUNTER:{self.heartbeat}:0:U',
            f'DS:user_count:GAUGE:{self.heartbeat}:0:U',
            'RRA:AVERAGE:0.5:1:2160',
            'RRA:AVERAGE:0.5:6:1460',
            'RRA:AVERAGE:0.5:72:1095',
            'RRA:MAX:0.5:1:2160',
            'RRA:MAX:0.5:6:1460',
            'RRA:MAX:0.5:72:1095'
        )
        
        return rrd_path
```

### 5. 錯誤處理機制

#### 問題
需要處理各種錯誤情況並記錄日誌。

#### 解決方案

```python
import logging
from typing import List, Dict
from dataclasses import dataclass

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/isp_monitor/logs/collector.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('collector')

@dataclass
class CollectionResult:
    """收集結果"""
    success: int = 0
    failed: int = 0
    skipped: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

def collect_device_traffic(device_ip: str, device_type: int, 
                          map_file: str) -> CollectionResult:
    """
    收集單一設備的流量資料
    
    Args:
        device_ip: 設備 IP
        device_type: 設備類型
        map_file: Map 檔案路徑
    
    Returns:
        收集結果
    """
    result = CollectionResult()
    
    try:
        # 1. 讀取 Map 檔案
        logger.info(f"開始收集 {device_ip} (類型: {device_type})")
        
        users = []
        with open(map_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                try:
                    user_data = parse_map_line(line)
                    users.append(user_data)
                except ValueError as e:
                    logger.warning(f"跳過無效行 {line_num}: {e}")
                    result.skipped += 1
        
        logger.info(f"載入 {len(users)} 筆用戶資料")
        
        # 2. 初始化收集器
        snmp = SNMPCollector(device_ip, device_type)
        rrd = RRDManager('/opt/isp_monitor/data')
        
        # 3. 收集流量資料
        for user in users:
            try:
                # 建立介面名稱
                interface = build_interface_name(
                    user['slot'], user['port'], user['vpi'], user['vci'],
                    device_type
                )
                
                # 取得流量計數器
                # (這裡需要先透過 SNMP walk 取得介面索引)
                # 簡化版本僅示範邏輯
                inbound = snmp.get_counter(f'1.3.6.1.2.1.31.1.1.1.6.{interface}')
                outbound = snmp.get_counter(f'1.3.6.1.2.1.31.1.1.1.10.{interface}')
                
                if inbound is not None and outbound is not None:
                    # 更新 RRD
                    if rrd.update_user_rrd(user['username'], inbound, outbound):
                        result.success += 1
                    else:
                        result.failed += 1
                        result.errors.append(f"RRD 更新失敗: {user['username']}")
                else:
                    result.failed += 1
                    result.errors.append(f"SNMP 查詢失敗: {user['username']}")
                
            except Exception as e:
                result.failed += 1
                result.errors.append(f"處理用戶 {user['username']} 失敗: {e}")
                logger.error(f"錯誤: {e}", exc_info=True)
        
        # 4. 記錄結果
        logger.info(
            f"收集完成: 成功={result.success}, "
            f"失敗={result.failed}, 跳過={result.skipped}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"收集設備 {device_ip} 失敗: {e}", exc_info=True)
        result.errors.append(str(e))
        return result
```

## 驗證清單

在部署前，請確認以下項目：

### Map 檔案驗證
```bash
# 使用驗證工具檢查格式
python3 collector_validator.py validate --map config/maps/map_61.64.191.74.txt

# 確認輸出顯示:
# ✓ 有效行數: XXX
# ✓ 格式完全正確！
```

### SNMP 連線測試
```bash
# 測試基本連線
snmpget -v 2c -c public 61.64.191.74 1.3.6.1.2.1.1.1.0

# 測試介面查詢
snmpwalk -v 2c -c public 61.64.191.74 1.3.6.1.2.1.2.2.1.2

# 使用驗證工具測試
python3 collector_validator.py test --ip 61.64.191.74 --type 3 --map config/maps/map_61.64.191.74.txt
```

### 收集器乾跑測試
```bash
# 模擬收集（不實際執行）
python3 collector_validator.py full --ip 61.64.191.74 --type 3 --map config/maps/map_61.64.191.74.txt

# 確認所有測試通過
```

### RRD 檔案檢查
```bash
# 檢查 RRD 是否正確建立
rrdtool info data/user/test_user.rrd

# 檢查最後更新時間
rrdtool lastupdate data/user/test_user.rrd

# 測試產生圖表
rrdtool graph test.png \
  DEF:in=data/user/test_user.rrd:inbound:AVERAGE \
  LINE1:in#00FF00:"Inbound"
```

## 常見錯誤修正

### 錯誤 1: ValueError: not enough values to unpack
**原因**: Map 檔案格式錯誤，欄位數量不正確

**解決**:
```bash
# 檢查檔案格式
python3 collector_validator.py validate --map your_map_file.txt

# 確保每行都有 4 個逗號分隔的欄位
```

### 錯誤 2: 介面格式使用斜線
**原因**: 使用了 `/` 而非 `_` 作為分隔符

**解決**:
```python
# 使用格式轉換工具
sed 's/,\([0-9]*\)\/\([0-9]*\)\/\([0-9]*\)\/\([0-9]*\),/,\1_\2_\3_\4,/g' old_map.txt > new_map.txt
```

### 錯誤 3: SNMP Timeout
**原因**: 設備回應慢或網路問題

**解決**:
- 增加 timeout 值（特別是 E320）
- 檢查防火牆規則
- 確認 SNMP community string

### 錯誤 4: RRD illegal attempt to update
**原因**: 嘗試用過去的時間戳記更新 RRD

**解決**:
- 確認系統時間正確
- 避免同時執行多個收集器
- 檢查 RRD step 設定

## 總結

完成以上修正後，收集器應該能夠:
1. ✓ 正確解析生產環境的 Map 檔案格式
2. ✓ 穩定連接各種型號的設備
3. ✓ 正確轉換介面名稱
4. ✓ 可靠地更新 RRD 檔案
5. ✓ 妥善處理各種錯誤情況

請使用提供的驗證工具進行測試，確保所有檢查都通過後再部署到生產環境。
