#!/usr/bin/env python3
"""
ISP Traffic Monitor - Map檔案範本產生工具
根據BRAS-Map.txt和實際SNMP查詢結果，產生各設備的map_{ip}.txt範本
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class MapTemplateGenerator:
    """Map檔案範本產生器"""
    
    def __init__(self, snmp_community='public', snmp_timeout=5):
        self.community = snmp_community
        self.timeout = snmp_timeout
        
    def read_bras_map(self, bras_map_file: str) -> List[Dict]:
        """讀取BRAS-Map.txt檔案"""
        devices = []
        
        with open(bras_map_file, 'r') as f:
            # 跳過標題行
            header = f.readline().strip().split('\t')
            
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split('\t')
                if len(parts) >= 10:
                    device = {
                        'area': parts[0],
                        'device_type': int(parts[1]),
                        'ip': parts[2],
                        'circuit_id': parts[3],
                        'slot': parts[4],
                        'port': parts[5],
                        'interface_type': parts[6],
                        'bandwidth_max': int(parts[7]),
                        'if_assign': parts[8],
                        'pic': parts[9]
                    }
                    devices.append(device)
        
        return devices
    
    def query_snmp_interfaces(self, ip: str) -> Dict[str, str]:
        """查詢設備的SNMP介面清單"""
        print(f"正在查詢 {ip} 的介面清單...")
        
        try:
            # 使用snmpwalk查詢ifDescr
            cmd = [
                'snmpwalk',
                '-v', '2c',
                '-c', self.community,
                '-t', str(self.timeout),
                ip,
                'ifDescr'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout + 5
            )
            
            if result.returncode != 0:
                print(f"  警告: SNMP查詢失敗: {result.stderr}")
                return {}
            
            # 解析結果
            interfaces = {}
            for line in result.stdout.split('\n'):
                if 'IF-MIB::ifDescr' in line or 'ifDescr' in line:
                    # 格式: IF-MIB::ifDescr.1 = STRING: ge-0/0/0
                    parts = line.split('=')
                    if len(parts) == 2:
                        index_part = parts[0].strip()
                        desc_part = parts[1].strip()
                        
                        # 提取index
                        if '.' in index_part:
                            index = index_part.split('.')[-1]
                        else:
                            continue
                        
                        # 提取介面名稱
                        if 'STRING:' in desc_part:
                            interface_name = desc_part.split('STRING:')[1].strip()
                        else:
                            interface_name = desc_part.strip()
                        
                        interfaces[index] = interface_name
            
            print(f"  找到 {len(interfaces)} 個介面")
            return interfaces
            
        except subprocess.TimeoutExpired:
            print(f"  警告: SNMP查詢超時")
            return {}
        except Exception as e:
            print(f"  警告: 查詢時發生錯誤: {e}")
            return {}
    
    def detect_device_type(self, ip: str, snmp_interfaces: Dict[str, str]) -> str:
        """根據介面名稱格式偵測設備類型"""
        if not snmp_interfaces:
            return 'unknown'
        
        # 取第一個介面名稱作為判斷依據
        sample_interface = list(snmp_interfaces.values())[0]
        
        if 'ge-' in sample_interface:
            # 計算斜線數量
            slash_count = sample_interface.count('/')
            if slash_count == 1:
                return 'E320'  # ge-slot/port
            elif slash_count == 2:
                return 'MX/ACX'  # ge-fpc/pic/port
        
        return 'unknown'
    
    def generate_map_template_e320(self, ip: str, slot: str, port: str, 
                                   output_file: str, num_users: int = 10):
        """生成E320格式的map檔案範本"""
        print(f"\n生成 E320 格式範本: {output_file}")
        print(f"  設備: {ip}")
        print(f"  插槽/埠: {slot}/{port}")
        print(f"  範例用戶數: {num_users}")
        
        # 常見的速度方案 (kbps)
        speed_plans = [
            (5120, 384),      # 5M/384K
            (16384, 3072),    # 16M/3M
            (35840, 6144),    # 35M/6M
            (61440, 20480),   # 60M/20M
            (102400, 40960),  # 100M/40M
        ]
        
        with open(output_file, 'w') as f:
            for i in range(num_users):
                # 循環使用速度方案
                downstream, upstream = speed_plans[i % len(speed_plans)]
                
                # 生成範例資料
                username = f"user{i+1:04d}"  # user0001, user0002...
                vpi = 0
                vci = 3000 + i
                user_id = 587000000 + i
                
                # 格式: username,slot_port_vpi_vci,downstream_upstream,user_id
                line = f"{username},{slot}_{port}_{vpi}_{vci},{downstream}_{upstream},{user_id}\n"
                f.write(line)
        
        print(f"  ✓ 範本已生成: {output_file}")
    
    def generate_map_template_mx(self, ip: str, slot: str, port: str, pic: str,
                                 output_file: str, num_users: int = 10):
        """生成MX/ACX格式的map檔案範本"""
        print(f"\n生成 MX/ACX 格式範本: {output_file}")
        print(f"  設備: {ip}")
        print(f"  插槽/PIC/埠: {slot}/{pic}/{port}")
        print(f"  範例用戶數: {num_users}")
        
        # 常見的速度方案 (kbps)
        speed_plans = [
            (10240, 2048),    # 10M/2M
            (20480, 4096),    # 20M/4M
            (51200, 10240),   # 50M/10M
            (102400, 20480),  # 100M/20M
            (307200, 102400), # 300M/100M
        ]
        
        with open(output_file, 'w') as f:
            for i in range(num_users):
                # 循環使用速度方案
                downstream, upstream = speed_plans[i % len(speed_plans)]
                
                # 生成範例資料
                username = f"user{i+1:04d}"  # user0001, user0002...
                vlan = 1000 + i
                user_id = 587000000 + i
                
                # 格式: username,slot_pic_port_vlan,downstream_upstream,user_id
                line = f"{username},{slot}_{pic}_{port}_{vlan},{downstream}_{upstream},{user_id}\n"
                f.write(line)
        
        print(f"  ✓ 範本已生成: {output_file}")
    
    def generate_all_templates(self, bras_map_file: str, output_dir: str, 
                              num_users: int = 10, query_snmp: bool = False):
        """根據BRAS-Map.txt生成所有設備的map檔案範本"""
        print("=" * 70)
        print("Map檔案範本產生器")
        print("=" * 70)
        
        # 讀取BRAS-Map.txt
        print(f"\n讀取 BRAS-Map.txt: {bras_map_file}")
        devices = self.read_bras_map(bras_map_file)
        print(f"找到 {len(devices)} 個設備")
        
        # 確保輸出目錄存在
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # 按IP分組設備
        devices_by_ip = {}
        for device in devices:
            ip = device['ip']
            if ip not in devices_by_ip:
                devices_by_ip[ip] = []
            devices_by_ip[ip].append(device)
        
        print(f"\n將為 {len(devices_by_ip)} 個不同IP的設備生成範本")
        print()
        
        # 為每個IP生成範本
        for ip, ip_devices in devices_by_ip.items():
            # 使用第一個device的資訊
            first_device = ip_devices[0]
            device_type = first_device['device_type']
            slot = first_device['slot']
            port = first_device['port']
            pic = first_device['pic']
            
            # 生成檔案名稱
            output_file = os.path.join(output_dir, f"map_{ip}.txt")
            
            # 如果要查詢SNMP，先檢查設備
            if query_snmp:
                interfaces = self.query_snmp_interfaces(ip)
                if interfaces:
                    detected_type = self.detect_device_type(ip, interfaces)
                    print(f"  偵測到設備類型: {detected_type}")
            
            # 根據設備類型生成範本
            if device_type == 3:  # E320
                self.generate_map_template_e320(
                    ip, slot, port, output_file, num_users
                )
            else:  # MX/ACX系列 (Type 1, 2, 4)
                self.generate_map_template_mx(
                    ip, slot, port, pic, output_file, num_users
                )
        
        print()
        print("=" * 70)
        print(f"所有範本已生成到: {output_dir}")
        print("=" * 70)
        print()
        print("下一步:")
        print("1. 檢查生成的map檔案範本")
        print("2. 替換範例用戶資料為實際用戶資料")
        print("3. 確認速度方案正確")
        print("4. 使用 validate_map_file.py 驗證格式")

def main():
    parser = argparse.ArgumentParser(
        description='Map檔案範本產生工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 從BRAS-Map.txt生成所有範本 (每個設備10個範例用戶)
  python3 generate_map_template.py -b config/BRAS-Map.txt -o config/maps/
  
  # 生成範本並查詢SNMP驗證設備類型
  python3 generate_map_template.py -b config/BRAS-Map.txt -o config/maps/ --query-snmp
  
  # 生成範本，每個設備20個範例用戶
  python3 generate_map_template.py -b config/BRAS-Map.txt -o config/maps/ -n 20
        """
    )
    
    parser.add_argument(
        '-b', '--bras-map',
        required=True,
        help='BRAS-Map.txt檔案路徑'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        required=True,
        help='輸出目錄'
    )
    
    parser.add_argument(
        '-n', '--num-users',
        type=int,
        default=10,
        help='每個設備的範例用戶數 (預設: 10)'
    )
    
    parser.add_argument(
        '--query-snmp',
        action='store_true',
        help='查詢SNMP以驗證設備類型'
    )
    
    parser.add_argument(
        '-c', '--community',
        default='public',
        help='SNMP community string (預設: public)'
    )
    
    parser.add_argument(
        '-t', '--timeout',
        type=int,
        default=5,
        help='SNMP查詢超時時間 (秒, 預設: 5)'
    )
    
    args = parser.parse_args()
    
    # 檢查BRAS-Map.txt是否存在
    if not os.path.exists(args.bras_map):
        print(f"錯誤: BRAS-Map.txt 不存在: {args.bras_map}")
        sys.exit(1)
    
    # 建立產生器
    generator = MapTemplateGenerator(
        snmp_community=args.community,
        snmp_timeout=args.timeout
    )
    
    # 生成範本
    generator.generate_all_templates(
        bras_map_file=args.bras_map,
        output_dir=args.output_dir,
        num_users=args.num_users,
        query_snmp=args.query_snmp
    )

if __name__ == '__main__':
    main()
