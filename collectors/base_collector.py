#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base Collector - 統一的收集器基類
提供所有設備收集器共用的功能
"""

import os
import time
import rrdtool
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Set
from dataclasses import dataclass


@dataclass
class UserTraffic:
    """使用者流量資料"""
    user_code: str
    interface_index: int
    slot: int
    port: int
    vlan: int
    download_kbps: int
    upload_kbps: int
    out_octets: int  # SNMP counter
    
    @property
    def speed_key(self) -> str:
        """速率鍵值"""
        return f"{self.download_kbps}_{self.upload_kbps}"
    
    @property
    def rate_bps(self) -> int:
        """當前速率 (bps)"""
        return self.out_octets * 8


class BaseCollector(ABC):
    """收集器基類"""
    
    def __init__(self, rrd_base_dir: str, config: Dict = None):
        """
        初始化收集器
        
        Args:
            rrd_base_dir: RRD 基礎目錄
            config: 設定字典
        """
        self.rrd_base_dir = rrd_base_dir
        self.config = config or {}
        
        # RRD 目錄
        self.rrd_sum_dir = os.path.join(rrd_base_dir, 'sum')
        self.rrd_sum2m_dir = os.path.join(rrd_base_dir, 'sum2m')
        self.rrd_circuit_dir = os.path.join(rrd_base_dir, 'circuit')
        
        # RRD 參數
        self.rrd_step = self.config.get('rrd_step', 1200)  # 20 分鐘
        
        # Fair Usage Policy
        self.fair_usage_policies = self.config.get('fair_usage_policies', {
            '3072_640': 3072000,
            '4096_1024': 2800000,
            'default': 2048000
        })
    
    @abstractmethod
    def load_users(self, device_ip: str, slot: int, port: int) -> List[UserTraffic]:
        """
        載入使用者列表（各設備實作）
        
        Args:
            device_ip: 設備 IP
            slot: 插槽
            port: 埠號
            
        Returns:
            UserTraffic 列表
        """
        pass
    
    @abstractmethod
    def snmp_collect(self, device_ip: str, users: List[UserTraffic]) -> Dict[int, int]:
        """
        SNMP 收集（各設備實作）
        
        Args:
            device_ip: 設備 IP
            users: 使用者列表
            
        Returns:
            {ifindex: out_octets}
        """
        pass
    
    def get_user_rrd_path(self, device_ip: str, slot: int, port: int, 
                         download_kbps: int, upload_kbps: int, vlan: int) -> str:
        """
        取得使用者 RRD 路徑
        格式: {IP}/{IP}_{slot}_{port}_{download}_{upload}_{vlan}.rrd
        """
        filename = f"{device_ip}_{slot}_{port}_{download_kbps}_{upload_kbps}_{vlan}.rrd"
        return os.path.join(self.rrd_base_dir, device_ip, filename)
    
    def get_sum_rrd_path(self, base_dir: str, device_ip: str, slot: int, port: int,
                        download_kbps: int, upload_kbps: int) -> str:
        """
        取得彙總 RRD 路徑
        格式: {base_dir}/{IP}/{IP}_{slot}_{port}_{download}_{upload}_sum.rrd
        """
        filename = f"{device_ip}_{slot}_{port}_{download_kbps}_{upload_kbps}_sum.rrd"
        return os.path.join(base_dir, device_ip, filename)
    
    def get_circuit_rrd_path(self, device_ip: str, interface: str) -> str:
        """
        取得 Circuit RRD 路徑
        格式: circuit/{IP}/{IP}_{interface}_circuit.rrd
        
        Args:
            device_ip: 設備 IP
            interface: 介面名稱 (ge-1-2 或 xe-1-0-0)
        """
        # 介面名稱中的斜線改為短橫線
        safe_interface = interface.replace('/', '-')
        filename = f"{device_ip}_{safe_interface}_circuit.rrd"
        return os.path.join(self.rrd_circuit_dir, device_ip, filename)
    
    def create_user_rrd(self, rrd_path: str, download_kbps: int, upload_kbps: int) -> bool:
        """建立使用者 RRD (COUNTER 類型)"""
        if os.path.exists(rrd_path):
            return True
        
        os.makedirs(os.path.dirname(rrd_path), exist_ok=True)
        
        ds_name = f"{download_kbps}_{upload_kbps}"
        max_ds = download_kbps * 1024 + 10240
        
        try:
            rrdtool.create(
                rrd_path,
                '--step', str(self.rrd_step),
                '--start', str(int(time.time()) - self.rrd_step),
                f'DS:{ds_name}:COUNTER:{self.rrd_step * 2}:0:{max_ds}',
                'RRA:AVERAGE:0.5:1:4465',
                'RRA:AVERAGE:0.5:24:564',
                'RRA:AVERAGE:0.5:144:1096',
                'RRA:MAX:0.5:1:4465',
                'RRA:MAX:0.5:24:564',
                'RRA:MAX:0.5:144:1096'
            )
            logging.debug(f"建立 User RRD: {rrd_path}")
            return True
        except Exception as e:
            logging.error(f"建立 RRD 失敗: {e}")
            return False
    
    def create_sum_rrd(self, rrd_path: str, speed_key: str) -> bool:
        """建立彙總 RRD (GAUGE 類型)"""
        if os.path.exists(rrd_path):
            return True
        
        os.makedirs(os.path.dirname(rrd_path), exist_ok=True)
        
        try:
            rrdtool.create(
                rrd_path,
                '--step', str(self.rrd_step),
                '--start', str(int(time.time()) - self.rrd_step),
                f'DS:{speed_key}:GAUGE:600:0:U',
                'RRA:AVERAGE:0.5:1:4465',
                'RRA:AVERAGE:0.5:24:564',
                'RRA:AVERAGE:0.5:144:1096',
                'RRA:MAX:0.5:1:4465',
                'RRA:MAX:0.5:24:564',
                'RRA:MAX:0.5:144:1096'
            )
            logging.debug(f"建立 Sum RRD: {rrd_path}")
            return True
        except Exception as e:
            logging.error(f"建立 Sum RRD 失敗: {e}")
            return False
    
    def create_circuit_rrd(self, rrd_path: str) -> bool:
        """建立 Circuit RRD (GAUGE 類型，多個 DS)"""
        if os.path.exists(rrd_path):
            return True
        
        os.makedirs(os.path.dirname(rrd_path), exist_ok=True)
        
        try:
            rrdtool.create(
                rrd_path,
                '--step', str(self.rrd_step),
                '--start', str(int(time.time()) - self.rrd_step),
                # DS 1: 總流量 (bps)
                'DS:total_traffic:GAUGE:600:0:U',
                # DS 2: VLAN 數量
                'DS:vlan_count:GAUGE:600:0:U',
                # DS 3: 使用者數量
                'DS:user_count:GAUGE:600:0:U',
                # DS 4: 尖峰速率 (bps)
                'DS:peak_rate:GAUGE:600:0:U',
                # DS 5: 平均速率 (bps)
                'DS:avg_rate:GAUGE:600:0:U',
                # RRA
                'RRA:AVERAGE:0.5:1:4465',
                'RRA:AVERAGE:0.5:24:564',
                'RRA:AVERAGE:0.5:144:1096',
                'RRA:MAX:0.5:1:4465',
                'RRA:MAX:0.5:24:564',
                'RRA:MAX:0.5:144:1096'
            )
            logging.info(f"建立 Circuit RRD: {rrd_path}")
            return True
        except Exception as e:
            logging.error(f"建立 Circuit RRD 失敗: {e}")
            return False
    
    def update_rrd(self, rrd_path: str, timestamp: int, value: int) -> bool:
        """更新 RRD"""
        try:
            rrdtool.update(rrd_path, f"{timestamp}:{int(value)}")
            return True
        except Exception as e:
            if 'illegal attempt to update' not in str(e):
                logging.error(f"RRD 更新失敗 {rrd_path}: {e}")
            return False
    
    def read_rrd_rate(self, rrd_path: str, timestamp: int) -> int:
        """從 RRD 讀取速率"""
        try:
            start_time = timestamp - 5
            end_time = timestamp + self.rrd_step
            
            result = rrdtool.fetch(
                rrd_path,
                'AVERAGE',
                '--start', str(start_time),
                '--end', str(end_time)
            )
            
            (fetch_start, fetch_end, fetch_step), ds_names, data = result
            
            for row in reversed(data):
                if row[0] is not None:
                    return int(row[0] + 0.9)
            
            return 0
        except Exception as e:
            logging.debug(f"讀取 RRD 失敗 {rrd_path}: {e}")
            return 0
    
    def apply_fair_usage_policy(self, bits: int, speed_key: str) -> tuple[int, bool]:
        """
        套用 Fair Usage Policy
        
        Returns:
            (限制後的流量, 是否超標)
        """
        if bits < 2048000:  # 小於 2Mbps 不限制
            return bits, False
        
        limit = self.fair_usage_policies.get(speed_key, 
                                             self.fair_usage_policies['default'])
        
        if bits >= limit:
            return limit, True
        
        return bits, False
    
    def collect_device(self, device_ip: str, device_name: str, 
                      slot: int, port: int) -> Dict:
        """
        主收集流程（統一介面）
        
        Args:
            device_ip: 設備 IP
            device_name: 設備名稱
            slot: 插槽
            port: 埠號
            
        Returns:
            收集結果字典
        """
        logging.info(f"=" * 70)
        logging.info(f"收集: {device_name} ({device_ip}) Slot {slot} Port {port}")
        logging.info(f"=" * 70)
        
        start_time = time.time()
        
        try:
            # Step 1: 載入使用者列表
            users = self.load_users(device_ip, slot, port)
            if not users:
                return {
                    'status': 'skipped',
                    'message': '未找到使用者',
                    'elapsed': time.time() - start_time
                }
            
            logging.info(f"載入 {len(users)} 個使用者")
            
            # Step 2: SNMP 收集
            traffic_data = self.snmp_collect(device_ip, users)
            if not traffic_data:
                return {
                    'status': 'failed',
                    'message': 'SNMP 收集失敗',
                    'elapsed': time.time() - start_time
                }
            
            logging.info(f"收集 {len(traffic_data)} 個介面資料")
            
            # Step 3: 更新使用者流量
            for user in users:
                if user.interface_index in traffic_data:
                    user.out_octets = traffic_data[user.interface_index]
            
            # Step 4: 寫入 Layer 1 (User RRD)
            self.write_user_rrd(device_ip, users)
            
            # Step 5: 寫入 Layer 2/3 (Sum/Sum2M RRD)
            self.write_sum_rrd(device_ip, slot, port, users)
            
            # Step 6: 寫入 Layer 4 (Circuit RRD)
            interface = self.get_interface_name(slot, port)
            self.write_circuit_rrd(device_ip, interface, users)
            
            return {
                'status': 'success',
                'message': f'成功收集 {len(users)} 個使用者',
                'user_count': len(users),
                'elapsed': time.time() - start_time
            }
            
        except Exception as e:
            logging.error(f"收集失敗: {e}", exc_info=True)
            return {
                'status': 'failed',
                'message': str(e),
                'elapsed': time.time() - start_time
            }
    
    def write_user_rrd(self, device_ip: str, users: List[UserTraffic]) -> None:
        """寫入 Layer 1: 使用者 RRD"""
        timestamp = int(time.time())
        timestamp = timestamp - (timestamp % self.rrd_step)
        
        for user in users:
            if user.out_octets == 0:
                continue
            
            rrd_path = self.get_user_rrd_path(
                device_ip, user.slot, user.port,
                user.download_kbps, user.upload_kbps, user.vlan
            )
            
            self.create_user_rrd(rrd_path, user.download_kbps, user.upload_kbps)
            
            out_bits = user.out_octets * 8
            self.update_rrd(rrd_path, timestamp, out_bits)
    
    def write_sum_rrd(self, device_ip: str, slot: int, port: int,
                     users: List[UserTraffic]) -> None:
        """寫入 Layer 2/3: Sum/Sum2M RRD"""
        timestamp = int(time.time())
        timestamp = timestamp - (timestamp % self.rrd_step)
        
        # 依速率分組
        speed_groups: Dict[str, List[UserTraffic]] = {}
        for user in users:
            if user.out_octets == 0:
                continue
            
            if user.speed_key not in speed_groups:
                speed_groups[user.speed_key] = []
            speed_groups[user.speed_key].append(user)
        
        # 為每個速率方案寫入 Sum RRD
        for speed_key, group_users in speed_groups.items():
            download, upload = map(int, speed_key.split('_'))
            
            # 計算總速率
            total_rate = 0
            total_rate_2m = 0
            
            for user in group_users:
                # 從使用者 RRD 讀取速率
                user_rrd = self.get_user_rrd_path(
                    device_ip, user.slot, user.port,
                    user.download_kbps, user.upload_kbps, user.vlan
                )
                rate = self.read_rrd_rate(user_rrd, timestamp)
                
                if rate > 0:
                    total_rate += rate
                    
                    # 套用 Fair Usage
                    limited_rate, _ = self.apply_fair_usage_policy(rate, speed_key)
                    total_rate_2m += limited_rate
            
            # Sum RRD (無限制)
            sum_rrd = self.get_sum_rrd_path(
                self.rrd_sum_dir, device_ip, slot, port, download, upload
            )
            self.create_sum_rrd(sum_rrd, speed_key)
            self.update_rrd(sum_rrd, timestamp, total_rate)
            
            # Sum2M RRD (Fair Usage)
            sum2m_rrd = self.get_sum_rrd_path(
                self.rrd_sum2m_dir, device_ip, slot, port, download, upload
            )
            self.create_sum_rrd(sum2m_rrd, speed_key)
            self.update_rrd(sum2m_rrd, timestamp, total_rate_2m)
            
            logging.info(
                f"  {speed_key}: {len(group_users)} 用戶, "
                f"{total_rate/1000000:.2f} Mbps "
                f"(2M限制: {total_rate_2m/1000000:.2f} Mbps)"
            )
    
    def write_circuit_rrd(self, device_ip: str, interface: str,
                         users: List[UserTraffic]) -> None:
        """寫入 Layer 4: Circuit RRD"""
        timestamp = int(time.time())
        timestamp = timestamp - (timestamp % self.rrd_step)
        
        # 計算 Circuit 統計
        active_users = [u for u in users if u.out_octets > 0]
        
        if not active_users:
            return
        
        # 總流量
        total_traffic = sum(user.rate_bps for user in active_users)
        
        # VLAN 數量
        vlan_count = len(set(user.vlan for user in active_users))
        
        # 使用者數量
        user_count = len(active_users)
        
        # 尖峰速率
        peak_rate = max(user.rate_bps for user in active_users)
        
        # 平均速率
        avg_rate = total_traffic // user_count if user_count > 0 else 0
        
        # Circuit RRD
        circuit_rrd = self.get_circuit_rrd_path(device_ip, interface)
        self.create_circuit_rrd(circuit_rrd)
        
        # 更新（多個 DS）
        try:
            rrdtool.update(circuit_rrd,
                f"{timestamp}:{total_traffic}:{vlan_count}:{user_count}:{peak_rate}:{avg_rate}")
            
            logging.info(
                f"Circuit {interface}: {total_traffic/1000000:.2f} Mbps, "
                f"{vlan_count} VLANs, {user_count} users"
            )
        except Exception as e:
            if 'illegal attempt to update' not in str(e):
                logging.error(f"Circuit RRD 更新失敗: {e}")
    
    @abstractmethod
    def get_interface_name(self, slot: int, port: int) -> str:
        """
        取得介面名稱（各設備實作）
        
        Args:
            slot: 插槽
            port: 埠號
            
        Returns:
            介面名稱 (如: ge-1-2 或 xe-1-0-0)
        """
        pass
