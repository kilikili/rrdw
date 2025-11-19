#!/usr/bin/env python3
"""
config_loader.py - 配置載入器

負責載入和管理系統配置
"""

import os
import configparser
import logging
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigLoader:
    """配置載入器類別"""
    
    def __init__(self, config_file: str = None):
        """
        初始化配置載入器
        
        Args:
            config_file: 配置檔案路徑，None 則使用預設路徑
        """
        if config_file is None:
            # 嘗試多個預設路徑
            possible_paths = [
                '/opt/isp_monitor/config/config.ini',
                './config/config.ini',
                '../config/config.ini',
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    config_file = path
                    break
            
            if config_file is None:
                raise FileNotFoundError("找不到配置檔案，請指定 config_file 參數")
        
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self._load_config()
        
        logger.info(f"配置已載入: {config_file}")
    
    def _load_config(self):
        """載入配置檔案"""
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"配置檔案不存在: {self.config_file}")
        
        self.config.read(self.config_file, encoding='utf-8')
    
    def get(self, section: str, key: str, fallback=None):
        """
        取得配置值
        
        Args:
            section: 區段名稱
            key: 鍵名
            fallback: 預設值
        
        Returns:
            配置值
        """
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            if fallback is not None:
                return fallback
            raise
    
    def getint(self, section: str, key: str, fallback: int = None) -> int:
        """取得整數配置值"""
        try:
            return self.config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            if fallback is not None:
                return fallback
            raise
    
    def getfloat(self, section: str, key: str, fallback: float = None) -> float:
        """取得浮點數配置值"""
        try:
            return self.config.getfloat(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            if fallback is not None:
                return fallback
            raise
    
    def getboolean(self, section: str, key: str, fallback: bool = None) -> bool:
        """取得布林配置值"""
        try:
            return self.config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            if fallback is not None:
                return fallback
            raise
    
    # 便利方法 - 常用配置
    
    @property
    def root_path(self) -> str:
        """系統根路徑"""
        return self.get('base', 'root_path', '/opt/isp_monitor')
    
    @property
    def snmp_community(self) -> str:
        """SNMP Community"""
        return self.get('snmp', 'default_community', 'public')
    
    @property
    def snmp_timeout(self) -> int:
        """SNMP 超時時間"""
        return self.getint('snmp', 'timeout', 5)
    
    @property
    def snmp_retries(self) -> int:
        """SNMP 重試次數"""
        return self.getint('snmp', 'retries', 2)
    
    @property
    def e320_timeout(self) -> int:
        """E320 專用超時時間"""
        return self.getint('snmp', 'e320_timeout', 10)
    
    @property
    def e320_retries(self) -> int:
        """E320 專用重試次數"""
        return self.getint('snmp', 'e320_retries', 3)
    
    @property
    def rrd_base_dir(self) -> str:
        """RRD 基礎目錄"""
        base = self.get('rrd', 'base_dir', 'data')
        if not os.path.isabs(base):
            base = os.path.join(self.root_path, base)
        return base
    
    @property
    def rrd_step(self) -> int:
        """RRD Step"""
        return self.getint('rrd', 'step', 1200)
    
    @property
    def rrd_heartbeat(self) -> int:
        """RRD Heartbeat"""
        return self.getint('rrd', 'heartbeat', 2400)
    
    @property
    def fork_threshold(self) -> int:
        """多進程閾值"""
        return self.getint('collection', 'fork_threshold', 2000)
    
    @property
    def max_processes(self) -> int:
        """最大進程數"""
        return self.getint('collection', 'max_processes', 4)
    
    @property
    def log_dir(self) -> str:
        """日誌目錄"""
        log_dir = self.get('logging', 'log_dir', 'logs')
        if not os.path.isabs(log_dir):
            log_dir = os.path.join(self.root_path, log_dir)
        return log_dir
    
    @property
    def log_level(self) -> str:
        """日誌級別"""
        return self.get('logging', 'log_level', 'INFO')
    
    @property
    def map_file_dir(self) -> str:
        """Map 檔案目錄"""
        map_dir = self.get('paths', 'map_file_dir', 'config/maps')
        if not os.path.isabs(map_dir):
            map_dir = os.path.join(self.root_path, map_dir)
        return map_dir
    
    @property
    def bras_map_file(self) -> str:
        """BRAS 映射檔案"""
        bras_map = self.get('paths', 'bras_map_file', 'config/BRAS-Map.txt')
        if not os.path.isabs(bras_map):
            bras_map = os.path.join(self.root_path, bras_map)
        return bras_map
    
    def get_device_timeout(self, device_type: int) -> int:
        """
        根據設備類型取得 SNMP 超時時間
        
        Args:
            device_type: 設備類型 (1=MX240, 2=MX960, 3=E320, 4=ACX7024)
        
        Returns:
            超時時間（秒）
        """
        if device_type == 3:  # E320
            return self.e320_timeout
        return self.snmp_timeout
    
    def get_device_retries(self, device_type: int) -> int:
        """
        根據設備類型取得 SNMP 重試次數
        
        Args:
            device_type: 設備類型
        
        Returns:
            重試次數
        """
        if device_type == 3:  # E320
            return self.e320_retries
        return self.snmp_retries
    
    def load_bras_map(self) -> List[Dict]:
        """
        載入 BRAS 映射檔案
        
        Returns:
            BRAS 設備列表
        """
        devices = []
        
        if not os.path.exists(self.bras_map_file):
            logger.warning(f"BRAS 映射檔案不存在: {self.bras_map_file}")
            return devices
        
        with open(self.bras_map_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # 跳過空行和註解
                if not line or line.startswith('#'):
                    continue
                
                # 解析 TSV 格式
                parts = line.split('\t')
                if len(parts) < 10:
                    logger.warning(f"BRAS-Map 第 {line_num} 行格式錯誤: {line}")
                    continue
                
                try:
                    device = {
                        'area': parts[0],
                        'device_type': int(parts[1]),
                        'ip': parts[2],
                        'circuit_id': parts[3],
                        'slot': int(parts[4]),
                        'port': int(parts[5]),
                        'interface_type': parts[6],
                        'bandwidth_max': int(parts[7]),
                        'if_assign': int(parts[8]),
                        'pic': int(parts[9])
                    }
                    devices.append(device)
                except (ValueError, IndexError) as e:
                    logger.warning(f"BRAS-Map 第 {line_num} 行解析失敗: {e}")
                    continue
        
        logger.info(f"載入 {len(devices)} 個 BRAS 設備")
        return devices
    
    def get_map_file_path(self, device_ip: str) -> str:
        """
        取得設備的 Map 檔案路徑
        
        Args:
            device_ip: 設備 IP
        
        Returns:
            Map 檔案路徑
        """
        map_filename = f"map_{device_ip}.txt"
        return os.path.join(self.map_file_dir, map_filename)


# 測試程式
if __name__ == '__main__':
    # 設定日誌
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # 載入配置
        config = ConfigLoader()
        
        # 顯示主要配置
        print("=== 主要配置 ===")
        print(f"根路徑: {config.root_path}")
        print(f"SNMP Community: {config.snmp_community}")
        print(f"SNMP Timeout: {config.snmp_timeout}s")
        print(f"E320 Timeout: {config.e320_timeout}s")
        print(f"RRD Step: {config.rrd_step}s")
        print(f"Fork Threshold: {config.fork_threshold}")
        print(f"Max Processes: {config.max_processes}")
        
        # 載入 BRAS 映射
        print("\n=== BRAS 設備 ===")
        devices = config.load_bras_map()
        for dev in devices[:5]:  # 只顯示前 5 個
            print(f"{dev['area']} - Type {dev['device_type']} - {dev['ip']}")
        
        if len(devices) > 5:
            print(f"... 還有 {len(devices) - 5} 個設備")
        
        print("\n✓ 配置載入測試完成")
        
    except Exception as e:
        print(f"✗ 錯誤: {e}")
        import traceback
        traceback.print_exc()
