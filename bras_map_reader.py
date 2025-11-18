#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BRAS Map Reader
讀取並解析 BRAS-Map.txt 檔案，提供 Circuit 資訊和設備介面映射

設備類型：
1 = MX240
2 = MX960
3 = E320
4 = ACX7024
"""

import csv
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from pathlib import Path
from collections import defaultdict


# 設備類型常數
DEVICE_TYPE_MX240 = 1
DEVICE_TYPE_MX960 = 2
DEVICE_TYPE_E320 = 3
DEVICE_TYPE_ACX7024 = 4

DEVICE_TYPE_NAMES = {
    DEVICE_TYPE_MX240: "MX240",
    DEVICE_TYPE_MX960: "MX960",
    DEVICE_TYPE_E320: "E320",
    DEVICE_TYPE_ACX7024: "ACX7024"
}


@dataclass
class CircuitInfo:
    """Circuit 資訊結構"""
    bras_hostname: str
    device_type: int
    bras_ip: str
    access_switch_hostname: str
    access_switch_port_even: str
    access_switch_port_singular: str
    circuit_name: str
    trunk_number: str
    area: str
    interface_info: str  # MX 系列為完整介面名，E320 為基本介面
    slot: int
    port: int
    vlan: int
    atmf: Optional[str]
    
    @property
    def device_type_name(self) -> str:
        """取得設備類型名稱"""
        return DEVICE_TYPE_NAMES.get(self.device_type, f"Unknown({self.device_type})")
    
    @property
    def is_e320(self) -> bool:
        """是否為 E320 設備"""
        return self.device_type == DEVICE_TYPE_E320
    
    @property
    def is_mx_series(self) -> bool:
        """是否為 MX 系列設備"""
        return self.device_type in [DEVICE_TYPE_MX240, DEVICE_TYPE_MX960]
    
    @property
    def is_acx_series(self) -> bool:
        """是否為 ACX 系列設備"""
        return self.device_type == DEVICE_TYPE_ACX7024
    
    def get_full_interface(self) -> str:
        """
        取得完整介面名稱
        E320: ge-{slot}/{port}.{vlan}
        MX/ACX: 從 interface_info 取得完整介面名
        """
        if self.is_e320:
            return f"{self.interface_info}.{self.vlan}"
        else:
            # MX/ACX 系列 interface_info 已包含完整介面資訊
            return f"{self.interface_info}.{self.vlan}"
    
    def get_snmp_timeout(self) -> int:
        """
        取得 SNMP 逾時時間（秒）
        E320 較慢，需要較長的逾時時間
        """
        if self.is_e320:
            return 10
        else:
            return 3
    
    def get_collection_priority(self) -> int:
        """
        取得收集優先序（數字越小優先序越高）
        新設備優先收集
        """
        if self.is_e320:
            return 3
        elif self.is_mx_series:
            return 1
        else:  # ACX
            return 2


class BRASMapReader:
    """BRAS Map 讀取器"""
    
    def __init__(self, map_file: str = "BRAS-Map.txt"):
        """
        初始化讀取器
        
        Args:
            map_file: BRAS-Map.txt 檔案路徑
        """
        self.map_file = Path(map_file)
        self.circuits: List[CircuitInfo] = []
        self.circuits_by_bras: Dict[str, List[CircuitInfo]] = defaultdict(list)
        self.circuits_by_ip: Dict[str, List[CircuitInfo]] = defaultdict(list)
        self.circuits_by_area: Dict[str, List[CircuitInfo]] = defaultdict(list)
        self.circuits_by_device_type: Dict[int, List[CircuitInfo]] = defaultdict(list)
        self.bras_ips: Set[str] = set()
        self.bras_hostnames: Set[str] = set()
        
    def load(self) -> None:
        """載入 BRAS Map 檔案"""
        if not self.map_file.exists():
            raise FileNotFoundError(f"BRAS Map 檔案不存在: {self.map_file}")
        
        with open(self.map_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # 跳過註解和空行
                if not line or line.startswith('#'):
                    continue
                
                # 解析資料行
                parts = [p.strip() for p in line.split(',')]
                if len(parts) < 14:
                    print(f"警告：資料行欄位不足，跳過: {line}")
                    continue
                
                try:
                    circuit = CircuitInfo(
                        bras_hostname=parts[0],
                        device_type=int(parts[1]),
                        bras_ip=parts[2],
                        access_switch_hostname=parts[3],
                        access_switch_port_even=parts[4],
                        access_switch_port_singular=parts[5],
                        circuit_name=parts[6],
                        trunk_number=parts[7],
                        area=parts[8],
                        interface_info=parts[9],
                        slot=int(parts[10]),
                        port=int(parts[11]),
                        vlan=int(parts[12]),
                        atmf=parts[13] if parts[13] and parts[13] != '-' else None
                    )
                    
                    # 加入各種索引
                    self.circuits.append(circuit)
                    self.circuits_by_bras[circuit.bras_hostname].append(circuit)
                    self.circuits_by_ip[circuit.bras_ip].append(circuit)
                    self.circuits_by_area[circuit.area].append(circuit)
                    self.circuits_by_device_type[circuit.device_type].append(circuit)
                    self.bras_ips.add(circuit.bras_ip)
                    self.bras_hostnames.add(circuit.bras_hostname)
                    
                except (ValueError, IndexError) as e:
                    print(f"警告：解析資料行失敗，跳過: {line}")
                    print(f"錯誤: {e}")
                    continue
    
    def get_circuits_by_bras(self, bras_hostname: str) -> List[CircuitInfo]:
        """依 BRAS 主機名稱取得 Circuit 列表"""
        return self.circuits_by_bras.get(bras_hostname, [])
    
    def get_circuits_by_ip(self, bras_ip: str) -> List[CircuitInfo]:
        """依 BRAS IP 取得 Circuit 列表"""
        return self.circuits_by_ip.get(bras_ip, [])
    
    def get_circuits_by_area(self, area: str) -> List[CircuitInfo]:
        """依區域取得 Circuit 列表"""
        return self.circuits_by_area.get(area, [])
    
    def get_circuits_by_device_type(self, device_type: int) -> List[CircuitInfo]:
        """依設備類型取得 Circuit 列表"""
        return self.circuits_by_device_type.get(device_type, [])
    
    def get_all_bras_ips(self) -> List[str]:
        """取得所有 BRAS IP 列表"""
        return sorted(list(self.bras_ips))
    
    def get_all_bras_hostnames(self) -> List[str]:
        """取得所有 BRAS 主機名稱列表"""
        return sorted(list(self.bras_hostnames))
    
    def get_device_groups(self) -> Dict[int, List[str]]:
        """
        依設備類型分組，回傳每種設備類型的 BRAS IP 列表
        用於收集器依設備類型分批處理
        """
        groups = defaultdict(set)
        for circuit in self.circuits:
            groups[circuit.device_type].add(circuit.bras_ip)
        
        return {
            device_type: sorted(list(ips))
            for device_type, ips in groups.items()
        }
    
    def get_statistics(self) -> Dict:
        """取得統計資訊"""
        stats = {
            'total_circuits': len(self.circuits),
            'total_bras': len(self.bras_ips),
            'total_hostnames': len(self.bras_hostnames),
            'by_device_type': {},
            'by_area': {},
        }
        
        # 依設備類型統計
        for device_type, circuits in self.circuits_by_device_type.items():
            stats['by_device_type'][DEVICE_TYPE_NAMES[device_type]] = {
                'count': len(circuits),
                'bras_count': len(set(c.bras_ip for c in circuits))
            }
        
        # 依區域統計
        for area, circuits in self.circuits_by_area.items():
            stats['by_area'][area] = {
                'count': len(circuits),
                'bras_count': len(set(c.bras_ip for c in circuits)),
                'device_types': list(set(c.device_type_name for c in circuits))
            }
        
        return stats
    
    def print_statistics(self) -> None:
        """印出統計資訊"""
        stats = self.get_statistics()
        
        print("=" * 60)
        print("BRAS Map 統計資訊")
        print("=" * 60)
        print(f"總 Circuit 數量: {stats['total_circuits']}")
        print(f"總 BRAS 數量: {stats['total_bras']}")
        print(f"總主機名稱數量: {stats['total_hostnames']}")
        print()
        
        print("設備類型分布:")
        print("-" * 60)
        for device_type, info in stats['by_device_type'].items():
            print(f"  {device_type:10s}: {info['count']:3d} circuits, {info['bras_count']:2d} BRAS")
        print()
        
        print("區域分布:")
        print("-" * 60)
        for area, info in stats['by_area'].items():
            device_types = ', '.join(info['device_types'])
            print(f"  {area:10s}: {info['count']:3d} circuits, {info['bras_count']:2d} BRAS")
            print(f"              設備類型: {device_types}")
        print("=" * 60)


def main():
    """測試主程式"""
    # 載入 BRAS Map
    reader = BRASMapReader("BRAS-Map.txt")
    reader.load()
    
    # 顯示統計資訊
    reader.print_statistics()
    print()
    
    # 測試依設備類型分組
    print("設備分組（用於收集器）:")
    print("-" * 60)
    groups = reader.get_device_groups()
    for device_type, ips in groups.items():
        device_name = DEVICE_TYPE_NAMES[device_type]
        print(f"{device_name}:")
        for ip in ips:
            circuits = reader.get_circuits_by_ip(ip)
            print(f"  {ip:15s} - {len(circuits):2d} circuits")
    print()
    
    # 測試取得特定 BRAS 的 Circuit
    print("測試：取得 center_3 的 Circuit 資訊")
    print("-" * 60)
    circuits = reader.get_circuits_by_bras("center_3")
    for circuit in circuits[:3]:  # 只顯示前 3 筆
        print(f"Circuit: {circuit.circuit_name}")
        print(f"  介面: {circuit.get_full_interface()}")
        print(f"  設備類型: {circuit.device_type_name}")
        print(f"  Trunk: {circuit.trunk_number}")
        print(f"  SNMP Timeout: {circuit.get_snmp_timeout()}s")
        print()


if __name__ == "__main__":
    main()
