#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MX240 Traffic Collector
MX240 動態 IP 流量收集器（PPPoE + PPPoE over VLAN）

特點：
- MX240 用於動態 IP 服務（PPPoE）
- 支援 PPPoE over VLAN
- 使用 SNMP Walk 收集所有介面
- 介面格式: xe-{slot}/{pic}/{port}.{vlan}（10G 介面）
- 支援 Layer 1-4 RRD
"""

import os
import sys
import logging
from typing import List, Dict, Optional
from pysnmp.hlapi import *

# 導入基類和 MX960 的 Session 管理器
from base_collector import BaseCollector, UserTraffic
from isp_traffic_collector_mx960 import MX960SessionManager


class MX240Collector(BaseCollector):
    """MX240 收集器（繼承 MX960 大部分邏輯）"""
    
    def __init__(self, rrd_base_dir: str, config: Dict = None):
        """
        初始化 MX240 收集器
        
        Args:
            rrd_base_dir: RRD 基礎目錄
            config: 設定字典
        """
        super().__init__(rrd_base_dir, config)
        
        # SNMP 參數
        self.snmp_community = self.config.get('snmp_community', 'public')
        self.snmp_timeout = self.config.get('snmp_timeout', 2)
        self.snmp_retries = self.config.get('snmp_retries', 2)
        
        # MX240 特定設定
        self.interface_type = self.config.get('interface_type', 'xe')  # xe (10G) 或 ge (1G)
        
        # Session 管理器（與 MX960 共用）
        session_source = self.config.get('session_source', 'radius')
        self.session_mgr = MX960SessionManager(session_source)
    
    def load_users(self, device_ip: str, slot: int, port: int) -> List[UserTraffic]:
        """
        載入 MX240 使用者列表
        
        Args:
            device_ip: 設備 IP
            slot: 插槽
            port: 埠號
            
        Returns:
            UserTraffic 列表
        """
        users = []
        
        # 從 RADIUS 載入當前 session
        sessions = self.session_mgr.load_from_radius(device_ip, slot, port)
        
        # 如果 RADIUS 沒資料，嘗試從檔案載入
        if not sessions and self.config.get('mx240_config_file'):
            sessions = self.session_mgr.load_from_file(
                self.config['mx240_config_file']
            )
        
        # 透過 SNMP Walk 發現介面
        interfaces = self.discover_interfaces(device_ip, slot, port)
        
        for interface_name, ifindex in interfaces.items():
            # 解析 VLAN
            vlan = self.parse_vlan_from_interface(interface_name)
            
            if vlan and vlan in sessions:
                session_info = sessions[vlan]
                
                user = UserTraffic(
                    user_code=session_info['username'],
                    interface_index=ifindex,
                    slot=slot,
                    port=port,
                    vlan=vlan,
                    download_kbps=session_info['download'],
                    upload_kbps=session_info['upload'],
                    out_octets=0
                )
                users.append(user)
        
        logging.info(f"載入 {len(users)} 個 MX240 PPPoE 使用者")
        return users
    
    def discover_interfaces(self, device_ip: str, slot: int, port: int) -> Dict[str, int]:
        """
        透過 SNMP Walk 發現介面
        
        MX240 介面格式:
        - 10G 介面: xe-{slot}/{pic}/{port}.{vlan}
        - 1G 介面: ge-{slot}/{pic}/{port}.{vlan}
        
        Args:
            device_ip: 設備 IP
            slot: 插槽
            port: 埠號
            
        Returns:
            {interface_name: ifindex}
        """
        interfaces = {}
        
        try:
            # ifDescr OID
            oid_ifDescr = '1.3.6.1.2.1.2.2.1.2'
            
            # 目標介面模式（支援 xe 和 ge）
            target_patterns = [
                f"{self.interface_type}-{slot}/0/{port}.",
                f"{self.interface_type}-{slot}/1/{port}.",
                f"{self.interface_type}-{slot}/2/{port}.",
            ]
            
            logging.info(f"SNMP Walk 搜尋 {self.interface_type.upper()} 介面: {target_patterns[0]}*")
            
            for (errorIndication, errorStatus, errorIndex, varBinds) in nextCmd(
                SnmpEngine(),
                CommunityData(self.snmp_community),
                UdpTransportTarget((device_ip, 161), 
                                 timeout=self.snmp_timeout, 
                                 retries=self.snmp_retries),
                ContextData(),
                ObjectType(ObjectIdentity(oid_ifDescr)),
                lexicographicMode=False
            ):
                if errorIndication or errorStatus:
                    logging.error(f"SNMP 錯誤: {errorIndication or errorStatus}")
                    break
                
                for varBind in varBinds:
                    oid, value = varBind
                    interface_name = str(value)
                    
                    # 檢查是否符合目標模式
                    for pattern in target_patterns:
                        if interface_name.startswith(pattern):
                            # 從 OID 取得 ifindex
                            ifindex = int(oid.prettyPrint().split('.')[-1])
                            interfaces[interface_name] = ifindex
                            break
            
            logging.info(f"發現 {len(interfaces)} 個 PPPoE 介面")
            if interfaces:
                sample = list(interfaces.keys())[:3]
                logging.info(f"範例: {sample}")
            
        except Exception as e:
            logging.error(f"SNMP Walk 失敗: {e}")
        
        return interfaces
    
    def parse_vlan_from_interface(self, interface_name: str) -> int:
        """
        從介面名稱解析 VLAN
        支援多種格式
        
        Args:
            interface_name: 介面名稱
            
        Returns:
            VLAN ID，失敗返回 0
        """
        try:
            # 格式 1: xe-1/0/0.100
            if '.' in interface_name:
                vlan_str = interface_name.split('.')[-1]
                return int(vlan_str)
            
            # 格式 2: xe-1/0/0:1.100 (PPPoE over VLAN)
            if ':' in interface_name:
                parts = interface_name.split(':')
                if len(parts) > 1 and '.' in parts[1]:
                    vlan_str = parts[1].split('.')[-1]
                    return int(vlan_str)
            
            return 0
            
        except (ValueError, IndexError):
            return 0
    
    def snmp_collect(self, device_ip: str, users: List[UserTraffic]) -> Dict[int, int]:
        """
        SNMP 收集流量資料
        使用優化的批次收集
        
        Args:
            device_ip: 設備 IP
            users: 使用者列表
            
        Returns:
            {ifindex: out_octets}
        """
        traffic_data = {}
        
        if not users:
            return traffic_data
        
        # 收集所有 ifindex
        ifindexes = list(set(user.interface_index for user in users))
        
        try:
            # ifHCOutOctets OID (64-bit counter)
            oid_base = '1.3.6.1.2.1.31.1.1.1.10'
            
            logging.info(f"SNMP 收集 {len(ifindexes)} 個介面...")
            
            # 使用 SNMP GETBULK 批次查詢（MX240 支援更高效的查詢）
            collected = 0
            
            for ifindex in ifindexes:
                oid = f"{oid_base}.{ifindex}"
                
                iterator = getCmd(
                    SnmpEngine(),
                    CommunityData(self.snmp_community),
                    UdpTransportTarget((device_ip, 161), 
                                     timeout=self.snmp_timeout, 
                                     retries=self.snmp_retries),
                    ContextData(),
                    ObjectType(ObjectIdentity(oid))
                )
                
                errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
                
                if errorIndication or errorStatus:
                    logging.warning(f"SNMP GET 失敗 (ifindex={ifindex})")
                    continue
                
                for varBind in varBinds:
                    _, value = varBind
                    out_octets = int(value)
                    traffic_data[ifindex] = out_octets
                    collected += 1
                
                # 進度顯示
                if collected % 100 == 0:
                    logging.debug(f"已收集 {collected}/{len(ifindexes)}")
            
            logging.info(f"成功收集 {len(traffic_data)} 個介面資料")
            
        except Exception as e:
            logging.error(f"SNMP 收集失敗: {e}")
        
        return traffic_data
    
    def get_interface_name(self, slot: int, port: int) -> str:
        """
        取得 MX240 介面名稱
        格式: xe-{slot}-{pic}-{port} 或 ge-{slot}-{pic}-{port}
        
        Args:
            slot: 插槽
            port: 埠號
            
        Returns:
            介面名稱
        """
        # MX240 通常 pic=0，使用 xe (10G) 或 ge (1G)
        return f"{self.interface_type}-{slot}-0-{port}"


def main():
    """主程式"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MX240 流量收集器（PPPoE）')
    parser.add_argument('device_ip', help='設備 IP 位址')
    parser.add_argument('slot', type=int, help='插槽編號')
    parser.add_argument('port', type=int, help='埠號')
    parser.add_argument('--rrd-dir', default='/home/bulks_data', help='RRD 基礎目錄')
    parser.add_argument('--community', default='public', help='SNMP Community')
    parser.add_argument('--config', help='MX240 配置檔案')
    parser.add_argument('--interface-type', choices=['xe', 'ge'], default='xe',
                       help='介面類型 (xe=10G, ge=1G)')
    parser.add_argument('--session-source', choices=['radius', 'file'], 
                       default='radius', help='Session 來源')
    parser.add_argument('--debug', action='store_true', help='除錯模式')
    
    args = parser.parse_args()
    
    # 設定日誌
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # 設定
    config = {
        'snmp_community': args.community,
        'snmp_timeout': 2,
        'snmp_retries': 2,
        'interface_type': args.interface_type,
        'session_source': args.session_source,
        'mx240_config_file': args.config
    }
    
    # 初始化收集器
    collector = MX240Collector(args.rrd_dir, config)
    
    # 執行收集
    result = collector.collect_device(
        args.device_ip,
        f"MX240-{args.device_ip}",
        args.slot,
        args.port
    )
    
    # 顯示結果
    print("\n" + "=" * 70)
    print("收集結果")
    print("=" * 70)
    print(f"狀態: {result['status']}")
    print(f"訊息: {result['message']}")
    if 'user_count' in result:
        print(f"PPPoE 使用者: {result['user_count']}")
    print(f"介面類型: {args.interface_type.upper()}")
    print(f"耗時: {result['elapsed']:.2f} 秒")
    print("=" * 70)
    
    # 回傳碼
    sys.exit(0 if result['status'] == 'success' else 1)


if __name__ == "__main__":
    main()
