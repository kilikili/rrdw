#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BRAS Map TSV Reader
Tab 分隔的 BRAS-Map.txt 讀取器

格式：
Area	DeviceType	IP	CircuitID	Slot(Fpc)	Port	InterfaceType	BandwidthMax	IfAssign	Pic
"""

import os
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class BRASCircuit:
    """BRAS Circuit 資訊"""
    area: str                   # 區域
    device_type: int            # 設備類型 (1=MX240, 2=MX960, 3=E320, 4=ACX)
    ip: str                     # BRAS IP
    circuit_id: str             # Circuit ID
    slot: int                   # Slot (Fpc)
    port: int                   # Port
    interface_type: str         # 介面類型 (GE/XE)
    bandwidth_max: int          # 頻寬上限 (Mbps)
    if_assign: int              # 介面分配
    pic: int                    # PIC 編號
    
    @property
    def device_type_name(self) -> str:
        """設備類型名稱"""
        names = {
            1: "MX240",
            2: "MX960",
            3: "E320",
            4: "ACX"
        }
        return names.get(self.device_type, f"Unknown({self.device_type})")
    
    @property
    def interface_name(self) -> str:
        """
        組合介面名稱
        
        Returns:
            介面名稱 (如: atm 1/0, xe-1/2/0, ge-0/0/1)
        """
        if self.device_type == 3:  # E320
            # E320: atm {slot}/{port}
            return f"atm {self.slot}/{self.port}"
        
        elif self.device_type in [1, 2]:  # MX240, MX960
            # MX: {type}-{slot}/{pic}/{port}
            if_type = self.interface_type.lower()
            return f"{if_type}-{self.slot}/{self.pic}/{self.port}"
        
        elif self.device_type == 4:  # ACX
            # ACX: {type}-{slot}/{pic}/{port}
            if_type = self.interface_type.lower()
            return f"{if_type}-{self.slot}/{self.pic}/{self.port}"
        
        return f"unknown-{self.slot}/{self.port}"
    
    @property
    def map_file_name(self) -> str:
        """
        取得對應的 Map File 檔名
        
        Returns:
            Map File 檔名 (如: map_61.64.191.74_1_0.txt)
        """
        return f"map_{self.ip}_{self.slot}_{self.port}.txt"


class BRASMapTSVReader:
    """BRAS-Map.txt (Tab 分隔) 讀取器"""
    
    def __init__(self, map_file: str = "BRAS-Map.txt"):
        """
        初始化讀取器
        
        Args:
            map_file: BRAS-Map.txt 檔案路徑
        """
        self.map_file = map_file
        self.circuits: List[BRASCircuit] = []
    
    def load(self) -> None:
        """載入 BRAS-Map.txt"""
        if not os.path.exists(self.map_file):
            print(f"錯誤: 找不到檔案 {self.map_file}")
            return
        
        with open(self.map_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if not lines:
            print("錯誤: 檔案是空的")
            return
        
        # 第一行是表頭
        header = lines[0].strip()
        expected_header = "Area\tDeviceType\tIP\tCircuitID\tSlot(Fpc)\tPort\tInterfaceType\tBandwidthMax\tIfAssign\tPic"
        
        if header != expected_header:
            print(f"警告: 表頭格式可能不正確")
            print(f"期望: {expected_header}")
            print(f"實際: {header}")
        
        # 解析資料行
        for line_num, line in enumerate(lines[1:], 2):
            line = line.strip()
            
            if not line:
                continue
            
            # Tab 分隔
            parts = line.split('\t')
            
            if len(parts) < 10:
                print(f"警告: 第 {line_num} 行欄位不足 ({len(parts)}/10): {line}")
                continue
            
            try:
                circuit = BRASCircuit(
                    area=parts[0],
                    device_type=int(parts[1]),
                    ip=parts[2],
                    circuit_id=parts[3],
                    slot=int(parts[4]),
                    port=int(parts[5]),
                    interface_type=parts[6],
                    bandwidth_max=int(parts[7]),
                    if_assign=int(parts[8]),
                    pic=int(parts[9])
                )
                
                self.circuits.append(circuit)
                
            except (ValueError, IndexError) as e:
                print(f"警告: 第 {line_num} 行解析失敗: {e}")
                continue
        
        print(f"載入 {len(self.circuits)} 個 Circuit")
    
    def get_circuits_by_ip(self, ip: str) -> List[BRASCircuit]:
        """
        取得指定 IP 的所有 Circuit
        
        Args:
            ip: BRAS IP
            
        Returns:
            BRASCircuit 列表
        """
        return [c for c in self.circuits if c.ip == ip]
    
    def get_circuits_by_area(self, area: str) -> List[BRASCircuit]:
        """
        取得指定區域的所有 Circuit
        
        Args:
            area: 區域名稱
            
        Returns:
            BRASCircuit 列表
        """
        return [c for c in self.circuits if c.area == area]
    
    def get_circuits_by_device_type(self, device_type: int) -> List[BRASCircuit]:
        """
        取得指定設備類型的所有 Circuit
        
        Args:
            device_type: 設備類型 (1/2/3/4)
            
        Returns:
            BRASCircuit 列表
        """
        return [c for c in self.circuits if c.device_type == device_type]
    
    def get_all_ips(self) -> List[str]:
        """取得所有 BRAS IP（不重複）"""
        return list(set(c.ip for c in self.circuits))
    
    def get_all_areas(self) -> List[str]:
        """取得所有區域（不重複）"""
        return list(set(c.area for c in self.circuits))
    
    def get_circuit(self, ip: str, slot: int, port: int) -> Optional[BRASCircuit]:
        """
        取得特定的 Circuit
        
        Args:
            ip: BRAS IP
            slot: 插槽編號
            port: 埠號
            
        Returns:
            BRASCircuit 或 None
        """
        for circuit in self.circuits:
            if circuit.ip == ip and circuit.slot == slot and circuit.port == port:
                return circuit
        return None
    
    def print_statistics(self) -> None:
        """印出統計資訊"""
        print("=" * 70)
        print("BRAS Map 統計資訊")
        print("=" * 70)
        print(f"總 Circuit 數量: {len(self.circuits)}")
        print(f"總 BRAS 數量: {len(self.get_all_ips())}")
        print(f"總區域數量: {len(self.get_all_areas())}")
        print()
        
        # 依設備類型分組
        print("設備類型分布:")
        print("-" * 70)
        device_types = {}
        for circuit in self.circuits:
            dt = circuit.device_type_name
            if dt not in device_types:
                device_types[dt] = []
            device_types[dt].append(circuit)
        
        for device_type in sorted(device_types.keys()):
            circuits = device_types[device_type]
            ips = set(c.ip for c in circuits)
            print(f"  {device_type:8s}: {len(circuits):3d} circuits, {len(ips):2d} BRAS")
        
        print()
        
        # 依區域分組
        print("區域分布:")
        print("-" * 70)
        areas = {}
        for circuit in self.circuits:
            if circuit.area not in areas:
                areas[circuit.area] = []
            areas[circuit.area].append(circuit)
        
        for area in sorted(areas.keys()):
            circuits = areas[area]
            ips = set(c.ip for c in circuits)
            device_types = set(c.device_type_name for c in circuits)
            print(f"  {area:12s}: {len(circuits):3d} circuits, {len(ips):2d} BRAS")
            print(f"              設備類型: {', '.join(sorted(device_types))}")
        
        print("=" * 70)
    
    def export_device_list(self, output_file: str) -> None:
        """
        匯出設備清單（用於 unified_map_reader）
        
        格式: BRAS_IP,設備類型,主機名稱,區域,頻寬上限(Mbps)
        
        Args:
            output_file: 輸出檔案路徑
        """
        # 依 IP 分組
        ip_groups = {}
        for circuit in self.circuits:
            if circuit.ip not in ip_groups:
                ip_groups[circuit.ip] = []
            ip_groups[circuit.ip].append(circuit)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# BRAS 設備清單\n")
            f.write("# BRAS_IP,設備類型,主機名稱,區域,頻寬上限(Mbps)\n")
            
            for ip in sorted(ip_groups.keys()):
                circuits = ip_groups[ip]
                # 取第一個 circuit 的資訊
                first = circuits[0]
                
                # 主機名稱使用 area_ip 組合
                hostname = f"{first.area}-{ip.split('.')[-1]}"
                
                f.write(f"{ip},{first.device_type_name},{hostname},{first.area},{first.bandwidth_max}\n")
        
        print(f"已匯出設備清單: {output_file}")
    
    def list_map_files(self) -> List[str]:
        """
        列出所有應該存在的 Map File
        
        Returns:
            Map File 檔名列表
        """
        map_files = []
        for circuit in self.circuits:
            map_files.append(circuit.map_file_name)
        return sorted(set(map_files))


def main():
    """主程式"""
    import argparse
    
    parser = argparse.ArgumentParser(description='BRAS-Map.txt (TSV) 讀取器')
    parser.add_argument('--file', default='BRAS-Map.txt', help='BRAS-Map.txt 檔案路徑')
    parser.add_argument('--statistics', action='store_true', help='顯示統計')
    parser.add_argument('--ip', help='查詢特定 IP 的 Circuit')
    parser.add_argument('--area', help='查詢特定區域的 Circuit')
    parser.add_argument('--device-type', type=int, choices=[1,2,3,4], help='查詢特定設備類型')
    parser.add_argument('--export-devices', help='匯出設備清單到檔案')
    parser.add_argument('--list-map-files', action='store_true', help='列出所有 Map File')
    
    args = parser.parse_args()
    
    # 初始化讀取器
    reader = BRASMapTSVReader(args.file)
    reader.load()
    
    if not reader.circuits:
        print("沒有載入任何資料")
        return
    
    # 顯示統計
    if args.statistics:
        reader.print_statistics()
    
    # 查詢特定 IP
    elif args.ip:
        circuits = reader.get_circuits_by_ip(args.ip)
        print(f"IP {args.ip} 的 Circuit ({len(circuits)} 個):")
        print("-" * 70)
        for circuit in circuits:
            print(f"  {circuit.area:12s} {circuit.device_type_name:6s} "
                  f"Slot {circuit.slot} Port {circuit.port} "
                  f"{circuit.interface_name:15s} {circuit.bandwidth_max} Mbps")
    
    # 查詢特定區域
    elif args.area:
        circuits = reader.get_circuits_by_area(args.area)
        print(f"區域 {args.area} 的 Circuit ({len(circuits)} 個):")
        print("-" * 70)
        for circuit in circuits:
            print(f"  {circuit.ip:15s} {circuit.device_type_name:6s} "
                  f"Slot {circuit.slot} Port {circuit.port} "
                  f"{circuit.interface_name:15s}")
    
    # 查詢特定設備類型
    elif args.device_type:
        circuits = reader.get_circuits_by_device_type(args.device_type)
        device_name = {1: "MX240", 2: "MX960", 3: "E320", 4: "ACX"}[args.device_type]
        print(f"設備類型 {device_name} 的 Circuit ({len(circuits)} 個):")
        print("-" * 70)
        for circuit in circuits:
            print(f"  {circuit.ip:15s} {circuit.area:12s} "
                  f"Slot {circuit.slot} Port {circuit.port} "
                  f"{circuit.interface_name:15s}")
    
    # 匯出設備清單
    elif args.export_devices:
        reader.export_device_list(args.export_devices)
    
    # 列出 Map Files
    elif args.list_map_files:
        map_files = reader.list_map_files()
        print(f"應該存在的 Map File ({len(map_files)} 個):")
        print("-" * 70)
        for map_file in map_files:
            print(f"  {map_file}")
    
    else:
        # 預設顯示簡單統計
        print(f"載入 {len(reader.circuits)} 個 Circuit")
        print(f"BRAS 數量: {len(reader.get_all_ips())}")
        print(f"區域數量: {len(reader.get_all_areas())}")
        print()
        print("使用 --statistics 查看詳細統計")
        print("使用 --help 查看所有選項")


if __name__ == "__main__":
    main()
