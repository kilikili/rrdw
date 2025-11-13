#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISP Traffic Collector - Final Production Version
================================================

功能：
- 透過 SNMP 收集網路設備流量資料
- 支援 Juniper ERX/MX/ACX 系列設備
- 儲存至 RRD 資料庫
- 完整的錯誤處理和日誌記錄

使用方式：
    python3 isp_traffic_collector_final.py <device_ip> <slot> <port> [area] [community]

範例：
    python3 isp_traffic_collector_final.py 192.168.1.1 1 0 北區 public
    python3 isp_traffic_collector_final.py 10.1.1.1 2 3

作者：ISP Tech Team
版本：1.0
日期：2025-11-13
"""

import os
import sys
import time
import subprocess
import configparser
import logging
from datetime import datetime
from pathlib import Path

# ============================================================================
# 設定和常數
# ============================================================================

# 預設值
DEFAULT_CONFIG_FILE = 'config.ini'
DEFAULT_COMMUNITY = 'public'
DEFAULT_SNMP_VERSION = '2c'
DEFAULT_TIMEOUT = 5
DEFAULT_RETRIES = 2

# RRD 設定
RRD_STEP = 1200  # 20 分鐘

# SNMP OID 定義
# 標準 IF-MIB OIDs
OID_IF_DESC = '1.3.6.1.2.1.2.2.1.2'       # ifDescr
OID_IF_INDEX = '1.3.6.1.2.1.2.2.1.1'      # ifIndex
OID_IF_IN_OCTETS = '1.3.6.1.2.1.2.2.1.10'   # ifInOctets
OID_IF_OUT_OCTETS = '1.3.6.1.2.1.2.2.1.16'  # ifOutOctets
OID_IF_IN_UCAST = '1.3.6.1.2.1.2.2.1.11'    # ifInUcastPkts
OID_IF_OUT_UCAST = '1.3.6.1.2.1.2.2.1.17'   # ifOutUcastPkts
OID_IF_IN_ERRORS = '1.3.6.1.2.1.2.2.1.14'   # ifInErrors
OID_IF_OUT_ERRORS = '1.3.6.1.2.1.2.2.1.20'  # ifOutErrors

# High Capacity Counter (64-bit)
OID_IF_HC_IN_OCTETS = '1.3.6.1.2.1.31.1.1.1.6'   # ifHCInOctets
OID_IF_HC_OUT_OCTETS = '1.3.6.1.2.1.31.1.1.1.10'  # ifHCOutOctets

# ============================================================================
# 設定日誌
# ============================================================================

def setup_logging(log_file=None, log_level=logging.INFO):
    """設定日誌系統"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format))
    handlers.append(console_handler)
    
    # File handler (如果指定)
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(logging.Formatter(log_format))
            handlers.append(file_handler)
        except Exception as e:
            print(f"Warning: Cannot create log file {log_file}: {e}")
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers
    )
    
    return logging.getLogger(__name__)

# ============================================================================
# 配置讀取
# ============================================================================

class Config:
    """配置管理類別"""
    
    def __init__(self, config_file=DEFAULT_CONFIG_FILE):
        self.config = configparser.ConfigParser()
        self.config_file = config_file
        self.load_config()
    
    def load_config(self):
        """載入配置檔"""
        if os.path.exists(self.config_file):
            try:
                self.config.read(self.config_file)
                logger.info(f"Loaded config from {self.config_file}")
            except Exception as e:
                logger.warning(f"Cannot read config file: {e}")
        else:
            logger.warning(f"Config file not found: {self.config_file}, using defaults")
    
    def get(self, section, key, fallback=None):
        """取得配置值"""
        try:
            return self.config.get(section, key)
        except:
            return fallback
    
    def getint(self, section, key, fallback=None):
        """取得整數配置值"""
        try:
            return self.config.getint(section, key)
        except:
            return fallback
    
    def getboolean(self, section, key, fallback=None):
        """取得布林配置值"""
        try:
            return self.config.getboolean(section, key)
        except:
            return fallback

# ============================================================================
# SNMP 查詢
# ============================================================================

class SNMPClient:
    """SNMP 客戶端"""
    
    def __init__(self, host, community=DEFAULT_COMMUNITY, version=DEFAULT_SNMP_VERSION, 
                 timeout=DEFAULT_TIMEOUT, retries=DEFAULT_RETRIES):
        self.host = host
        self.community = community
        self.version = version
        self.timeout = timeout
        self.retries = retries
    
    def get(self, oid):
        """SNMP GET 查詢"""
        cmd = [
            'snmpget',
            '-v', self.version,
            '-c', self.community,
            '-t', str(self.timeout),
            '-r', str(self.retries),
            '-Oqv',  # 只輸出值，不要 OID
            self.host,
            oid
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout + 5
            )
            
            if result.returncode == 0:
                value = result.stdout.strip()
                # 移除可能的引號
                value = value.strip('"')
                return value
            else:
                logger.error(f"SNMP GET failed: {result.stderr.strip()}")
                return None
        
        except subprocess.TimeoutExpired:
            logger.error(f"SNMP GET timeout for {oid}")
            return None
        except Exception as e:
            logger.error(f"SNMP GET error: {e}")
            return None
    
    def walk(self, oid):
        """SNMP WALK 查詢"""
        cmd = [
            'snmpwalk',
            '-v', self.version,
            '-c', self.community,
            '-t', str(self.timeout),
            '-r', str(self.retries),
            '-Oqv',
            self.host,
            oid
        ]
        
        try:
            # E320 設備回應較慢，增加 timeout
            # 使用更長的 timeout (timeout * 10 秒)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout * 10
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                return [line.strip().strip('"') for line in lines if line.strip()]
            else:
                logger.error(f"SNMP WALK failed: {result.stderr.strip()}")
                return []
        
        except subprocess.TimeoutExpired:
            logger.error(f"SNMP WALK timeout for {oid} after {self.timeout * 10} seconds")
            logger.warning(f"Device may be slow to respond, consider increasing timeout in config.ini")
            return []
        except Exception as e:
            logger.error(f"SNMP WALK error: {e}")
            return []
    
    def get_bulk(self, oids):
        """批次查詢多個 OID"""
        results = {}
        for oid in oids:
            value = self.get(oid)
            results[oid] = value
        return results

# ============================================================================
# 介面資訊查詢
# ============================================================================

class InterfaceInfo:
    """網路介面資訊"""
    
    def __init__(self, snmp_client):
        self.snmp = snmp_client
    
    def find_interface_index(self, slot, port):
        """
        尋找介面的 ifIndex
        
        Args:
            slot: Slot 編號
            port: Port 編號
        
        Returns:
            ifIndex 或 None
        """
        # 可能的介面名稱格式
        possible_names = [
            # Juniper E320 格式
            f"GigabitEthernet{slot}/0/{port}",     # E320 主要格式
            f"FastEthernet{slot}/0/{port}",        # E320 FastEthernet
            f"TenGigabitEthernet{slot}/0/{port}",  # E320 10G
            
            # MX/ACX 格式
            f"ge-{slot}/{port}",      # Gigabit Ethernet
            f"xe-{slot}/{port}",      # 10 Gigabit Ethernet
            f"et-{slot}/{port}",      # 100 Gigabit Ethernet
            f"ge-{slot}/0/{port}",    # 某些型號的格式
            f"xe-{slot}/0/{port}",
            
            # 其他可能格式
            f"slot{slot}.port{port}",
            f"Slot{slot}/Port{port}",
        ]
        
        logger.info(f"Searching for interface: slot={slot}, port={port}")
        
        # 取得所有介面描述
        if_descs = self.snmp.walk(OID_IF_DESC)
        
        if not if_descs:
            logger.error("Cannot get interface descriptions via SNMP WALK")
            return None
        
        logger.info(f"Found {len(if_descs)} interfaces on device")
        
        # 搜尋匹配的介面
        for idx, desc in enumerate(if_descs, start=1):
            logger.debug(f"  ifIndex {idx}: {desc}")
            
            # 檢查是否匹配
            for name_pattern in possible_names:
                # E320 介面可能有 VLAN 後綴，所以使用 startswith
                if desc.startswith(name_pattern):
                    logger.info(f"Found interface: {desc} -> ifIndex={idx}")
                    return idx
                
                # 也嘗試不區分大小寫的匹配
                if name_pattern.lower() in desc.lower():
                    logger.info(f"Found interface (case-insensitive): {desc} -> ifIndex={idx}")
                    return idx
        
        logger.error(f"Cannot find interface for slot={slot}, port={port}")
        logger.info(f"Tried patterns: {possible_names}")
        logger.info(f"Available interfaces (first 20): {if_descs[:20]}")
        return None
    
    def get_interface_stats(self, if_index):
        """
        取得介面統計資料
        
        Args:
            if_index: 介面 index
        
        Returns:
            dict with statistics or None
        """
        oids = {
            'in_octets': f"{OID_IF_HC_IN_OCTETS}.{if_index}",
            'out_octets': f"{OID_IF_HC_OUT_OCTETS}.{if_index}",
            'in_ucast': f"{OID_IF_IN_UCAST}.{if_index}",
            'out_ucast': f"{OID_IF_OUT_UCAST}.{if_index}",
            'in_errors': f"{OID_IF_IN_ERRORS}.{if_index}",
            'out_errors': f"{OID_IF_OUT_ERRORS}.{if_index}",
        }
        
        # 如果 HC counter 失敗，嘗試標準 counter
        results = self.snmp.get_bulk(list(oids.values()))
        
        stats = {}
        for key, oid in oids.items():
            value = results.get(oid)
            if value and value != 'No Such Instance currently exists at this OID':
                try:
                    stats[key] = int(value)
                except ValueError:
                    logger.warning(f"Cannot convert {key}={value} to int")
                    stats[key] = 0
            else:
                # 如果是 HC counter 失敗，嘗試標準 counter
                if key in ['in_octets', 'out_octets']:
                    fallback_oid = OID_IF_IN_OCTETS if key == 'in_octets' else OID_IF_OUT_OCTETS
                    fallback_value = self.snmp.get(f"{fallback_oid}.{if_index}")
                    if fallback_value:
                        try:
                            stats[key] = int(fallback_value)
                            logger.debug(f"Using standard counter for {key}")
                        except ValueError:
                            stats[key] = 0
                    else:
                        stats[key] = 0
                else:
                    stats[key] = 0
        
        return stats if any(stats.values()) else None

# ============================================================================
# RRD 資料庫管理
# ============================================================================

class RRDManager:
    """RRD 資料庫管理"""
    
    def __init__(self, base_dir='/home/bulks_data'):
        self.base_dir = base_dir
        self.sum_dir = os.path.join(base_dir, 'sum')
        self.sum2m_dir = os.path.join(base_dir, 'sum2m')
        
        # 確保目錄存在
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.sum_dir, exist_ok=True)
        os.makedirs(self.sum2m_dir, exist_ok=True)
    
    def get_rrd_filename(self, device_ip, slot, port):
        """產生 RRD 檔案名稱"""
        # 將 IP 的最後一段作為識別
        ip_parts = device_ip.split('.')
        ip_suffix = ip_parts[-1] if len(ip_parts) == 4 else device_ip.replace('.', '_')
        
        filename = f"{ip_suffix}_{slot}_{port}.rrd"
        filepath = os.path.join(self.base_dir, filename)
        
        return filepath
    
    def create_rrd(self, filepath):
        """建立 RRD 資料庫"""
        if os.path.exists(filepath):
            logger.info(f"RRD file already exists: {filepath}")
            return True
        
        logger.info(f"Creating RRD file: {filepath}")
        
        cmd = [
            'rrdtool', 'create', filepath,
            '-s', str(RRD_STEP),
            
            # Data Sources (Counter type for traffic)
            f'DS:InOctets:COUNTER:{RRD_STEP*2}:0:U',
            f'DS:OutOctets:COUNTER:{RRD_STEP*2}:0:U',
            f'DS:InUcast:COUNTER:{RRD_STEP*2}:0:U',
            f'DS:OutUcast:COUNTER:{RRD_STEP*2}:0:U',
            f'DS:InErrors:COUNTER:{RRD_STEP*2}:0:U',
            f'DS:OutErrors:COUNTER:{RRD_STEP*2}:0:U',
            
            # RRA (Round Robin Archives)
            # 1. 原始資料保存 1 週 (603 個點 = 7 天)
            'RRA:AVERAGE:0.5:1:603',
            'RRA:MAX:0.5:1:603',
            
            # 2. 每 2 小時平均，保存 1 個月 (6個點 = 2小時, 603個 ≈ 1個月)
            'RRA:AVERAGE:0.5:6:603',
            'RRA:MAX:0.5:6:603',
            
            # 3. 每天平均，保存 2 年 (24個點 = 1天, 800個 ≈ 2年)
            'RRA:AVERAGE:0.5:24:800',
            'RRA:MAX:0.5:24:800',
            
            # 4. 每週平均，保存 5 年 (288個點 = 4天, 800個 ≈ 5年)
            'RRA:AVERAGE:0.5:288:800',
            'RRA:MAX:0.5:288:800',
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"RRD created successfully: {filepath}")
                return True
            else:
                logger.error(f"RRD creation failed: {result.stderr}")
                return False
        
        except Exception as e:
            logger.error(f"Error creating RRD: {e}")
            return False
    
    def update_rrd(self, filepath, stats):
        """更新 RRD 資料"""
        if not os.path.exists(filepath):
            logger.error(f"RRD file not found: {filepath}")
            return False
        
        # 準備資料 (N 表示現在的時間)
        data = (
            f"N:"
            f"{stats.get('in_octets', 'U')}:"
            f"{stats.get('out_octets', 'U')}:"
            f"{stats.get('in_ucast', 'U')}:"
            f"{stats.get('out_ucast', 'U')}:"
            f"{stats.get('in_errors', 'U')}:"
            f"{stats.get('out_errors', 'U')}"
        )
        
        cmd = ['rrdtool', 'update', filepath, data]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                logger.info(f"RRD updated: {filepath}")
                logger.debug(f"Data: {data}")
                return True
            else:
                logger.error(f"RRD update failed: {result.stderr}")
                return False
        
        except Exception as e:
            logger.error(f"Error updating RRD: {e}")
            return False

# ============================================================================
# 主要收集器
# ============================================================================

class TrafficCollector:
    """流量收集器主類別"""
    
    def __init__(self, device_ip, slot, port, area='', community=DEFAULT_COMMUNITY):
        self.device_ip = device_ip
        self.slot = int(slot)
        self.port = int(port)
        self.area = area
        self.community = community
        
        # 載入配置
        self.config = Config()
        
        # 從配置讀取設定
        self.snmp_timeout = self.config.getint('snmp', 'timeout', DEFAULT_TIMEOUT)
        self.snmp_retries = self.config.getint('snmp', 'retries', DEFAULT_RETRIES)
        self.rrd_base_dir = self.config.get('rrd', 'base_dir', '/home/bulks_data')
        
        # 初始化元件
        self.snmp = SNMPClient(
            device_ip, 
            community=community,
            timeout=self.snmp_timeout,
            retries=self.snmp_retries
        )
        self.interface = InterfaceInfo(self.snmp)
        self.rrd = RRDManager(self.rrd_base_dir)
    
    def collect(self):
        """執行收集"""
        start_time = time.time()
        
        logger.info("=" * 60)
        logger.info(f"Starting collection for {self.device_ip} Slot{self.slot} Port{self.port}")
        logger.info(f"Area: {self.area}, Community: {'***' if self.community else 'default'}")
        
        try:
            # 1. 尋找介面 index
            if_index = self.interface.find_interface_index(self.slot, self.port)
            if not if_index:
                logger.error("Cannot find interface index")
                return False
            
            # 2. 取得統計資料
            stats = self.interface.get_interface_stats(if_index)
            if not stats:
                logger.error("Cannot get interface statistics")
                return False
            
            logger.info(f"Statistics collected: {stats}")
            
            # 3. 取得 RRD 檔案路徑
            rrd_file = self.rrd.get_rrd_filename(self.device_ip, self.slot, self.port)
            
            # 4. 建立 RRD（如果不存在）
            if not os.path.exists(rrd_file):
                if not self.rrd.create_rrd(rrd_file):
                    logger.error("Cannot create RRD file")
                    return False
            
            # 5. 更新 RRD
            if not self.rrd.update_rrd(rrd_file, stats):
                logger.error("Cannot update RRD file")
                return False
            
            elapsed = time.time() - start_time
            logger.info(f"Collection completed successfully in {elapsed:.2f} seconds")
            logger.info("=" * 60)
            
            return True
        
        except Exception as e:
            logger.error(f"Collection failed: {e}", exc_info=True)
            return False

# ============================================================================
# 主程式
# ============================================================================

def print_usage():
    """顯示使用說明"""
    print("""
ISP Traffic Collector - Usage
==============================

Usage:
    python3 isp_traffic_collector_final.py <device_ip> <slot> <port> [area] [community]

Arguments:
    device_ip   : Device IP address (required)
    slot        : Slot number (required)
    port        : Port number (required)
    area        : Area name (optional)
    community   : SNMP community string (optional, default: public)

Examples:
    python3 isp_traffic_collector_final.py 192.168.1.1 1 0
    python3 isp_traffic_collector_final.py 192.168.1.1 1 0 北區
    python3 isp_traffic_collector_final.py 192.168.1.1 1 0 北區 public

Environment Variables:
    SNMP_COMMUNITY  : Default SNMP community string
    LOG_LEVEL       : Logging level (DEBUG, INFO, WARNING, ERROR)

Config File:
    config.ini      : Configuration file (optional)
    
For more information, see the documentation.
""")

def main():
    """主程式進入點"""
    # 檢查參數
    if len(sys.argv) < 4:
        print("Error: Insufficient arguments")
        print_usage()
        sys.exit(1)
    
    # 解析參數
    device_ip = sys.argv[1]
    slot = sys.argv[2]
    port = sys.argv[3]
    area = sys.argv[4] if len(sys.argv) > 4 else ''
    community = sys.argv[5] if len(sys.argv) > 5 else os.environ.get('SNMP_COMMUNITY', DEFAULT_COMMUNITY)
    
    # 設定日誌
    log_level_str = os.environ.get('LOG_LEVEL', 'INFO')
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    
    global logger
    logger = setup_logging(log_level=log_level)
    
    # 顯示開始資訊
    logger.info("ISP Traffic Collector Started")
    logger.info(f"Version: 1.0")
    logger.info(f"Device: {device_ip}, Slot: {slot}, Port: {port}")
    
    # 建立收集器並執行
    collector = TrafficCollector(device_ip, slot, port, area, community)
    
    success = collector.collect()
    
    # 結束
    if success:
        logger.info("Collection finished successfully")
        sys.exit(0)
    else:
        logger.error("Collection failed")
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
