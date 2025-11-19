#!/usr/bin/env python3
"""
base_collector.py - 收集器基類

提供所有收集器的共用功能
"""

import os
import sys
import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# 添加 core 模組到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.config_loader import ConfigLoader
from core.snmp_helper import SNMPHelper
from core.rrd_manager import RRDManager

logger = logging.getLogger(__name__)


@dataclass
class UserData:
    """用戶資料結構"""
    username: str
    slot: int
    port: int
    vpi: int
    vci: int
    download: int  # bps
    upload: int    # bps
    account: str
    interface_name: str = None
    if_index: int = None


@dataclass
class CollectionStats:
    """收集統計"""
    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    start_time: float = 0
    end_time: float = 0
    
    @property
    def duration(self) -> float:
        """收集耗時（秒）"""
        if self.end_time > 0:
            return self.end_time - self.start_time
        return 0
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total > 0:
            return (self.success / self.total) * 100
        return 0


class BaseCollector:
    """收集器基類"""
    
    def __init__(self, device_ip: str, device_type: int, map_file: str,
                 config: ConfigLoader = None):
        """
        初始化收集器
        
        Args:
            device_ip: 設備 IP
            device_type: 設備類型 (1=E320, 2=MX960, 3=MX240, 4=ACX7024)
            map_file: Map 檔案路徑
            config: 配置載入器，None 則自動建立
        """
        self.device_ip = device_ip
        self.device_type = device_type
        self.map_file = map_file
        
        # 載入配置
        self.config = config if config else ConfigLoader()
        
        # 初始化 SNMP Helper
        timeout = self.config.get_device_timeout(device_type)
        retries = self.config.get_device_retries(device_type)
        self.snmp = SNMPHelper(
            device_ip,
            self.config.snmp_community,
            timeout,
            retries
        )
        
        # 初始化 RRD Manager
        self.rrd = RRDManager(
            self.config.rrd_base_dir,
            self.config.rrd_step,
            self.config.rrd_heartbeat
        )
        
        # 用戶資料
        self.users: List[UserData] = []
        
        # 統計資訊
        self.stats = CollectionStats()
        
        # 設備名稱
        self.device_names = {
            1: 'MX240',
            2: 'MX960',
            3: 'E320',
            4: 'ACX7024'
        }
        
        logger.info(f"收集器初始化: {self.device_name} - {device_ip}")
    
    @property
    def device_name(self) -> str:
        """設備名稱"""
        return self.device_names.get(self.device_type, f'Unknown({self.device_type})')
    
    def build_interface_name(self, user: UserData) -> str:
        """
        建立 Junos 介面名稱
        
        Args:
            user: 用戶資料
        
        Returns:
            介面名稱
        
        Note:
            子類別應覆寫此方法以提供設備專用的介面格式
            - DeviceType 1 (MX240): ge-fpc/pic/port:vci
            - DeviceType 2 (MX960): ge-fpc/pic/port:vci
            - DeviceType 3 (E320): ge-slot/port/pic.vci
            - DeviceType 4 (ACX7024): ge-fpc/pic/port:vci
        """
        raise NotImplementedError("子類別必須實作 build_interface_name 方法")
    
    def parse_map_file(self) -> bool:
        """
        解析 Map 檔案
        
        Returns:
            是否成功
        """
        if not os.path.exists(self.map_file):
            logger.error(f"Map 檔案不存在: {self.map_file}")
            return False
        
        logger.info(f"讀取 Map 檔案: {self.map_file}")
        
        with open(self.map_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # 跳過空行和註解
                if not line or line.startswith('#'):
                    continue
                
                try:
                    parts = line.split(',')
                    if len(parts) != 4:
                        logger.warning(f"第 {line_num} 行格式錯誤: {line}")
                        continue
                    
                    username, interface, bandwidth, account = [p.strip() for p in parts]
                    
                    # 解析介面
                    iface_parts = interface.split('_')
                    if len(iface_parts) != 4:
                        logger.warning(f"第 {line_num} 行介面格式錯誤: {interface}")
                        continue
                    
                    slot, port, vpi, vci = [int(x) for x in iface_parts]
                    
                    # 解析頻寬
                    bw_parts = bandwidth.split('_')
                    if len(bw_parts) != 2:
                        logger.warning(f"第 {line_num} 行頻寬格式錯誤: {bandwidth}")
                        continue
                    
                    download, upload = [int(x) for x in bw_parts]
                    
                    # 建立用戶資料
                    user = UserData(
                        username=username,
                        slot=slot,
                        port=port,
                        vpi=vpi,
                        vci=vci,
                        download=download,
                        upload=upload,
                        account=account
                    )
                    
                    # 建立介面名稱
                    user.interface_name = self.build_interface_name(user)
                    
                    self.users.append(user)
                    
                except Exception as e:
                    logger.warning(f"第 {line_num} 行解析失敗: {e}")
                    continue
        
        logger.info(f"載入 {len(self.users)} 筆用戶資料")
        return len(self.users) > 0
    
    def test_connectivity(self) -> bool:
        """
        測試 SNMP 連線
        
        Returns:
            是否成功
        """
        return self.snmp.test_connectivity()
    
    def collect_user_traffic(self, user: UserData) -> bool:
        """
        收集單一用戶流量
        
        Args:
            user: 用戶資料
        
        Returns:
            是否成功
        """
        try:
            # 取得流量計數器
            counters = self.snmp.get_interface_counters(user.interface_name)
            if counters is None:
                logger.debug(f"無法取得用戶 {user.username} 的計數器")
                return False
            
            inbound, outbound = counters
            
            # 更新用戶 RRD
            if self.rrd.update_user_rrd(user.username, inbound, outbound):
                return True
            else:
                logger.warning(f"更新用戶 {user.username} RRD 失敗")
                return False
            
        except Exception as e:
            logger.error(f"收集用戶 {user.username} 失敗: {e}")
            return False
    
    def collect_all_users(self) -> CollectionStats:
        """
        收集所有用戶流量
        
        Returns:
            收集統計
        """
        self.stats = CollectionStats()
        self.stats.total = len(self.users)
        self.stats.start_time = time.time()
        
        logger.info(f"開始收集 {self.stats.total} 個用戶")
        
        for user in self.users:
            if self.collect_user_traffic(user):
                self.stats.success += 1
            else:
                self.stats.failed += 1
        
        self.stats.end_time = time.time()
        
        logger.info(
            f"收集完成: 成功={self.stats.success}, 失敗={self.stats.failed}, "
            f"耗時={self.stats.duration:.1f}秒, 成功率={self.stats.success_rate:.1f}%"
        )
        
        return self.stats
    
    def run(self) -> bool:
        """
        執行完整收集流程
        
        Returns:
            是否成功
        """
        try:
            # 1. 測試連線
            logger.info(f"測試 SNMP 連線: {self.device_ip}")
            if not self.test_connectivity():
                logger.error("SNMP 連線失敗")
                return False
            
            # 2. 解析 Map 檔案
            if not self.parse_map_file():
                logger.error("Map 檔案解析失敗")
                return False
            
            # 3. 收集流量
            stats = self.collect_all_users()
            
            # 4. 判斷是否成功
            if stats.success_rate >= 80:  # 80% 以上視為成功
                logger.info(f"收集成功 (成功率: {stats.success_rate:.1f}%)")
                return True
            else:
                logger.warning(f"收集成功率過低: {stats.success_rate:.1f}%")
                return False
            
        except Exception as e:
            logger.error(f"收集流程失敗: {e}", exc_info=True)
            return False


# 測試程式
if __name__ == '__main__':
    print("這是基類，請使用具體的收集器實作")
    print("例如: collector_e320.py, collector_mx960.py")
