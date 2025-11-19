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
        收集所有用戶流量（使用 snmpwalk 批次查詢優化版）
        
        Returns:
            收集統計
        """
        self.stats = CollectionStats()
        self.stats.total = len(self.users)
        self.stats.start_time = time.time()
        
        logger.info(f"開始收集 {self.stats.total} 個用戶")
        
        # 使用批次 snmpwalk 收集
        if self.config.use_snmpwalk_batch:
            logger.info("使用 snmpwalk 批次收集模式")
            success_count = self._collect_batch_snmpwalk()
            self.stats.success = success_count
            self.stats.failed = self.stats.total - success_count
        else:
            # 逐個收集（原始方式）
            logger.info("使用逐個收集模式")
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
    
    def _collect_batch_snmpwalk(self) -> int:
        """
        使用 snmpwalk 批次收集所有用戶（內部方法）
        
        Returns:
            成功收集的用戶數
        """
        # 建立介面索引映射
        # 對於沒有 ifindex 的用戶，需要先查詢介面清單建立映射
        users_need_ifindex = [u for u in self.users if u.if_index is None]
        users_have_ifindex = [u for u in self.users if u.if_index is not None]
        
        # 如果有用戶需要查詢 ifindex，先建立介面映射
        if_name_to_index = {}
        if users_need_ifindex:
            logger.info(f"{len(users_need_ifindex)} 個用戶需要查詢 ifindex")
            
            # 取得所有介面
            interfaces = self.snmp.get_interface_descriptions(use_cache=True)
            
            # 建立名稱到索引的映射
            for if_index, if_descr in interfaces.items():
                if_name_to_index[if_descr] = if_index
            
            # 為用戶填入 ifindex
            for user in users_need_ifindex:
                if user.interface_name in if_name_to_index:
                    user.if_index = if_name_to_index[user.interface_name]
                else:
                    logger.warning(f"找不到介面 {user.interface_name} 的索引")
        
        # 收集所有需要的 ifindex
        required_indexes = set()
        for user in self.users:
            if user.if_index:
                required_indexes.add(str(user.if_index))
        
        if not required_indexes:
            logger.error("沒有有效的 ifindex，無法收集")
            return 0
        
        logger.info(f"使用 snmpwalk 查詢 {len(required_indexes)} 個介面")
        
        # 執行 snmpwalk 批次查詢
        # 查詢出站流量 (ifHCOutOctets)
        out_octets_results = self.snmp.snmpwalk_cli(
            self.snmp.OID_IF_HC_OUT_OCTETS,
            required_indexes
        )
        
        # 查詢入站流量 (ifHCInOctets)
        in_octets_results = self.snmp.snmpwalk_cli(
            self.snmp.OID_IF_HC_IN_OCTETS,
            required_indexes
        )
        
        if not out_octets_results and not in_octets_results:
            logger.error("snmpwalk 查詢失敗")
            return 0
        
        logger.info(
            f"取得 {len(out_octets_results)} 個出站計數器, "
            f"{len(in_octets_results)} 個入站計數器"
        )
        
        # 更新每個用戶的 RRD
        success_count = 0
        for user in self.users:
            if not user.if_index:
                continue
            
            ifindex_str = str(user.if_index)
            
            # 取得計數器值
            outbound = out_octets_results.get(ifindex_str, 0)
            inbound = in_octets_results.get(ifindex_str, 0)
            
            if outbound == 0 and inbound == 0:
                logger.debug(f"用戶 {user.username} (ifindex={ifindex_str}) 無流量資料")
                continue
            
            # 更新 RRD
            if self.rrd.update_user_rrd(user.username, inbound, outbound):
                success_count += 1
            else:
                logger.warning(f"更新用戶 {user.username} RRD 失敗")
        
        return success_count
    
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
