#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interface Mapping Generator
介面對照表產生器

根據 BRAS-Map.txt 產生完整的介面對照表，包含：
- Access Switch 資訊
- BRAS 設備資訊  
- 介面映射關係
- Circuit 資訊

輸出格式符合截圖中的表格格式。
"""

import csv
from bras_map_reader import BRASMapReader, DEVICE_TYPE_NAMES


class InterfaceMappingGenerator:
    """介面對照表產生器"""
    
    def __init__(self, map_file="BRAS-Map.txt"):
        """
        初始化產生器
        
        Args:
            map_file: BRAS-Map.txt 檔案路徑
        """
        self.map_reader = BRASMapReader(map_file)
        
    def load(self):
        """載入 BRAS Map"""
        self.map_reader.load()
    
    def generate_csv(self, output_file="interface_mapping.csv"):
        """
        產生 CSV 格式的介面對照表
        
        格式（依照截圖）：
        access_switch_hostname, access_switch_port_even, access_switch_port_singular,
        mx_port, bras_ip, bras_hostname, atmf, slot, port, vlan, trunk_number, area
        
        Args:
            output_file: 輸出檔案名稱
        """
        print(f"產生介面對照表: {output_file}")
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 寫入標頭
            headers = [
                'access_switch_hostname',
                'access_switch_port_even', 
                'access_switch_port_singular',
                'mx_port',  # E320 此欄為空或顯示介面資訊
                'bras_ip',
                'bras_hostname',
                'atmf',
                'slot',
                'port',
                'vlan',
                'trunk_number',
                'area',
                'device_type',  # 新增：設備類型
                'circuit_name'  # 新增：Circuit 名稱
            ]
            writer.writerow(headers)
            
            # 寫入資料
            for circuit in self.map_reader.circuits:
                # MX/ACX 系列使用 interface_info，E320 留空或顯示基本介面
                mx_port = circuit.interface_info if not circuit.is_e320 else ''
                
                # ATMF 欄位（E320 無此欄位）
                atmf = circuit.atmf if circuit.atmf else ''
                
                row = [
                    circuit.access_switch_hostname,
                    circuit.access_switch_port_even,
                    circuit.access_switch_port_singular,
                    mx_port,
                    circuit.bras_ip,
                    circuit.bras_hostname,
                    atmf,
                    circuit.slot,
                    circuit.port,
                    circuit.vlan,
                    circuit.trunk_number,
                    circuit.area,
                    circuit.device_type_name,
                    circuit.circuit_name
                ]
                writer.writerow(row)
        
        print(f"產生完成，共 {len(self.map_reader.circuits)} 筆資料")
    
    def generate_by_device_type(self, output_dir="."):
        """
        依設備類型分別產生介面對照表
        
        Args:
            output_dir: 輸出目錄
        """
        print("依設備類型產生介面對照表...")
        
        for device_type, circuits in self.map_reader.circuits_by_device_type.items():
            device_name = DEVICE_TYPE_NAMES[device_type]
            output_file = f"{output_dir}/interface_mapping_{device_name}.csv"
            
            print(f"  產生 {device_name} 對照表: {output_file}")
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # 標頭
                if device_type == 3:  # E320
                    headers = [
                        'access_switch_hostname',
                        'access_switch_port_even',
                        'e320_interface',  # E320 特有
                        'bras_ip',
                        'bras_hostname',
                        'slot',
                        'port',
                        'vlan',
                        'trunk_number',
                        'area',
                        'circuit_name'
                    ]
                else:  # MX/ACX
                    headers = [
                        'access_switch_hostname',
                        'access_switch_port_even',
                        'access_switch_port_singular',
                        'mx_port',
                        'bras_ip',
                        'bras_hostname',
                        'atmf',
                        'slot',
                        'port',
                        'vlan',
                        'trunk_number',
                        'area',
                        'circuit_name'
                    ]
                
                writer.writerow(headers)
                
                # 資料
                for circuit in circuits:
                    if device_type == 3:  # E320
                        row = [
                            circuit.access_switch_hostname,
                            circuit.access_switch_port_even,
                            circuit.interface_info,
                            circuit.bras_ip,
                            circuit.bras_hostname,
                            circuit.slot,
                            circuit.port,
                            circuit.vlan,
                            circuit.trunk_number,
                            circuit.area,
                            circuit.circuit_name
                        ]
                    else:  # MX/ACX
                        row = [
                            circuit.access_switch_hostname,
                            circuit.access_switch_port_even,
                            circuit.access_switch_port_singular,
                            circuit.interface_info,
                            circuit.bras_ip,
                            circuit.bras_hostname,
                            circuit.atmf if circuit.atmf else '',
                            circuit.slot,
                            circuit.port,
                            circuit.vlan,
                            circuit.trunk_number,
                            circuit.area,
                            circuit.circuit_name
                        ]
                    
                    writer.writerow(row)
            
            print(f"    完成，共 {len(circuits)} 筆資料")
    
    def generate_by_area(self, output_dir="."):
        """
        依區域產生介面對照表
        
        Args:
            output_dir: 輸出目錄
        """
        print("依區域產生介面對照表...")
        
        for area, circuits in self.map_reader.circuits_by_area.items():
            # 檔名中的區域名稱處理（移除特殊字元）
            safe_area = area.replace('/', '_').replace('\\', '_')
            output_file = f"{output_dir}/interface_mapping_{safe_area}.csv"
            
            print(f"  產生 {area} 對照表: {output_file}")
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # 標頭（包含所有可能欄位）
                headers = [
                    'access_switch_hostname',
                    'access_switch_port_even',
                    'access_switch_port_singular',
                    'interface',  # MX 為 mx_port，E320 為 e320_interface
                    'bras_ip',
                    'bras_hostname',
                    'atmf',
                    'slot',
                    'port',
                    'vlan',
                    'trunk_number',
                    'device_type',
                    'circuit_name'
                ]
                
                writer.writerow(headers)
                
                # 資料
                for circuit in circuits:
                    row = [
                        circuit.access_switch_hostname,
                        circuit.access_switch_port_even,
                        circuit.access_switch_port_singular,
                        circuit.interface_info,
                        circuit.bras_ip,
                        circuit.bras_hostname,
                        circuit.atmf if circuit.atmf else '',
                        circuit.slot,
                        circuit.port,
                        circuit.vlan,
                        circuit.trunk_number,
                        circuit.device_type_name,
                        circuit.circuit_name
                    ]
                    
                    writer.writerow(row)
            
            print(f"    完成，共 {len(circuits)} 筆資料")
    
    def print_summary(self):
        """印出摘要資訊"""
        print("\n" + "=" * 60)
        print("介面對照表摘要")
        print("=" * 60)
        
        # 依設備類型
        print("\n設備類型分布:")
        for device_type, circuits in self.map_reader.circuits_by_device_type.items():
            device_name = DEVICE_TYPE_NAMES[device_type]
            unique_bras = len(set(c.bras_hostname for c in circuits))
            unique_switches = len(set(c.access_switch_hostname for c in circuits))
            
            print(f"  {device_name}:")
            print(f"    Circuit 數量: {len(circuits)}")
            print(f"    BRAS 數量: {unique_bras}")
            print(f"    Access Switch 數量: {unique_switches}")
        
        # 依區域
        print("\n區域分布:")
        for area, circuits in self.map_reader.circuits_by_area.items():
            unique_bras = len(set(c.bras_hostname for c in circuits))
            device_types = set(c.device_type_name for c in circuits)
            
            print(f"  {area}:")
            print(f"    Circuit 數量: {len(circuits)}")
            print(f"    BRAS 數量: {unique_bras}")
            print(f"    設備類型: {', '.join(sorted(device_types))}")
        
        print("=" * 60)


def main():
    """主程式"""
    print("=" * 60)
    print("介面對照表產生器")
    print("=" * 60)
    print()
    
    # 初始化產生器
    generator = InterfaceMappingGenerator("BRAS-Map.txt")
    
    # 載入資料
    generator.load()
    
    # 產生統一的介面對照表
    generator.generate_csv("interface_mapping.csv")
    print()
    
    # 依設備類型產生
    generator.generate_by_device_type(".")
    print()
    
    # 依區域產生
    generator.generate_by_area(".")
    print()
    
    # 印出摘要
    generator.print_summary()


if __name__ == "__main__":
    main()
