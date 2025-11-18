#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BRAS Map System Test Suite
BRAS Map 系統測試套件

測試項目：
1. BRAS Map 檔案格式驗證
2. 介面名稱格式驗證（E320 vs MX/ACX）
3. Circuit 資訊完整性檢查
4. 設備類型正確性驗證
5. 介面對照表產生測試
"""

import sys
from pathlib import Path
from bras_map_reader import (
    BRASMapReader, 
    DEVICE_TYPE_MX240, 
    DEVICE_TYPE_MX960, 
    DEVICE_TYPE_E320, 
    DEVICE_TYPE_ACX7024
)


class BRASMapTester:
    """BRAS Map 測試器"""
    
    def __init__(self, map_file="BRAS-Map.txt"):
        self.map_file = map_file
        self.reader = BRASMapReader(map_file)
        self.errors = []
        self.warnings = []
        
    def log_error(self, message):
        """記錄錯誤"""
        self.errors.append(f"❌ {message}")
        print(f"❌ 錯誤: {message}")
    
    def log_warning(self, message):
        """記錄警告"""
        self.warnings.append(f"⚠️  {message}")
        print(f"⚠️  警告: {message}")
    
    def log_success(self, message):
        """記錄成功"""
        print(f"✓ {message}")
    
    def test_file_exists(self):
        """測試 1: 檔案是否存在"""
        print("\n測試 1: 檢查檔案存在性")
        print("-" * 60)
        
        if not Path(self.map_file).exists():
            self.log_error(f"BRAS-Map.txt 檔案不存在: {self.map_file}")
            return False
        
        self.log_success(f"檔案存在: {self.map_file}")
        return True
    
    def test_load_map(self):
        """測試 2: 載入 BRAS Map"""
        print("\n測試 2: 載入 BRAS Map")
        print("-" * 60)
        
        try:
            self.reader.load()
            self.log_success(f"成功載入 {len(self.reader.circuits)} 筆 Circuit 資料")
            return True
        except Exception as e:
            self.log_error(f"載入失敗: {e}")
            return False
    
    def test_device_types(self):
        """測試 3: 設備類型驗證"""
        print("\n測試 3: 設備類型驗證")
        print("-" * 60)
        
        valid_types = {DEVICE_TYPE_MX240, DEVICE_TYPE_MX960, DEVICE_TYPE_E320, DEVICE_TYPE_ACX7024}
        invalid_circuits = []
        
        for circuit in self.reader.circuits:
            if circuit.device_type not in valid_types:
                invalid_circuits.append(circuit)
                self.log_error(
                    f"無效的設備類型: {circuit.circuit_name} "
                    f"(device_type={circuit.device_type})"
                )
        
        if not invalid_circuits:
            self.log_success(f"所有 {len(self.reader.circuits)} 筆 Circuit 的設備類型均有效")
            return True
        else:
            self.log_error(f"發現 {len(invalid_circuits)} 筆無效的設備類型")
            return False
    
    def test_interface_formats(self):
        """測試 4: 介面格式驗證"""
        print("\n測試 4: 介面格式驗證")
        print("-" * 60)
        
        e320_errors = []
        mx_acx_errors = []
        
        for circuit in self.reader.circuits:
            interface = circuit.interface_info
            
            if circuit.is_e320:
                # E320 應為兩段式: ge-{slot}/{port}
                # 注意：不包含 VLAN，VLAN 會在後面加上
                if not interface.startswith('ge-'):
                    e320_errors.append(f"{circuit.circuit_name}: {interface}")
                    self.log_error(
                        f"E320 介面格式錯誤: {circuit.circuit_name} - {interface}"
                    )
                else:
                    # 驗證格式：ge-數字/數字
                    parts = interface.replace('ge-', '').split('/')
                    if len(parts) != 2:
                        e320_errors.append(f"{circuit.circuit_name}: {interface}")
                        self.log_error(
                            f"E320 介面應為兩段式 (ge-slot/port): "
                            f"{circuit.circuit_name} - {interface}"
                        )
            
            else:  # MX/ACX
                # MX/ACX 應包含三段式介面: {type}-{fpc}/{pic}/{port}
                if '-' not in interface or '/' not in interface:
                    mx_acx_errors.append(f"{circuit.circuit_name}: {interface}")
                    self.log_error(
                        f"MX/ACX 介面格式錯誤: {circuit.circuit_name} - {interface}"
                    )
                else:
                    # 驗證是否為有效的介面類型
                    interface_type = interface.split('-')[0]
                    if interface_type not in ['xe', 'ge', 'et']:
                        mx_acx_errors.append(f"{circuit.circuit_name}: {interface}")
                        self.log_warning(
                            f"未知的介面類型: {circuit.circuit_name} - {interface_type}"
                        )
        
        if not e320_errors and not mx_acx_errors:
            self.log_success("所有介面格式均符合規範")
            return True
        else:
            total_errors = len(e320_errors) + len(mx_acx_errors)
            self.log_error(f"發現 {total_errors} 筆介面格式錯誤")
            return False
    
    def test_vlan_values(self):
        """測試 5: VLAN 值驗證"""
        print("\n測試 5: VLAN 值驗證")
        print("-" * 60)
        
        invalid_vlans = []
        
        for circuit in self.reader.circuits:
            # VLAN 應在 1-4094 範圍內
            if circuit.vlan < 1 or circuit.vlan > 4094:
                invalid_vlans.append(circuit)
                self.log_error(
                    f"無效的 VLAN 值: {circuit.circuit_name} - VLAN {circuit.vlan}"
                )
        
        if not invalid_vlans:
            self.log_success(f"所有 {len(self.reader.circuits)} 筆 VLAN 值均有效 (1-4094)")
            return True
        else:
            self.log_error(f"發現 {len(invalid_vlans)} 筆無效的 VLAN 值")
            return False
    
    def test_ip_addresses(self):
        """測試 6: IP 位址格式驗證"""
        print("\n測試 6: IP 位址格式驗證")
        print("-" * 60)
        
        invalid_ips = []
        
        for circuit in self.reader.circuits:
            ip = circuit.bras_ip
            parts = ip.split('.')
            
            # 簡單的 IP 格式驗證
            if len(parts) != 4:
                invalid_ips.append(circuit)
                self.log_error(f"無效的 IP 格式: {circuit.circuit_name} - {ip}")
                continue
            
            try:
                for part in parts:
                    num = int(part)
                    if num < 0 or num > 255:
                        invalid_ips.append(circuit)
                        self.log_error(
                            f"IP 位址超出範圍: {circuit.circuit_name} - {ip}"
                        )
                        break
            except ValueError:
                invalid_ips.append(circuit)
                self.log_error(f"無效的 IP 格式: {circuit.circuit_name} - {ip}")
        
        if not invalid_ips:
            self.log_success("所有 IP 位址格式均有效")
            return True
        else:
            self.log_error(f"發現 {len(invalid_ips)} 筆無效的 IP 位址")
            return False
    
    def test_full_interface_generation(self):
        """測試 7: 完整介面名稱產生"""
        print("\n測試 7: 完整介面名稱產生")
        print("-" * 60)
        
        errors = []
        
        for circuit in self.reader.circuits:
            try:
                full_interface = circuit.get_full_interface()
                
                # 驗證完整介面名稱包含 VLAN
                if f".{circuit.vlan}" not in full_interface:
                    errors.append(circuit)
                    self.log_error(
                        f"完整介面名稱缺少 VLAN: {circuit.circuit_name} - {full_interface}"
                    )
                
                # 驗證 E320 格式
                if circuit.is_e320:
                    expected_format = f"{circuit.interface_info}.{circuit.vlan}"
                    if full_interface != expected_format:
                        errors.append(circuit)
                        self.log_error(
                            f"E320 完整介面格式錯誤: {circuit.circuit_name}\n"
                            f"  預期: {expected_format}\n"
                            f"  實際: {full_interface}"
                        )
                
            except Exception as e:
                errors.append(circuit)
                self.log_error(
                    f"產生完整介面名稱失敗: {circuit.circuit_name} - {e}"
                )
        
        if not errors:
            self.log_success("所有完整介面名稱產生正確")
            return True
        else:
            self.log_error(f"發現 {len(errors)} 筆介面名稱產生錯誤")
            return False
    
    def test_atmf_field(self):
        """測試 8: ATMF 欄位驗證"""
        print("\n測試 8: ATMF 欄位驗證")
        print("-" * 60)
        
        e320_with_atmf = []
        mx_acx_without_atmf = []
        
        for circuit in self.reader.circuits:
            if circuit.is_e320:
                # E320 不應有 ATMF
                if circuit.atmf:
                    e320_with_atmf.append(circuit)
                    self.log_warning(
                        f"E320 不應有 ATMF 欄位: {circuit.circuit_name}"
                    )
            else:
                # MX/ACX 應有 ATMF（或為空）
                if not circuit.atmf:
                    mx_acx_without_atmf.append(circuit)
                    # 這不一定是錯誤，所以只記錄警告
                    # self.log_warning(
                    #     f"MX/ACX 缺少 ATMF 欄位: {circuit.circuit_name}"
                    # )
        
        if not e320_with_atmf:
            self.log_success("ATMF 欄位使用正確")
            return True
        else:
            self.log_warning(f"發現 {len(e320_with_atmf)} 筆 E320 有 ATMF 欄位")
            return True  # 這是警告，不算錯誤
    
    def test_statistics(self):
        """測試 9: 統計資訊"""
        print("\n測試 9: 統計資訊")
        print("-" * 60)
        
        stats = self.reader.get_statistics()
        
        print(f"總 Circuit 數量: {stats['total_circuits']}")
        print(f"總 BRAS 數量: {stats['total_bras']}")
        print()
        
        print("設備類型分布:")
        for device_type, info in stats['by_device_type'].items():
            print(f"  {device_type}: {info['count']} circuits, {info['bras_count']} BRAS")
        print()
        
        print("區域分布:")
        for area, info in stats['by_area'].items():
            print(f"  {area}: {info['count']} circuits")
        
        self.log_success("統計資訊產生成功")
        return True
    
    def run_all_tests(self):
        """執行所有測試"""
        print("=" * 60)
        print("BRAS Map 系統測試")
        print("=" * 60)
        
        tests = [
            self.test_file_exists,
            self.test_load_map,
            self.test_device_types,
            self.test_interface_formats,
            self.test_vlan_values,
            self.test_ip_addresses,
            self.test_full_interface_generation,
            self.test_atmf_field,
            self.test_statistics,
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            if test():
                passed += 1
            else:
                failed += 1
        
        # 顯示測試結果摘要
        print("\n" + "=" * 60)
        print("測試結果摘要")
        print("=" * 60)
        print(f"總測試數: {len(tests)}")
        print(f"通過: {passed}")
        print(f"失敗: {failed}")
        print(f"錯誤數: {len(self.errors)}")
        print(f"警告數: {len(self.warnings)}")
        
        if failed == 0 and len(self.errors) == 0:
            print("\n✓ 所有測試通過！")
            return True
        else:
            print("\n❌ 部分測試失敗，請檢查錯誤訊息")
            return False


def main():
    """主程式"""
    tester = BRASMapTester("BRAS-Map.txt")
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
