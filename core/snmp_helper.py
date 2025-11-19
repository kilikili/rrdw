#!/usr/bin/env python3
"""
snmp_helper.py - SNMP 輔助工具

提供 SNMP 查詢和 Bulk Walking 功能
"""

import time
import logging
from typing import Dict, Optional, List, Tuple
from pysnmp.hlapi import *

logger = logging.getLogger(__name__)


class SNMPHelper:
    """SNMP 輔助工具類別"""
    
    # 常用 OID
    OID_SYSTEM_DESC = '1.3.6.1.2.1.1.1.0'
    OID_IF_DESCR = '1.3.6.1.2.1.2.2.1.2'
    OID_IF_TYPE = '1.3.6.1.2.1.2.2.1.3'
    OID_IF_SPEED = '1.3.6.1.2.1.2.2.1.5'
    OID_IF_HC_IN_OCTETS = '1.3.6.1.2.1.31.1.1.1.6'
    OID_IF_HC_OUT_OCTETS = '1.3.6.1.2.1.31.1.1.1.10'
    
    def __init__(self, device_ip: str, community: str = 'public',
                 timeout: int = 5, retries: int = 2):
        """
        初始化 SNMP Helper
        
        Args:
            device_ip: 設備 IP
            community: SNMP Community
            timeout: 超時時間（秒）
            retries: 重試次數
        """
        self.device_ip = device_ip
        self.community = community
        self.timeout = timeout
        self.retries = retries
        
        # 介面快取
        self._interface_cache = {}
        self._cache_timestamp = 0
        self._cache_ttl = 3600  # 快取 1 小時
        
        logger.debug(f"SNMP Helper 初始化: {device_ip} (timeout={timeout}s, retries={retries})")
    
    def get(self, oid: str, max_retries: int = None) -> Optional[any]:
        """
        執行 SNMP GET 查詢
        
        Args:
            oid: OID 字串
            max_retries: 最大重試次數，None 則使用預設值
        
        Returns:
            查詢結果，失敗則返回 None
        """
        if max_retries is None:
            max_retries = self.retries
        
        for attempt in range(max_retries + 1):
            try:
                errorIndication, errorStatus, errorIndex, varBinds = next(
                    getCmd(
                        SnmpEngine(),
                        CommunityData(self.community, mpModel=1),  # SNMPv2c
                        UdpTransportTarget((self.device_ip, 161), 
                                         timeout=self.timeout, 
                                         retries=0),  # 自己處理重試
                        ContextData(),
                        ObjectType(ObjectIdentity(oid))
                    )
                )
                
                if errorIndication:
                    if attempt < max_retries:
                        logger.debug(f"SNMP GET 失敗 (嘗試 {attempt+1}/{max_retries+1}): {errorIndication}")
                        time.sleep(1)
                        continue
                    else:
                        logger.error(f"SNMP GET 失敗: {errorIndication}")
                        return None
                
                if errorStatus:
                    logger.error(f"SNMP Error: {errorStatus.prettyPrint()}")
                    return None
                
                # 成功取得值
                for varBind in varBinds:
                    return varBind[1]
                
            except Exception as e:
                if attempt < max_retries:
                    logger.debug(f"SNMP GET 異常 (嘗試 {attempt+1}/{max_retries+1}): {e}")
                    time.sleep(1)
                    continue
                else:
                    logger.error(f"SNMP GET 異常: {e}")
                    return None
        
        return None
    
    def bulk_walk(self, oid: str, max_repetitions: int = 50) -> Dict[str, any]:
        """
        執行 SNMP Bulk Walk
        
        Args:
            oid: 起始 OID
            max_repetitions: 每次請求的最大重複數
        
        Returns:
            OID -> 值的字典
        """
        results = {}
        
        try:
            for (errorIndication, errorStatus, errorIndex, varBinds) in bulkCmd(
                SnmpEngine(),
                CommunityData(self.community, mpModel=1),
                UdpTransportTarget((self.device_ip, 161), 
                                 timeout=self.timeout, 
                                 retries=self.retries),
                ContextData(),
                0, max_repetitions,  # non-repeaters, max-repetitions
                ObjectType(ObjectIdentity(oid)),
                lexicographicMode=False
            ):
                if errorIndication:
                    logger.error(f"Bulk Walk Error: {errorIndication}")
                    break
                
                if errorStatus:
                    logger.error(f"SNMP Error: {errorStatus.prettyPrint()}")
                    break
                
                for varBind in varBinds:
                    oid_str = str(varBind[0])
                    value = varBind[1]
                    results[oid_str] = value
            
            logger.debug(f"Bulk Walk 完成: {len(results)} 個結果")
            
        except Exception as e:
            logger.error(f"Bulk Walk 失敗: {e}")
        
        return results
    
    def get_system_description(self) -> Optional[str]:
        """
        取得系統描述
        
        Returns:
            系統描述字串
        """
        result = self.get(self.OID_SYSTEM_DESC)
        if result:
            return str(result)
        return None
    
    def get_interface_descriptions(self, use_cache: bool = True) -> Dict[int, str]:
        """
        取得所有介面描述
        
        Args:
            use_cache: 是否使用快取
        
        Returns:
            介面索引 -> 描述的字典
        """
        # 檢查快取
        if use_cache and self._interface_cache:
            if time.time() - self._cache_timestamp < self._cache_ttl:
                logger.debug("使用介面快取")
                return self._interface_cache
        
        # 執行 Bulk Walk
        interfaces = {}
        results = self.bulk_walk(self.OID_IF_DESCR)
        
        for oid_str, value in results.items():
            # 解析介面索引
            # OID 格式: 1.3.6.1.2.1.2.2.1.2.{index}
            parts = oid_str.split('.')
            if len(parts) > 0:
                try:
                    if_index = int(parts[-1])
                    interfaces[if_index] = str(value)
                except (ValueError, IndexError):
                    continue
        
        # 更新快取
        self._interface_cache = interfaces
        self._cache_timestamp = time.time()
        
        logger.info(f"取得 {len(interfaces)} 個介面描述")
        return interfaces
    
    def find_interface_index(self, interface_name: str, use_cache: bool = True) -> Optional[int]:
        """
        根據介面名稱尋找介面索引
        
        Args:
            interface_name: 介面名稱 (例如: ge-1/2/0.3490)
            use_cache: 是否使用快取
        
        Returns:
            介面索引，找不到則返回 None
        """
        interfaces = self.get_interface_descriptions(use_cache)
        
        for if_index, if_descr in interfaces.items():
            if if_descr == interface_name:
                return if_index
        
        logger.warning(f"找不到介面: {interface_name}")
        return None
    
    def get_interface_counters(self, interface_name: str) -> Optional[Tuple[int, int]]:
        """
        取得介面的流量計數器
        
        Args:
            interface_name: 介面名稱
        
        Returns:
            (inbound_octets, outbound_octets) 或 None
        """
        # 尋找介面索引
        if_index = self.find_interface_index(interface_name)
        if if_index is None:
            return None
        
        # 查詢計數器
        in_oid = f"{self.OID_IF_HC_IN_OCTETS}.{if_index}"
        out_oid = f"{self.OID_IF_HC_OUT_OCTETS}.{if_index}"
        
        inbound = self.get(in_oid)
        outbound = self.get(out_oid)
        
        if inbound is None or outbound is None:
            logger.warning(f"無法取得介面 {interface_name} 的計數器")
            return None
        
        try:
            return (int(inbound), int(outbound))
        except (ValueError, TypeError):
            logger.error(f"計數器值轉換失敗: in={inbound}, out={outbound}")
            return None
    
    def get_interface_counters_by_index(self, if_index: int) -> Optional[Tuple[int, int]]:
        """
        根據介面索引取得流量計數器
        
        Args:
            if_index: 介面索引
        
        Returns:
            (inbound_octets, outbound_octets) 或 None
        """
        in_oid = f"{self.OID_IF_HC_IN_OCTETS}.{if_index}"
        out_oid = f"{self.OID_IF_HC_OUT_OCTETS}.{if_index}"
        
        inbound = self.get(in_oid)
        outbound = self.get(out_oid)
        
        if inbound is None or outbound is None:
            return None
        
        try:
            return (int(inbound), int(outbound))
        except (ValueError, TypeError):
            return None
    
    def test_connectivity(self) -> bool:
        """
        測試 SNMP 連線
        
        Returns:
            連線是否成功
        """
        logger.info(f"測試 SNMP 連線: {self.device_ip}")
        
        result = self.get_system_description()
        if result:
            logger.info(f"連線成功: {result[:80]}")
            return True
        else:
            logger.error("連線失敗")
            return False


# 測試程式
if __name__ == '__main__':
    import sys
    
    # 設定日誌
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 從命令列參數取得設備 IP
    if len(sys.argv) < 2:
        print("使用方式: python3 snmp_helper.py <device_ip> [community]")
        print("範例: python3 snmp_helper.py 192.168.1.1 public")
        sys.exit(1)
    
    device_ip = sys.argv[1]
    community = sys.argv[2] if len(sys.argv) > 2 else 'public'
    
    print(f"\n=== SNMP 測試: {device_ip} ===\n")
    
    # 建立 SNMP Helper
    snmp = SNMPHelper(device_ip, community)
    
    # 測試連線
    if not snmp.test_connectivity():
        print("✗ SNMP 連線失敗")
        sys.exit(1)
    
    print("\n=== 介面清單 ===")
    interfaces = snmp.get_interface_descriptions()
    
    # 顯示前 20 個介面
    for if_index, if_descr in list(interfaces.items())[:20]:
        print(f"{if_index:5d}: {if_descr}")
    
    if len(interfaces) > 20:
        print(f"... 還有 {len(interfaces) - 20} 個介面")
    
    # 測試查詢特定介面
    if interfaces:
        test_index = list(interfaces.keys())[0]
        print(f"\n=== 測試查詢介面 {test_index} ===")
        counters = snmp.get_interface_counters_by_index(test_index)
        if counters:
            inbound, outbound = counters
            print(f"入站: {inbound:,} bytes")
            print(f"出站: {outbound:,} bytes")
        else:
            print("無法取得計數器")
    
    print("\n✓ SNMP 測試完成")
