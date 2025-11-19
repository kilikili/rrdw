#!/usr/bin/env python3
"""
dependency_check.py - RRDW 系統相依關係檢查工具

此工具會檢查：
1. Python 版本
2. 必要 Python 套件
3. 系統工具 (rrdtool)
4. 檔案結構
5. 配置檔案
6. Map 檔案格式
"""

import sys
import os
import subprocess
import importlib
from pathlib import Path

class Colors:
    """終端顏色輸出"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """印出標題"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}\n")

def print_success(text):
    """印出成功訊息"""
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")

def print_warning(text):
    """印出警告訊息"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")

def print_error(text):
    """印出錯誤訊息"""
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")

def check_python_version():
    """檢查 Python 版本"""
    print_header("Python 版本檢查")
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    
    if version.major >= 3 and version.minor >= 6:
        print_success(f"Python 版本: {version_str} (符合要求 >= 3.6)")
        return True
    else:
        print_error(f"Python 版本: {version_str} (需要 >= 3.6)")
        return False

def check_python_packages():
    """檢查必要的 Python 套件"""
    print_header("Python 套件檢查")
    
    required_packages = {
        'pysnmp': '4.4.0',
        'configparser': None,  # 標準庫
    }
    
    optional_packages = {
        'rrdtool': '0.1.0',
    }
    
    all_ok = True
    
    # 檢查必要套件
    print(f"{Colors.BOLD}必要套件:{Colors.ENDC}")
    for package, min_version in required_packages.items():
        try:
            mod = importlib.import_module(package)
            version = getattr(mod, '__version__', 'Unknown')
            print_success(f"{package}: {version}")
        except ImportError:
            print_error(f"{package}: 未安裝")
            all_ok = False
    
    # 檢查選用套件
    print(f"\n{Colors.BOLD}選用套件:{Colors.ENDC}")
    for package, min_version in optional_packages.items():
        try:
            mod = importlib.import_module(package)
            version = getattr(mod, '__version__', 'Unknown')
            print_success(f"{package}: {version}")
        except ImportError:
            print_warning(f"{package}: 未安裝 (可選，用於 Python RRD 綁定)")
    
    return all_ok

def check_system_tools():
    """檢查系統工具"""
    print_header("系統工具檢查")
    
    tools = ['rrdtool', 'snmpwalk', 'snmpget']
    all_ok = True
    
    for tool in tools:
        try:
            result = subprocess.run(
                ['which', tool],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                path = result.stdout.strip()
                # 取得版本
                try:
                    ver_result = subprocess.run(
                        [tool, '--version'],
                        capture_output=True,
                        text=True,
                        stderr=subprocess.STDOUT
                    )
                    version = ver_result.stdout.split('\n')[0]
                    print_success(f"{tool}: {path} ({version})")
                except:
                    print_success(f"{tool}: {path}")
            else:
                print_error(f"{tool}: 未安裝")
                if tool == 'rrdtool':
                    all_ok = False
        except Exception as e:
            print_error(f"{tool}: 檢查失敗 - {e}")
            if tool == 'rrdtool':
                all_ok = False
    
    return all_ok

def check_directory_structure(base_path='/opt/isp_monitor'):
    """檢查目錄結構"""
    print_header("目錄結構檢查")
    
    required_dirs = [
        'config',
        'config/maps',
        'collectors',
        'core',
        'orchestrator',
        'data',
        'data/user',
        'data/sum',
        'data/sum2m',
        'data/circuit',
        'logs',
        'reports'
    ]
    
    all_ok = True
    
    for dir_path in required_dirs:
        full_path = Path(base_path) / dir_path
        if full_path.exists():
            print_success(f"{dir_path}: 存在")
        else:
            print_error(f"{dir_path}: 不存在")
            all_ok = False
            print(f"  建議: mkdir -p {full_path}")
    
    return all_ok

def check_config_files(base_path='/opt/isp_monitor'):
    """檢查配置檔案"""
    print_header("配置檔案檢查")
    
    config_files = {
        'config/config.ini': True,
        'config/BRAS-Map.txt': True,
    }
    
    all_ok = True
    
    for file_path, required in config_files.items():
        full_path = Path(base_path) / file_path
        if full_path.exists():
            size = full_path.stat().st_size
            print_success(f"{file_path}: 存在 ({size} bytes)")
        else:
            if required:
                print_error(f"{file_path}: 不存在 (必要)")
                all_ok = False
            else:
                print_warning(f"{file_path}: 不存在 (選用)")
    
    return all_ok

def check_map_file_format(map_file_path):
    """檢查 map 檔案格式"""
    print_header(f"Map 檔案格式檢查: {map_file_path}")
    
    if not Path(map_file_path).exists():
        print_error(f"檔案不存在: {map_file_path}")
        return False
    
    try:
        with open(map_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        valid_lines = 0
        errors = []
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split(',')
            if len(parts) != 4:
                errors.append(f"行 {i}: 欄位數量錯誤 (需要4個，實際{len(parts)}個)")
                continue
            
            username, interface, bandwidth, account = parts
            
            # 檢查介面格式 (應為底線分隔)
            if '_' not in interface:
                errors.append(f"行 {i}: 介面格式錯誤 (應使用底線分隔): {interface}")
                continue
            
            # 檢查頻寬格式 (應為底線分隔)
            if '_' not in bandwidth:
                errors.append(f"行 {i}: 頻寬格式錯誤 (應使用底線分隔): {bandwidth}")
                continue
            
            # 檢查頻寬是否為數字
            try:
                down, up = bandwidth.split('_')
                int(down)
                int(up)
            except ValueError:
                errors.append(f"行 {i}: 頻寬數值格式錯誤: {bandwidth}")
                continue
            
            valid_lines += 1
        
        if errors:
            print_warning(f"總行數: {total_lines}, 有效行數: {valid_lines}, 錯誤數: {len(errors)}")
            print("\n錯誤詳情:")
            for error in errors[:10]:  # 只顯示前10個錯誤
                print(f"  {Colors.RED}{error}{Colors.ENDC}")
            if len(errors) > 10:
                print(f"  ... 還有 {len(errors) - 10} 個錯誤")
            return False
        else:
            print_success(f"格式正確: {valid_lines} 行有效資料")
            return True
            
    except Exception as e:
        print_error(f"檢查失敗: {e}")
        return False

def check_module_imports(base_path='/opt/isp_monitor'):
    """檢查核心模組是否可以匯入"""
    print_header("核心模組匯入檢查")
    
    # 暫時加入路徑
    sys.path.insert(0, base_path)
    
    modules_to_check = [
        ('core.config_loader', 'ConfigLoader'),
        ('core.snmp_helper', 'SNMPHelper'),
        ('core.rrd_manager', 'RRDManager'),
    ]
    
    all_ok = True
    
    for module_name, class_name in modules_to_check:
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, class_name):
                print_success(f"{module_name}.{class_name}: 可匯入")
            else:
                print_error(f"{module_name}: 找不到類別 {class_name}")
                all_ok = False
        except ImportError as e:
            print_error(f"{module_name}: 無法匯入 - {e}")
            all_ok = False
        except Exception as e:
            print_error(f"{module_name}: 檢查失敗 - {e}")
            all_ok = False
    
    return all_ok

def generate_installation_guide():
    """產生安裝指令"""
    print_header("安裝建議")
    
    print(f"{Colors.BOLD}如果檢查失敗，請執行以下指令:{Colors.ENDC}\n")
    
    print("1. 安裝系統套件:")
    print("   # CentOS/RHEL")
    print("   sudo yum install -y rrdtool python3 python3-pip net-snmp-utils")
    print()
    print("   # Ubuntu/Debian")
    print("   sudo apt-get install -y rrdtool python3 python3-pip snmp")
    print()
    
    print("2. 安裝 Python 套件:")
    print("   pip3 install pysnmp pysnmp-mibs")
    print()
    
    print("3. 建立目錄結構:")
    print("   sudo mkdir -p /opt/isp_monitor/{config/maps,collectors,core,orchestrator,data/{user,sum,sum2m,circuit},logs,reports}")
    print("   sudo chown -R $(whoami):$(whoami) /opt/isp_monitor")
    print()
    
    print("4. 部署配置檔案:")
    print("   cd /opt/isp_monitor")
    print("   cp config.ini.example config/config.ini")
    print("   cp BRAS-Map.txt.example config/BRAS-Map.txt")

def main():
    """主程式"""
    print(f"\n{Colors.BOLD}RRDW 系統相依關係檢查工具{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*60}{Colors.ENDC}\n")
    
    checks = []
    
    # 執行各項檢查
    checks.append(("Python 版本", check_python_version()))
    checks.append(("Python 套件", check_python_packages()))
    checks.append(("系統工具", check_system_tools()))
    
    # 檢查目錄和配置檔案（如果指定了基礎路徑）
    if len(sys.argv) > 1:
        base_path = sys.argv[1]
        checks.append(("目錄結構", check_directory_structure(base_path)))
        checks.append(("配置檔案", check_config_files(base_path)))
        
        # 檢查 map 檔案
        if len(sys.argv) > 2:
            map_file = sys.argv[2]
            checks.append(("Map 檔案格式", check_map_file_format(map_file)))
    else:
        print_warning("未指定基礎路徑，跳過檔案系統檢查")
        print(f"使用方式: {sys.argv[0]} [base_path] [map_file]\n")
    
    # 總結
    print_header("檢查總結")
    
    all_passed = True
    for check_name, result in checks:
        if result:
            print_success(f"{check_name}: 通過")
        else:
            print_error(f"{check_name}: 失敗")
            all_passed = False
    
    if all_passed:
        print(f"\n{Colors.GREEN}{Colors.BOLD}所有檢查通過！系統已就緒。{Colors.ENDC}\n")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}部分檢查失敗，請查看上方詳情。{Colors.ENDC}\n")
        generate_installation_guide()
        return 1

if __name__ == '__main__':
    sys.exit(main())
