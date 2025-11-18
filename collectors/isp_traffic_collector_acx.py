#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACX7024 Traffic Collector
ACX7024 固定 IP 流量收集器

特點：
- ACX7024 用於固定 IP 服務
- 使用 SNMP Walk 收集所有介面
- 介面格式: ge-{slot}/{pic}/{port}.{vlan}
- 支援 Layer 1-4 RRD
"""

import os
import sys
import logging
from typing import List, Dict
from pysnmp.hlapi import *

# 導入基類
from base_collector import BaseCollector, UserTraffic


class ACXUserConfig:
    """ACX 使用者配置"""
    
    def __init__(self, config_file: str = None):
        """
        初始化配置
        
        Args:
            config_file: 配置檔案路徑（可選）
        """
        self.config_file = config_file
        self.users = {}  # {vlan: user_info}
    
    def load_from_file(self, device_ip: str, slot: int, port: int) -> Dict:
        """
        從配置檔案載入使用者
        格式類似 Map File，但用於固定 IP
        
        Args:
            device_ip: 設備 IP
            slot: 插槽
            port: 埠號
            
        Returns:
            {vlan: {'user_code': str, 'download': int, 'upload': int}}
        """
        if not self.config_file or not os.path.exists(self.config_file):
            return {}
        
        users = {}
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # 格式: user_code,download,upload,vlan,ip_address
                parts = line.split(',')
                if len(parts) >= 4:
                    user_code = parts[0]
                    download = int(parts[1])
                    upload = int(parts[2])
                    vlan = int(parts[3])
                    
                    users[vlan] = {
                        'user_code': user_code,
                        'download': download,
                        'upload': upload
                    }
        
        return users


class ACXCollector(BaseCollector):
    """ACX7024 收集器"""
    
    def __init__(self, rrd_base_dir: str, config: Dict = None):
        """
        初始化 ACX 收集器
        
        Args:
            rrd_base_dir: RRD 基礎目錄
            config: 設定字典
        """
        super().__init__(rrd_base_dir, config)
        
        # SNMP 參數
        self.snmp_community = self.config.get('snmp_community', 'public')
        self.snmp_timeout = self.config.get('snmp_timeout', 3)
        self.snmp_retries = self.config.get('snmp_retries', 2)
        
        # ACX 配置
        self.user_config = ACXUserConfig(
            self.config.get('acx_config_file')
        )
    
    def load_users(self, device_ip: str, slot: int, port: int) -> List[UserTraffic]:
        """
        載入 ACX 使用者列表
        
        ACX 可能從以下來源載入：
        1. 配置檔案（類似 Map File）
        2. SNMP Walk（自動發現）
        3. 資料庫
        
        Args:
            device_ip: 設備 IP
            slot: 插槽
            port: 埠號
            
        Returns:
            UserTraffic 列表
        """
        users = []
        
        # 方式 1: 從配置檔案載入
        user_configs = self.user_config.load_from_file(device_ip, slot, port)
        
        # 方式 2: 透過 SNMP Walk 發現介面
        interfaces = self.discover_interfaces(device_ip, slot, port)
        
        for interface_name, ifindex in interfaces.items():
            # 解析 VLAN
            # 格式: ge-0/0/2.200 或 ge-0/0/2:0.200
            vlan = self.parse_vlan_from_interface(interface_name)
            
            if vlan and vlan in user_configs:
                user_info = user_configs[vlan]
                
                user = UserTraffic(
                    user_code=user_info['user_code'],
                    interface_index=ifindex,
                    slot=slot,
                    port=port,
                    vlan=vlan,
                    download_kbps=user_info['download'],
                    upload_kbps=user_info['upload'],
                    out_octets=0
                )
                users.append(user)
        
        logging.info(f"載入 {len(users)} 個 ACX 使用者")
        return users
    
    def discover_interfaces(self, device_ip: str, slot: int, port: int) -> Dict[str, int]:
        """
        透過 SNMP Walk 發現介面
        
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
            
            # 目標介面模式
            target_prefix = f"ge-{slot}/0/{port}."
            
            for (errorIndication, errorStatus, errorIndex, varBinds) in nextCmd(
                SnmpEngine(),
                CommunityData(self.snmp_community),
                UdpTransportTarget((device_ip, 161), timeout=self.snmp_timeout, retries=self.snmp_retries),
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
                    
                    # 只處理目標介面
                    if interface_name.startswith(target_prefix):
                        # 從 OID 取得 ifindex
                        ifindex = int(oid.prettyPrint().split('.')[-1])
                        interfaces[interface_name] = ifindex
            
            logging.info(f"發現 {len(interfaces)} 個介面: {list(interfaces.keys())[:5]}...")
            
        except Exception as e:
            logging.error(f"SNMP Walk 失敗: {e}")
        
        return interfaces
    
    def parse_vlan_from_interface(self, interface_name: str) -> int:
        """
        從介面名稱解析 VLAN
        
        Args:
            interface_name: 介面名稱 (如: ge-0/0/2.200)
            
        Returns:
            VLAN ID，失敗返回 0
        """
        try:
            # 格式 1: ge-0/0/2.200
            if '.' in interface_name:
                vlan_str = interface_name.split('.')[-1]
                return int(vlan_str)
            
            # 格式 2: ge-0/0/2:0.200
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
            # 使用 SNMP GETBULK 批次查詢
            # ifHCOutOctets OID (64-bit counter)
            oid_base = '1.3.6.1.2.1.31.1.1.1.10'
            
            logging.info(f"SNMP 收集 {len(ifindexes)} 個介面...")
            
            for ifindex in ifindexes:
                oid = f"{oid_base}.{ifindex}"
                
                # SNMP GET
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
                    logging.warning(f"SNMP GET 失敗 (ifindex={ifindex}): {errorIndication or errorStatus}")
                    continue
                
                for varBind in varBinds:
                    _, value = varBind
                    out_octets = int(value)
                    traffic_data[ifindex] = out_octets
            
            logging.info(f"成功收集 {len(traffic_data)} 個介面資料")
            
        except Exception as e:
            logging.error(f"SNMP 收集失敗: {e}")
        
        return traffic_data
    
    def get_interface_name(self, slot: int, port: int) -> str:
        """
        取得 ACX 介面名稱
        格式: ge-{slot}-0-{port}
        
        Args:
            slot: 插槽
            port: 埠號
            
        Returns:
            介面名稱
        """
        # ACX7024 通常 pic = 0
        return f"ge-{slot}-0-{port}"


def main():
    """主程式"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ACX7024 流量收集器')
    parser.add_argument('device_ip', help='設備 IP 位址')
    parser.add_argument('slot', type=int, help='插槽編號')
    parser.add_argument('port', type=int, help='埠號')
    parser.add_argument('--rrd-dir', default='/home/bulks_data', help='RRD 基礎目錄')
    parser.add_argument('--community', default='public', help='SNMP Community')
    parser.add_argument('--config', help='ACX 配置檔案')
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
        'snmp_timeout': 3,
        'snmp_retries': 2,
        'acx_config_file': args.config
    }
    
    # 初始化收集器
    collector = ACXCollector(args.rrd_dir, config)
    
    # 執行收集
    result = collector.collect_device(
        args.device_ip,
        f"ACX-{args.device_ip}",
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
        print(f"使用者數: {result['user_count']}")
    print(f"耗時: {result['elapsed']:.2f} 秒")
    print("=" * 70)
    
    # 回傳碼
    sys.exit(0 if result['status'] == 'success' else 1)


if __name__ == "__main__":
    main()
