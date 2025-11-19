#!/usr/bin/env python3
"""
collector_validator.py - 收集器校正與驗證工具

此工具提供：
1. Map 檔案格式驗證
2. SNMP 連線測試
3. 介面名稱格式檢查
4. RRD 檔案結構驗證
5. 收集流程模擬測試
"""

import sys
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# 顏色輸出
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_section(title):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title:^70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.ENDC}\n")

def print_ok(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.ENDC}")

def print_warn(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.ENDC}")

def print_err(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.ENDC}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.ENDC}")


class MapFileValidator:
    """Map 檔案格式驗證器"""
    
    # 正確的格式範例
    CORRECT_FORMAT = """
    正確格式範例:
    0989703334,1_2_0_3490,35840_6144,587247394
    0981345344,3_1_0_3441,102400_40960,587272279
    
    格式說明:
    UserID,Slot_Port_VPI_VCI,Download_Upload,AccountID
    
    重點:
    - 使用底線 (_) 分隔介面和頻寬欄位
    - 頻寬單位為 bps
    - 第四欄位為電話號碼或用戶 ID
    """
    
    def __init__(self, map_file_path: str):
        self.map_file_path = map_file_path
        self.errors = []
        self.warnings = []
        self.valid_lines = []
        
    def validate(self) -> bool:
        """驗證 map 檔案"""
        print_section(f"Map 檔案驗證: {self.map_file_path}")
        
        if not Path(self.map_file_path).exists():
            print_err(f"檔案不存在: {self.map_file_path}")
            return False
        
        try:
            with open(self.map_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print_err(f"無法讀取檔案: {e}")
            return False
        
        total_lines = len(lines)
        print_info(f"總行數: {total_lines}")
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # 跳過空行和註解
            if not line or line.startswith('#'):
                continue
            
            self._validate_line(line, line_num)
        
        # 輸出結果
        print(f"\n{Colors.BOLD}驗證結果:{Colors.ENDC}")
        print_ok(f"有效行數: {len(self.valid_lines)}")
        
        if self.warnings:
            print_warn(f"警告數量: {len(self.warnings)}")
            for warn in self.warnings[:5]:
                print(f"  {warn}")
            if len(self.warnings) > 5:
                print(f"  ... 還有 {len(self.warnings) - 5} 個警告")
        
        if self.errors:
            print_err(f"錯誤數量: {len(self.errors)}")
            for err in self.errors[:10]:
                print(f"  {err}")
            if len(self.errors) > 10:
                print(f"  ... 還有 {len(self.errors) - 10} 個錯誤")
            print(self.CORRECT_FORMAT)
            return False
        else:
            print_ok("格式完全正確！")
            return True
    
    def _validate_line(self, line: str, line_num: int):
        """驗證單行"""
        parts = line.split(',')
        
        if len(parts) != 4:
            self.errors.append(
                f"行 {line_num}: 欄位數量錯誤 (需要4個，實際{len(parts)}個) - {line}"
            )
            return
        
        username, interface, bandwidth, account = [p.strip() for p in parts]
        
        # 1. 檢查用戶名稱
        if not username:
            self.errors.append(f"行 {line_num}: 用戶名稱為空")
            return
        
        # 2. 檢查介面格式 (必須使用底線)
        if '/' in interface:
            self.errors.append(
                f"行 {line_num}: 介面格式錯誤 - 應使用底線(_)而非斜線(/): {interface}"
            )
            return
        
        if '_' not in interface:
            self.errors.append(
                f"行 {line_num}: 介面格式錯誤 - 缺少底線分隔: {interface}"
            )
            return
        
        # 驗證介面格式 (應為 4 個數字)
        iface_parts = interface.split('_')
        if len(iface_parts) != 4:
            self.errors.append(
                f"行 {line_num}: 介面格式錯誤 - 應為 Slot_Port_VPI_VCI: {interface}"
            )
            return
        
        try:
            [int(x) for x in iface_parts]
        except ValueError:
            self.errors.append(
                f"行 {line_num}: 介面欄位應為數字: {interface}"
            )
            return
        
        # 3. 檢查頻寬格式 (必須使用底線)
        if '/' in bandwidth:
            self.errors.append(
                f"行 {line_num}: 頻寬格式錯誤 - 應使用底線(_)而非斜線(/): {bandwidth}"
            )
            return
        
        if '_' not in bandwidth:
            self.errors.append(
                f"行 {line_num}: 頻寬格式錯誤 - 缺少底線分隔: {bandwidth}"
            )
            return
        
        bw_parts = bandwidth.split('_')
        if len(bw_parts) != 2:
            self.errors.append(
                f"行 {line_num}: 頻寬格式錯誤 - 應為 Download_Upload: {bandwidth}"
            )
            return
        
        try:
            down, up = int(bw_parts[0]), int(bw_parts[1])
            if down <= 0 or up <= 0:
                self.warnings.append(
                    f"行 {line_num}: 頻寬數值異常 (下載:{down}, 上傳:{up})"
                )
        except ValueError:
            self.errors.append(
                f"行 {line_num}: 頻寬數值格式錯誤: {bandwidth}"
            )
            return
        
        # 4. 檢查帳號欄位
        if not account:
            self.warnings.append(f"行 {line_num}: 帳號欄位為空")
        
        # 如果都通過，加入有效行列表
        self.valid_lines.append({
            'line_num': line_num,
            'username': username,
            'interface': interface,
            'bandwidth': bandwidth,
            'account': account
        })
    
    def get_statistics(self) -> Dict:
        """取得統計資訊"""
        if not self.valid_lines:
            return {}
        
        # 統計頻寬分佈
        bandwidth_stats = {}
        for line in self.valid_lines:
            bw = line['bandwidth']
            bandwidth_stats[bw] = bandwidth_stats.get(bw, 0) + 1
        
        return {
            'total_valid': len(self.valid_lines),
            'total_errors': len(self.errors),
            'total_warnings': len(self.warnings),
            'bandwidth_distribution': bandwidth_stats
        }


class InterfaceNameConverter:
    """介面名稱格式轉換器"""
    
    @staticmethod
    def map_to_junos(slot, port, vpi, vci, device_type, interface_type='GE'):
        """
        將 map 檔案格式轉換為 Junos 介面名稱
        
        Args:
            slot: FPC/Slot 編號
            port: Port 編號  
            vpi: VPI (對 E320 是 PIC)
            vci: VCI
            device_type: 設備類型 (1=E320, 2=MX960, 3=MX240, 4=ACX7024)
            interface_type: 介面類型 (GE/XE)
        
        Returns:
            Junos 介面名稱
        """
        iface_prefix = interface_type.lower()
        
        if device_type == 1:  # E320
            # E320 格式: ge-slot/port/pic.vci
            return f"{iface_prefix}-{slot}/{port}/{vpi}.{vci}"
        else:  # MX240, MX960, ACX7024
            # 現代格式: ge-fpc/pic/port:vci
            return f"{iface_prefix}-{slot}/{vpi}/{port}:{vci}"
    
    @staticmethod
    def validate_and_convert(interface_str: str, device_type: int, 
                            interface_type: str = 'GE') -> Optional[str]:
        """
        驗證並轉換介面格式
        
        Args:
            interface_str: map 檔案中的介面字串 (例如: "1_2_0_3490")
            device_type: 設備類型
            interface_type: 介面類型
        
        Returns:
            Junos 介面名稱，或 None (如果格式錯誤)
        """
        parts = interface_str.split('_')
        if len(parts) != 4:
            return None
        
        try:
            slot, port, vpi, vci = [int(x) for x in parts]
            return InterfaceNameConverter.map_to_junos(
                slot, port, vpi, vci, device_type, interface_type
            )
        except ValueError:
            return None


class CollectorTester:
    """收集器測試工具"""
    
    def __init__(self, device_ip: str, device_type: int, map_file: str):
        self.device_ip = device_ip
        self.device_type = device_type
        self.map_file = map_file
        self.device_names = {
            1: 'E320',
            2: 'MX960',
            3: 'MX240',
            4: 'ACX7024'
        }
    
    def test_snmp_connectivity(self, community: str = 'public') -> bool:
        """測試 SNMP 連線"""
        print_section(f"SNMP 連線測試: {self.device_ip}")
        
        print_info(f"設備類型: {self.device_names.get(self.device_type, 'Unknown')}")
        print_info(f"Community: {community}")
        
        try:
            import subprocess
            
            # 測試基本連線 - sysDescr
            cmd = [
                'snmpget',
                '-v', '2c',
                '-c', community,
                self.device_ip,
                '1.3.6.1.2.1.1.1.0'  # sysDescr
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print_ok("SNMP 連線成功")
                print(f"  系統描述: {result.stdout.strip()}")
                return True
            else:
                print_err("SNMP 連線失敗")
                print(f"  錯誤: {result.stderr.strip()}")
                return False
                
        except subprocess.TimeoutExpired:
            print_err("SNMP 連線逾時")
            return False
        except FileNotFoundError:
            print_warn("snmpget 工具未安裝，跳過此測試")
            return True
        except Exception as e:
            print_err(f"測試失敗: {e}")
            return False
    
    def test_interface_query(self, sample_interface: str, 
                            community: str = 'public') -> bool:
        """測試介面查詢"""
        print_section(f"介面查詢測試: {sample_interface}")
        
        try:
            import subprocess
            
            # 先取得介面列表
            cmd = [
                'snmpwalk',
                '-v', '2c',
                '-c', community,
                '-On',  # 使用數字 OID
                self.device_ip,
                '1.3.6.1.2.1.2.2.1.2'  # ifDescr
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                interfaces = result.stdout.strip().split('\n')
                print_ok(f"找到 {len(interfaces)} 個介面")
                
                # 尋找匹配的介面
                for line in interfaces[:10]:  # 只顯示前 10 個
                    if sample_interface in line:
                        print_ok(f"  找到目標介面: {line.strip()}")
                    else:
                        print(f"  {line.strip()}")
                
                return True
            else:
                print_err("介面查詢失敗")
                return False
                
        except subprocess.TimeoutExpired:
            print_err("查詢逾時")
            return False
        except FileNotFoundError:
            print_warn("snmpwalk 工具未安裝，跳過此測試")
            return True
        except Exception as e:
            print_err(f"測試失敗: {e}")
            return False
    
    def simulate_collection(self) -> bool:
        """模擬收集流程"""
        print_section("收集流程模擬")
        
        # 1. 讀取 map 檔案
        print_info("步驟 1: 讀取 map 檔案")
        validator = MapFileValidator(self.map_file)
        if not validator.validate():
            return False
        
        stats = validator.get_statistics()
        print_ok(f"載入 {stats['total_valid']} 筆用戶資料")
        
        # 2. 顯示頻寬分佈
        print_info("\n步驟 2: 分析頻寬分佈")
        bw_dist = stats.get('bandwidth_distribution', {})
        for bw, count in sorted(bw_dist.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {bw}: {count} 用戶")
        
        # 3. 測試介面名稱轉換
        print_info("\n步驟 3: 介面名稱轉換測試")
        if validator.valid_lines:
            sample = validator.valid_lines[0]
            interface_str = sample['interface']
            junos_name = InterfaceNameConverter.validate_and_convert(
                interface_str, self.device_type
            )
            if junos_name:
                print_ok(f"Map 格式: {interface_str}")
                print_ok(f"Junos 格式: {junos_name}")
            else:
                print_err(f"轉換失敗: {interface_str}")
        
        # 4. 估算收集時間
        print_info("\n步驟 4: 估算收集時間")
        user_count = stats['total_valid']
        
        # 根據設備類型估算
        if self.device_type == 1:  # E320
            est_time = user_count * 0.1  # 每用戶 0.1 秒 (較慢)
        else:
            est_time = user_count * 0.05  # 每用戶 0.05 秒
        
        print(f"  用戶數量: {user_count}")
        print(f"  預估時間: {est_time:.1f} 秒 ({est_time/60:.1f} 分鐘)")
        
        if est_time > 600:  # 超過 10 分鐘
            print_warn("  建議啟用多進程處理以提升效能")
        
        print_ok("\n模擬完成！")
        return True


def generate_map_file_template(output_file: str, device_type: int):
    """產生 map 檔案範本"""
    print_section(f"產生 Map 檔案範本: {output_file}")
    
    device_names = {
        1: 'E320',
        2: 'MX960', 
        3: 'MX240',
        4: 'ACX7024'
    }
    
    template = f"""# Map 檔案範本 - {device_names.get(device_type, 'Unknown')}
# 格式: UserID,Slot_Port_VPI_VCI,Download_Upload(bps),AccountID
# 重要: 使用底線(_)分隔，不要使用斜線(/)

# 範例資料 - 請替換為實際資料
user001,1_0_0_100,102400_40960,1234567890
user002,1_0_0_101,51200_10240,1234567891
user003,1_1_0_100,25600_5120,1234567892
user004,2_0_0_200,10240_2048,1234567893
user005,2_1_0_150,5120_1024,1234567894

# 常見頻寬檔次 (bps):
# 100M/40M:  102400_40960
# 50M/10M:   51200_10240
# 25M/5M:    25600_5120
# 10M/2M:    10240_2048
# 5M/1M:     5120_1024
"""
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(template)
        print_ok(f"範本已產生: {output_file}")
        return True
    except Exception as e:
        print_err(f"產生失敗: {e}")
        return False


def main():
    """主程式"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='RRDW 收集器校正與驗證工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  # 驗證 map 檔案格式
  python3 collector_validator.py validate --map config/maps/map_61.64.191.74.txt
  
  # 測試 SNMP 連線
  python3 collector_validator.py test --ip 61.64.191.74 --type 3 --map config/maps/map_61.64.191.74.txt
  
  # 產生 map 檔案範本
  python3 collector_validator.py template --output test_map.txt --type 3
  
  # 完整測試流程
  python3 collector_validator.py full --ip 61.64.191.74 --type 3 --map config/maps/map_61.64.191.74.txt
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用指令')
    
    # validate 指令
    validate_parser = subparsers.add_parser('validate', help='驗證 map 檔案格式')
    validate_parser.add_argument('--map', required=True, help='Map 檔案路徑')
    
    # test 指令
    test_parser = subparsers.add_parser('test', help='測試 SNMP 連線')
    test_parser.add_argument('--ip', required=True, help='設備 IP')
    test_parser.add_argument('--type', type=int, required=True, 
                            choices=[1,2,3,4], help='設備類型 (1=E320, 2=MX960, 3=MX240, 4=ACX7024)')
    test_parser.add_argument('--map', required=True, help='Map 檔案路徑')
    test_parser.add_argument('--community', default='public', help='SNMP community')
    
    # template 指令
    template_parser = subparsers.add_parser('template', help='產生 map 檔案範本')
    template_parser.add_argument('--output', required=True, help='輸出檔案路徑')
    template_parser.add_argument('--type', type=int, required=True,
                                choices=[1,2,3,4], help='設備類型')
    
    # full 指令
    full_parser = subparsers.add_parser('full', help='執行完整測試')
    full_parser.add_argument('--ip', required=True, help='設備 IP')
    full_parser.add_argument('--type', type=int, required=True,
                            choices=[1,2,3,4], help='設備類型')
    full_parser.add_argument('--map', required=True, help='Map 檔案路徑')
    full_parser.add_argument('--community', default='public', help='SNMP community')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # 執行對應指令
    if args.command == 'validate':
        validator = MapFileValidator(args.map)
        success = validator.validate()
        
        stats = validator.get_statistics()
        if stats:
            print_section("統計資訊")
            print(f"有效資料: {stats['total_valid']} 筆")
            print(f"錯誤: {stats['total_errors']} 個")
            print(f"警告: {stats['total_warnings']} 個")
            
            print("\n頻寬分佈 (前 10 名):")
            for bw, count in sorted(
                stats['bandwidth_distribution'].items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]:
                print(f"  {bw}: {count} 用戶")
        
        return 0 if success else 1
    
    elif args.command == 'test':
        tester = CollectorTester(args.ip, args.type, args.map)
        
        # SNMP 連線測試
        snmp_ok = tester.test_snmp_connectivity(args.community)
        
        # 介面查詢測試
        if snmp_ok:
            # 從 map 檔案讀取第一個介面作為範例
            validator = MapFileValidator(args.map)
            validator.validate()
            if validator.valid_lines:
                sample = validator.valid_lines[0]
                junos_iface = InterfaceNameConverter.validate_and_convert(
                    sample['interface'], args.type
                )
                if junos_iface:
                    tester.test_interface_query(junos_iface, args.community)
        
        return 0 if snmp_ok else 1
    
    elif args.command == 'template':
        success = generate_map_file_template(args.output, args.type)
        return 0 if success else 1
    
    elif args.command == 'full':
        tester = CollectorTester(args.ip, args.type, args.map)
        
        results = []
        results.append(('Map 檔案驗證', MapFileValidator(args.map).validate()))
        results.append(('SNMP 連線測試', tester.test_snmp_connectivity(args.community)))
        results.append(('收集流程模擬', tester.simulate_collection()))
        
        # 總結
        print_section("測試總結")
        all_passed = True
        for test_name, result in results:
            if result:
                print_ok(f"{test_name}: 通過")
            else:
                print_err(f"{test_name}: 失敗")
                all_passed = False
        
        if all_passed:
            print(f"\n{Colors.GREEN}{Colors.BOLD}所有測試通過！{Colors.ENDC}\n")
            return 0
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}部分測試失敗，請查看詳情。{Colors.ENDC}\n")
            return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
