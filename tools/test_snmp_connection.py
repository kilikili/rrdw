#!/usr/bin/env python3
"""
test_snmp_connection.py - SNMP 連線測試工具

快速測試 SNMP 連線並顯示設備資訊
"""

import sys
import argparse
import logging
from typing import Optional

try:
    from pysnmp.hlapi import *
except ImportError:
    print("錯誤: 缺少 pysnmp 套件")
    print("請執行: pip3 install pysnmp")
    sys.exit(1)


def test_snmp(host: str, community: str = 'public', timeout: int = 5) -> bool:
    """
    測試 SNMP 連線
    
    Args:
        host: 設備 IP
        community: SNMP Community
        timeout: 超時時間（秒）
    
    Returns:
        連線是否成功
    """
    print(f"\n{'='*60}")
    print(f"SNMP 連線測試")
    print(f"{'='*60}")
    print(f"設備 IP:    {host}")
    print(f"Community:  {community}")
    print(f"Timeout:    {timeout}s")
    print(f"{'='*60}\n")
    
    # 測試系統描述 (sysDescr)
    oid_sysdescr = '1.3.6.1.2.1.1.1.0'
    print(f"查詢 sysDescr (1.3.6.1.2.1.1.1.0)...")
    
    try:
        errorIndication, errorStatus, errorIndex, varBinds = next(
            getCmd(
                SnmpEngine(),
                CommunityData(community, mpModel=1),
                UdpTransportTarget((host, 161), timeout=timeout, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(oid_sysdescr))
            )
        )
        
        if errorIndication:
            print(f"✗ 連線失敗: {errorIndication}")
            print(f"\n可能原因:")
            print(f"  1. 設備無法連線（檢查網路）")
            print(f"  2. SNMP 服務未啟用")
            print(f"  3. Community String 錯誤")
            print(f"  4. 防火牆阻擋 UDP 161 port")
            return False
        
        if errorStatus:
            print(f"✗ SNMP 錯誤: {errorStatus.prettyPrint()}")
            return False
        
        # 成功
        for varBind in varBinds:
            sys_descr = str(varBind[1])
            print(f"✓ 連線成功！\n")
            print(f"系統描述:")
            print(f"{sys_descr}\n")
            
            # 判斷設備類型
            device_type = "未知"
            if "e320" in sys_descr.lower() or "e-320" in sys_descr.lower():
                device_type = "E320"
                print(f"設備類型: {device_type} (DeviceType=1)")
                print(f"建議 timeout: 10 秒")
                print(f"介面格式: ge-slot/port/pic.vci")
            elif "mx960" in sys_descr.lower():
                device_type = "MX960"
                print(f"設備類型: {device_type} (DeviceType=2)")
                print(f"建議 timeout: 5 秒")
                print(f"介面格式: ge-fpc/pic/port:vci")
            elif "mx240" in sys_descr.lower():
                device_type = "MX240"
                print(f"設備類型: {device_type} (DeviceType=3)")
                print(f"建議 timeout: 5 秒")
                print(f"介面格式: ge-fpc/pic/port:vci")
            elif "acx7024" in sys_descr.lower():
                device_type = "ACX7024"
                print(f"設備類型: {device_type} (DeviceType=4)")
                print(f"建議 timeout: 5 秒")
                print(f"介面格式: ge-fpc/pic/port:vci")
            
            return True
    
    except Exception as e:
        print(f"✗ 發生異常: {e}")
        return False


def get_interface_count(host: str, community: str = 'public', timeout: int = 5) -> Optional[int]:
    """
    取得介面數量
    
    Returns:
        介面數量，失敗返回 None
    """
    print(f"\n查詢介面數量...")
    
    oid_ifnumber = '1.3.6.1.2.1.2.1.0'
    
    try:
        errorIndication, errorStatus, errorIndex, varBinds = next(
            getCmd(
                SnmpEngine(),
                CommunityData(community, mpModel=1),
                UdpTransportTarget((host, 161), timeout=timeout, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(oid_ifnumber))
            )
        )
        
        if errorIndication or errorStatus:
            print(f"✗ 查詢失敗")
            return None
        
        for varBind in varBinds:
            count = int(varBind[1])
            print(f"✓ 介面數量: {count}")
            return count
    
    except Exception as e:
        print(f"✗ 查詢異常: {e}")
        return None


def show_interfaces(host: str, community: str = 'public', timeout: int = 5, max_show: int = 10):
    """
    顯示介面清單
    
    Args:
        max_show: 最多顯示幾個介面
    """
    print(f"\n查詢介面清單（顯示前 {max_show} 個）...")
    
    oid_ifdescr = '1.3.6.1.2.1.2.2.1.2'
    
    try:
        count = 0
        for (errorIndication, errorStatus, errorIndex, varBinds) in bulkCmd(
            SnmpEngine(),
            CommunityData(community, mpModel=1),
            UdpTransportTarget((host, 161), timeout=timeout, retries=1),
            ContextData(),
            0, 50,
            ObjectType(ObjectIdentity(oid_ifdescr)),
            lexicographicMode=False
        ):
            if errorIndication or errorStatus:
                print(f"✗ 查詢失敗")
                return
            
            for varBind in varBinds:
                oid_str = str(varBind[0])
                if_descr = str(varBind[1])
                
                # 解析介面索引
                parts = oid_str.split('.')
                if len(parts) > 0:
                    if_index = parts[-1]
                    print(f"  {if_index:>6}: {if_descr}")
                    count += 1
                    
                    if count >= max_show:
                        print(f"  ... (只顯示前 {max_show} 個)")
                        return
    
    except Exception as e:
        print(f"✗ 查詢異常: {e}")


def main():
    """主程式"""
    parser = argparse.ArgumentParser(
        description='SNMP 連線測試工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  # 測試基本連線
  python3 test_snmp_connection.py --host 192.168.1.1
  
  # 指定 community
  python3 test_snmp_connection.py --host 192.168.1.1 --community private
  
  # E320 設備（較長 timeout）
  python3 test_snmp_connection.py --host 61.64.191.78 --timeout 10
  
  # 顯示更多介面
  python3 test_snmp_connection.py --host 192.168.1.1 --interfaces 20
        """
    )
    
    parser.add_argument('--host', required=True, help='設備 IP 位址')
    parser.add_argument('--community', default='public', help='SNMP Community (預設: public)')
    parser.add_argument('--timeout', type=int, default=5, help='超時時間（秒，預設: 5）')
    parser.add_argument('--interfaces', type=int, default=10, 
                       help='顯示介面數量（預設: 10）')
    
    args = parser.parse_args()
    
    # 執行測試
    success = test_snmp(args.host, args.community, args.timeout)
    
    if success:
        # 取得介面數量
        if_count = get_interface_count(args.host, args.community, args.timeout)
        
        # 顯示介面清單
        if if_count:
            show_interfaces(args.host, args.community, args.timeout, args.interfaces)
        
        print(f"\n{'='*60}")
        print(f"✓ 測試成功！")
        print(f"{'='*60}")
        print(f"\n後續步驟:")
        print(f"  1. 建立 Map 檔案: config/maps/map_{args.host}.txt")
        print(f"  2. 執行收集器測試")
        print(f"\n")
        
        sys.exit(0)
    else:
        print(f"\n{'='*60}")
        print(f"✗ 測試失敗")
        print(f"{'='*60}\n")
        sys.exit(1)


if __name__ == '__main__':
    main()
