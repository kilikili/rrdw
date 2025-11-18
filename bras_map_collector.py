#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RRDW Data Collector with BRAS Map Integration
整合 BRAS Map 的資料收集器，支援 E320, MX240, MX960, ACX7024

功能：
1. 從 BRAS-Map.txt 讀取 Circuit 和設備資訊
2. 依設備類型調整 SNMP 收集策略
3. 支援不同介面格式（E320 兩段式，MX/ACX 三段式）
4. 產生相容於現有 RRD 格式的資料
"""

import sys
import time
import mysql.connector
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pysnmp.hlapi import *
from bras_map_reader import BRASMapReader, DEVICE_TYPE_E320


class BRASMapCollector:
    """整合 BRAS Map 的資料收集器"""
    
    def __init__(self, map_file="BRAS-Map.txt", db_config=None):
        """
        初始化收集器
        
        Args:
            map_file: BRAS-Map.txt 檔案路徑
            db_config: 資料庫連線設定（選用）
        """
        self.map_reader = BRASMapReader(map_file)
        self.db_config = db_config
        self.community = 'public'
        
        # 收集結果儲存
        self.traffic_data = defaultdict(dict)  # {bras_ip: {interface: (in_octets, out_octets)}}
        self.interface_mapping = {}  # {bras_ip: {vlan: interface_name}}
        
    def load_bras_map(self):
        """載入 BRAS Map"""
        print("載入 BRAS Map...")
        self.map_reader.load()
        self.map_reader.print_statistics()
        print()
    
    def load_user_map_from_db(self):
        """
        從資料庫載入使用者對應表
        格式：user_code -> (bras_ip, slot, port, vpi, vci, download, upload)
        """
        if not self.db_config:
            print("警告：未設定資料庫連線，跳過使用者對應表載入")
            return {}
        
        print("從資料庫載入使用者對應表...")
        user_map = {}
        
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            # 查詢使用者對應表
            # 根據實際資料庫結構調整 SQL
            query = """
                SELECT user_code, bras_ip, slot, port, vpi, vci, download, upload
                FROM user_mapping
                WHERE status = 'active'
            """
            
            cursor.execute(query)
            for row in cursor.fetchall():
                user_code, bras_ip, slot, port, vpi, vci, download, upload = row
                user_map[user_code] = {
                    'bras_ip': bras_ip,
                    'slot': slot,
                    'port': port,
                    'vpi': vpi,
                    'vci': vci,
                    'download': download,
                    'upload': upload
                }
            
            cursor.close()
            conn.close()
            
            print(f"載入 {len(user_map)} 筆使用者對應資料")
            
        except Exception as e:
            print(f"載入使用者對應表失敗: {e}")
            return {}
        
        return user_map
    
    def get_interface_name_from_circuit(self, circuit):
        """
        從 Circuit 資訊取得介面名稱
        
        Args:
            circuit: CircuitInfo 物件
            
        Returns:
            完整介面名稱
        """
        return circuit.get_full_interface()
    
    def snmp_walk_interfaces(self, bras_ip, timeout=3):
        """
        對 BRAS 執行 SNMP Walk 取得所有介面資訊
        
        Args:
            bras_ip: BRAS IP 位址
            timeout: SNMP 逾時時間（秒）
            
        Returns:
            {interface_name: (ifIndex, in_octets, out_octets)}
        """
        interfaces = {}
        
        # OID 定義
        OID_ifDescr = '1.3.6.1.2.1.2.2.1.2'        # 介面描述
        OID_ifInOctets = '1.3.6.1.2.1.2.2.1.10'    # 入流量
        OID_ifOutOctets = '1.3.6.1.2.1.2.2.1.16'   # 出流量
        
        try:
            # 取得介面描述（ifDescr）
            ifDescr_map = {}
            for (errorIndication, errorStatus, errorIndex, varBinds) in nextCmd(
                SnmpEngine(),
                CommunityData(self.community),
                UdpTransportTarget((bras_ip, 161), timeout=timeout, retries=2),
                ContextData(),
                ObjectType(ObjectIdentity(OID_ifDescr)),
                lexicographicMode=False
            ):
                if errorIndication or errorStatus:
                    break
                
                for varBind in varBinds:
                    oid, value = varBind
                    ifIndex = int(oid.prettyPrint().split('.')[-1])
                    ifDescr = str(value)
                    ifDescr_map[ifIndex] = ifDescr
            
            # 取得入流量（ifInOctets）
            ifInOctets_map = {}
            for (errorIndication, errorStatus, errorIndex, varBinds) in nextCmd(
                SnmpEngine(),
                CommunityData(self.community),
                UdpTransportTarget((bras_ip, 161), timeout=timeout, retries=2),
                ContextData(),
                ObjectType(ObjectIdentity(OID_ifInOctets)),
                lexicographicMode=False
            ):
                if errorIndication or errorStatus:
                    break
                
                for varBind in varBinds:
                    oid, value = varBind
                    ifIndex = int(oid.prettyPrint().split('.')[-1])
                    ifInOctets_map[ifIndex] = int(value)
            
            # 取得出流量（ifOutOctets）
            ifOutOctets_map = {}
            for (errorIndication, errorStatus, errorIndex, varBinds) in nextCmd(
                SnmpEngine(),
                CommunityData(self.community),
                UdpTransportTarget((bras_ip, 161), timeout=timeout, retries=2),
                ContextData(),
                ObjectType(ObjectIdentity(OID_ifOutOctets)),
                lexicographicMode=False
            ):
                if errorIndication or errorStatus:
                    break
                
                for varBind in varBinds:
                    oid, value = varBind
                    ifIndex = int(oid.prettyPrint().split('.')[-1])
                    ifOutOctets_map[ifIndex] = int(value)
            
            # 組合結果
            for ifIndex in ifDescr_map.keys():
                interface_name = ifDescr_map.get(ifIndex, '')
                in_octets = ifInOctets_map.get(ifIndex, 0)
                out_octets = ifOutOctets_map.get(ifIndex, 0)
                
                # 只保留有 VLAN 的介面（包含 '.' 的介面）
                if '.' in interface_name:
                    interfaces[interface_name] = (ifIndex, in_octets, out_octets)
            
        except Exception as e:
            print(f"SNMP Walk {bras_ip} 失敗: {e}")
        
        return interfaces
    
    def collect_bras_data(self, bras_ip, device_type):
        """
        收集單一 BRAS 的資料
        
        Args:
            bras_ip: BRAS IP 位址
            device_type: 設備類型（用於決定 timeout）
            
        Returns:
            收集到的介面資料
        """
        # E320 使用較長的 timeout
        timeout = 10 if device_type == DEVICE_TYPE_E320 else 3
        
        print(f"收集 {bras_ip} 資料（設備類型: {device_type}, timeout: {timeout}s）...")
        start_time = time.time()
        
        interfaces = self.snmp_walk_interfaces(bras_ip, timeout=timeout)
        
        elapsed = time.time() - start_time
        print(f"  完成 {bras_ip}，收集 {len(interfaces)} 個介面，耗時 {elapsed:.2f}s")
        
        return bras_ip, interfaces
    
    def collect_all_data(self, max_workers=5):
        """
        並行收集所有 BRAS 的資料
        
        Args:
            max_workers: 最大並行執行緒數
        """
        print("=" * 60)
        print("開始收集所有 BRAS 資料")
        print("=" * 60)
        
        # 取得設備分組
        device_groups = self.map_reader.get_device_groups()
        
        # 建立收集任務列表
        tasks = []
        for device_type, bras_ips in device_groups.items():
            for bras_ip in bras_ips:
                tasks.append((bras_ip, device_type))
        
        # 依優先序排序（新設備優先）
        # E320 是 3，MX 是 1，ACX 是 2
        tasks.sort(key=lambda x: x[1])
        
        # 並行收集
        total_start = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.collect_bras_data, bras_ip, device_type): (bras_ip, device_type)
                for bras_ip, device_type in tasks
            }
            
            for future in as_completed(futures):
                bras_ip, interfaces = future.result()
                self.traffic_data[bras_ip] = interfaces
        
        total_elapsed = time.time() - total_start
        total_interfaces = sum(len(interfaces) for interfaces in self.traffic_data.values())
        
        print("=" * 60)
        print(f"收集完成！")
        print(f"總 BRAS 數量: {len(self.traffic_data)}")
        print(f"總介面數量: {total_interfaces}")
        print(f"總耗時: {total_elapsed:.2f}s")
        print("=" * 60)
    
    def build_interface_mapping(self):
        """
        建立介面對應表
        {bras_ip: {vlan: interface_name}}
        """
        print("建立介面對應表...")
        
        for bras_ip, interfaces in self.traffic_data.items():
            if bras_ip not in self.interface_mapping:
                self.interface_mapping[bras_ip] = {}
            
            for interface_name in interfaces.keys():
                # 解析 VLAN
                if '.' in interface_name:
                    vlan = int(interface_name.split('.')[-1])
                    self.interface_mapping[bras_ip][vlan] = interface_name
        
        total_mappings = sum(len(m) for m in self.interface_mapping.values())
        print(f"建立 {total_mappings} 筆介面對應")
    
    def generate_output_data(self, user_map):
        """
        產生輸出資料（相容於現有 RRD 格式）
        
        Args:
            user_map: 使用者對應表 {user_code: {...}}
            
        Returns:
            輸出資料列表
        """
        print("產生輸出資料...")
        output_data = []
        
        for user_code, user_info in user_map.items():
            bras_ip = user_info['bras_ip']
            vlan = user_info.get('vci', 0)  # 使用 VCI 作為 VLAN（根據實際情況調整）
            
            # 查找對應的介面
            if bras_ip in self.interface_mapping:
                if vlan in self.interface_mapping[bras_ip]:
                    interface_name = self.interface_mapping[bras_ip][vlan]
                    
                    if interface_name in self.traffic_data[bras_ip]:
                        ifIndex, in_octets, out_octets = self.traffic_data[bras_ip][interface_name]
                        
                        output_data.append({
                            'user_code': user_code,
                            'bras_ip': bras_ip,
                            'interface': interface_name,
                            'vlan': vlan,
                            'download': user_info['download'],
                            'upload': user_info['upload'],
                            'in_octets': in_octets,
                            'out_octets': out_octets,
                            'timestamp': datetime.now()
                        })
        
        print(f"產生 {len(output_data)} 筆輸出資料")
        return output_data
    
    def save_to_file(self, output_data, filename="traffic_data.txt"):
        """
        儲存資料到檔案
        格式：user_code,bras_ip,interface,vlan,download,upload,in_octets,out_octets,timestamp
        """
        print(f"儲存資料到 {filename}...")
        
        with open(filename, 'w', encoding='utf-8') as f:
            # 寫入標頭
            f.write("user_code,bras_ip,interface,vlan,download_upload,in_octets,out_octets,timestamp\n")
            
            # 寫入資料
            for data in output_data:
                # 組合下載上傳速率（使用底線分隔，符合正式環境格式）
                download_upload = f"{data['download']}_{data['upload']}"
                
                line = f"{data['user_code']},{data['bras_ip']},{data['interface']}," \
                       f"{data['vlan']},{download_upload},{data['in_octets']}," \
                       f"{data['out_octets']},{data['timestamp']}\n"
                f.write(line)
        
        print(f"儲存完成，共 {len(output_data)} 筆資料")


def main():
    """主程式"""
    print("=" * 60)
    print("RRDW Data Collector with BRAS Map Integration")
    print("=" * 60)
    print()
    
    # 初始化收集器
    collector = BRASMapCollector(
        map_file="BRAS-Map.txt",
        db_config=None  # 若要使用資料庫，請設定 db_config
    )
    
    # 載入 BRAS Map
    collector.load_bras_map()
    
    # 載入使用者對應表（從資料庫或其他來源）
    # user_map = collector.load_user_map_from_db()
    # 測試用：建立假資料
    user_map = {
        'user001': {
            'bras_ip': '61.64.214.54',
            'slot': 1,
            'port': 0,
            'vpi': 0,
            'vci': 400,
            'download': 61440,
            'upload': 20480
        },
        'user002': {
            'bras_ip': '61.64.214.54',
            'slot': 1,
            'port': 0,
            'vpi': 0,
            'vci': 401,
            'download': 102400,
            'upload': 20480
        }
    }
    
    # 收集所有 BRAS 資料
    collector.collect_all_data(max_workers=5)
    
    # 建立介面對應表
    collector.build_interface_mapping()
    
    # 產生輸出資料
    output_data = collector.generate_output_data(user_map)
    
    # 儲存到檔案
    collector.save_to_file(output_data, "traffic_data.txt")
    
    print()
    print("處理完成！")


if __name__ == "__main__":
    main()
