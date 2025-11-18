#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MX960 Traffic Collector
MX960 動態 IP 流量收集器（PPPoE）

特點：
- MX960 用於動態 IP 服務（PPPoE）
- 使用 SNMP Walk 收集所有介面
- 介面格式: ge-{slot}/{pic}/{port}.{vlan}
- 支援 PPPoE session 追蹤
- 支援 Layer 1-4 RRD
"""

import os
import sys
import logging
from typing import List, Dict, Optional
from pysnmp.hlapi import *

# 導入基類
from base_collector import BaseCollector, UserTraffic


class MX960SessionManager:
    """MX960 PPPoE Session 管理器"""
    
    def __init__(self, session_source: str = 'radius'):
        """
        初始化 Session 管理器
        
        Args:
            session_source: Session 來源 ('radius', 'snmp', 'file')
        """
        self.session_source = session_source
        self.sessions = {}  # {vlan: session_info}
    
    def load_from_radius(self, device_ip: str, slot: int, port: int) -> Dict:
        """
        從 RADIUS 資料庫載入當前 session
        
        Returns:
            {vlan: {'username': str, 'download': int, 'upload': int, 'ip': str}}
        """
        # TODO: 實際應該查詢 RADIUS 資料庫
        # 這裡提供介面定義
        sessions = {}
        
        try:
            import pymysql
            
            # 連接 RADIUS DB
            conn = pymysql.connect(
                host=os.getenv('RADIUS_HOST', 'localhost'),
                user=os.getenv('RADIUS_USER', 'radius'),
                password=os.getenv('RADIUS_PASS', ''),
                database=os.getenv('RADIUS_DB', 'radius')
            )
            
            cursor = conn.cursor()
            
            # 查詢當前 online 的 session
            query = """
                SELECT 
                    username,
                    framedipaddress,
                    acctsessionid,
                    nas_port_id
                FROM radacct
                WHERE 
                    acctstoptime IS NULL
                    AND nasipaddress = %s
            """
            
            cursor.execute(query, (device_ip,))
            
            for row in cursor.fetchall():
                username, ip, session_id, nas_port_id = row
                
                # 從 nas_port_id 解析 VLAN
                # 格式範例: ge-1/0/0.100
                vlan = self.parse_vlan_from_nas_port(nas_port_id)
                
                if vlan:
                    # 從使用者名稱或其他來源取得速率方案
                    download, upload = self.get_speed_profile(username)
                    
                    sessions[vlan] = {
                        'username': username,
                        'download': download,
                        'upload': upload,
                        'ip': ip,
                        'session_id': session_id
                    }
            
            cursor.close()
            conn.close()
            
            logging.info(f"從 RADIUS 載入 {len(sessions)} 個 session")
            
        except ImportError:
            logging.warning("pymysql 未安裝，無法連接 RADIUS 資料庫")
        except Exception as e:
            logging.error(f"RADIUS 查詢失敗: {e}")
        
        return sessions
    
    def load_from_file(self, config_file: str) -> Dict:
        """
        從配置檔案載入 session
        用於測試或備用
        
        格式: username,download,upload,vlan,ip
        """
        sessions = {}
        
        if not config_file or not os.path.exists(config_file):
            return sessions
        
        with open(config_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split(',')
                if len(parts) >= 4:
                    username = parts[0]
                    download = int(parts[1])
                    upload = int(parts[2])
                    vlan = int(parts[3])
                    ip = parts[4] if len(parts) > 4 else ''
                    
                    sessions[vlan] = {
                        'username': username,
                        'download': download,
                        'upload': upload,
                        'ip': ip
                    }
        
        return sessions
    
    def parse_vlan_from_nas_port(self, nas_port_id: str) -> int:
        """解析 NAS Port ID 取得 VLAN"""
        try:
            if '.' in nas_port_id:
                vlan_str = nas_port_id.split('.')[-1]
                return int(vlan_str)
        except (ValueError, IndexError):
            pass
        return 0
    
    def get_speed_profile(self, username: str) -> tuple[int, int]:
        """
        取得使用者速率方案
        
        Returns:
            (download_kbps, upload_kbps)
        """
        # TODO: 實際應該從資料庫查詢
        # 這裡返回預設值
        return (102400, 40960)  # 100M/40M


class MX960Collector(BaseCollector):
    """MX960 收集器"""
    
    def __init__(self, rrd_base_dir: str, config: Dict = None):
        """
        初始化 MX960 收集器
        
        Args:
            rrd_base_dir: RRD 基礎目錄
            config: 設定字典
        """
        super().__init__(rrd_base_dir, config)
        
        # SNMP 參數
        self.snmp_community = self.config.get('snmp_community', 'public')
        self.snmp_timeout = self.config.get('snmp_timeout', 2)
        self.snmp_retries = self.config.get('snmp_retries', 2)
        
        # Session 管理器
        session_source = self.config.get('session_source', 'radius')
        self.session_mgr = MX960SessionManager(session_source)
    
    def load_users(self, device_ip: str, slot: int, port: int) -> List[UserTraffic]:
        """
        載入 MX960 使用者列表
        
        Args:
            device_ip: 設備 IP
            slot: 插槽
            port: 埠號
            
        Returns:
            UserTraffic 列表
        """
        users = []
        
        # 方式 1: 從 RADIUS 載入當前 session
        sessions = self.session_mgr.load_from_radius(device_ip, slot, port)
        
        # 如果 RADIUS 沒資料，嘗試從檔案載入
        if not sessions and self.config.get('mx960_config_file'):
            sessions = self.session_mgr.load_from_file(
                self.config['mx960_config_file']
            )
        
        # 方式 2: 透過 SNMP Walk 發現介面
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
        
        logging.info(f"載入 {len(users)} 個 MX960 PPPoE 使用者")
        return users
    
    def discover_interfaces(self, device_ip: str, slot: int, port: int) -> Dict[str, int]:
        """
        透過 SNMP Walk 發現介面
        
        MX960 介面格式:
        - 實體介面: ge-{slot}/{pic}/{port}
        - 邏輯介面: ge-{slot}/{pic}/{port}.{vlan}
        
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
            # MX960 通常 pic=0，但也可能有其他值
            target_patterns = [
                f"ge-{slot}/0/{port}.",
                f"ge-{slot}/1/{port}.",
                f"ge-{slot}/2/{port}.",
            ]
            
            logging.info(f"SNMP Walk 搜尋介面: {target_patterns[0]}*")
            
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
        
        Args:
            interface_name: 介面名稱 (如: ge-1/0/0.100)
            
        Returns:
            VLAN ID，失敗返回 0
        """
        try:
            if '.' in interface_name:
                vlan_str = interface_name.split('.')[-1]
                return int(vlan_str)
            return 0
        except (ValueError, IndexError):
            return 0
    
    def snmp_collect(self, device_ip: str, users: List[UserTraffic]) -> Dict[int, int]:
        """
        SNMP 收集流量資料
        使用 SNMP GETBULK 提高效率
        
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
            
            # 批次收集（每次最多 50 個）
            batch_size = 50
            for i in range(0, len(ifindexes), batch_size):
                batch = ifindexes[i:i+batch_size]
                
                # 使用 getBulk
                for ifindex in batch:
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
                        continue
                    
                    for varBind in varBinds:
                        _, value = varBind
                        out_octets = int(value)
                        traffic_data[ifindex] = out_octets
                
                if i + batch_size < len(ifindexes):
                    logging.debug(f"已處理 {i+batch_size}/{len(ifindexes)}")
            
            logging.info(f"成功收集 {len(traffic_data)} 個介面資料")
            
        except Exception as e:
            logging.error(f"SNMP 收集失敗: {e}")
        
        return traffic_data
    
    def get_interface_name(self, slot: int, port: int) -> str:
        """
        取得 MX960 介面名稱
        格式: ge-{slot}-{pic}-{port}
        
        Args:
            slot: 插槽
            port: 埠號
            
        Returns:
            介面名稱
        """
        # MX960 通常 pic=0
        return f"ge-{slot}-0-{port}"


def main():
    """主程式"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MX960 流量收集器（PPPoE）')
    parser.add_argument('device_ip', help='設備 IP 位址')
    parser.add_argument('slot', type=int, help='插槽編號')
    parser.add_argument('port', type=int, help='埠號')
    parser.add_argument('--rrd-dir', default='/home/bulks_data', help='RRD 基礎目錄')
    parser.add_argument('--community', default='public', help='SNMP Community')
    parser.add_argument('--config', help='MX960 配置檔案')
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
        'session_source': args.session_source,
        'mx960_config_file': args.config
    }
    
    # 初始化收集器
    collector = MX960Collector(args.rrd_dir, config)
    
    # 執行收集
    result = collector.collect_device(
        args.device_ip,
        f"MX960-{args.device_ip}",
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
    print(f"耗時: {result['elapsed']:.2f} 秒")
    print("=" * 70)
    
    # 回傳碼
    sys.exit(0 if result['status'] == 'success' else 1)


if __name__ == "__main__":
    main()
