#!/usr/bin/env python3
# isp_traffic_collector_final.py - 修正版（正確的 RRD 結構）

import time
import rrdtool
import configparser
import subprocess
from datetime import datetime
import logging
import os
import sys
import re
import fcntl
from concurrent.futures import ThreadPoolExecutor, as_completed

# ========== 取得執行檔所在目錄 ==========
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, 'config.ini')

# ========== 讀取設定檔 ==========
if os.path.exists(CONFIG_FILE):
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    
    log_dir = config.get('logging', 'log_dir', fallback='/var/log/isp_traffic')
    log_file = config.get('logging', 'log_file', fallback='collector.log')
    log_level = config.get('logging', 'log_level', fallback='INFO')
    
    DB_ENABLED = config.getboolean('database', 'enabled', fallback=False)
    DB_CONFIG = {
        'host': config.get('database', 'host', fallback='localhost'),
        'port': config.getint('database', 'port', fallback=3306),
        'user': config.get('database', 'user', fallback='isp_monitor'),
        'password': config.get('database', 'password', fallback=''),
        'database': config.get('database', 'database', fallback='isp_traffic_monitor')
    } if DB_ENABLED else None
    
    RRD_BASE_DIR = config.get('rrd', 'base_dir', fallback='/home/bulks_data')
    RRD_SUM_DIR = config.get('rrd', 'sum_dir', fallback='/home/bulks_data/sum')
    RRD_SUM2M_DIR = config.get('rrd', 'sum2m_dir', fallback='/home/bulks_data/sum2m')
    RRD_STEP = config.getint('rrd', 'step', fallback=1200)
    
    DEFAULT_COMMUNITY = config.get('snmp', 'default_community', fallback='public')
    SNMP_TIMEOUT = config.getint('snmp', 'timeout', fallback=5)
    SNMP_RETRIES = config.getint('snmp', 'retries', fallback=2)
    SNMP_VERSION = config.get('snmp', 'version', fallback='2c')
    
    FAIR_USAGE_POLICIES = {
        '3072_640': config.getint('fair_usage', 'profile_3072_640', fallback=3072000),
        '4096_1024': config.getint('fair_usage', 'profile_4096_1024', fallback=2800000),
        'default': config.getint('fair_usage', 'default_limit', fallback=2048000)
    }
    
    MAP_FILE_DIR = config.get('paths', 'map_file_dir', fallback='/home/bulks_script')
    OVERBIT_LOG = config.get('paths', 'overbit_log', fallback='/var/log/ob_log.txt')
    
    print(f"✓ 載入設定檔: {CONFIG_FILE}")
    
else:
    print(f"⚠️  找不到設定檔: {CONFIG_FILE}")
    print("使用預設設定")
    
    log_dir = '/var/log/isp_traffic'
    log_file = 'collector.log'
    log_level = 'INFO'
    
    DB_ENABLED = False
    DB_CONFIG = None
    
    RRD_BASE_DIR = '/home/bulks_data'
    RRD_SUM_DIR = '/home/bulks_data/sum'
    RRD_SUM2M_DIR = '/home/bulks_data/sum2m'
    RRD_STEP = 1200
    
    DEFAULT_COMMUNITY = 'public'
    SNMP_TIMEOUT = 5
    SNMP_RETRIES = 2
    SNMP_VERSION = '2c'
    
    FAIR_USAGE_POLICIES = {
        '3072_640': 3072000,
        '4096_1024': 2800000,
        'default': 2048000
    }
    
    MAP_FILE_DIR = '/home/bulks_script'
    OVERBIT_LOG = '/var/log/ob_log.txt'

os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, log_file)),
        logging.StreamHandler(sys.stdout)
    ]
)

OID_IF_HC_OUT_OCTETS = '.1.3.6.1.2.1.31.1.1.1.10'

if DB_ENABLED:
    try:
        import mysql.connector
        logging.info("資料庫模式：啟用")
    except ImportError:
        logging.error("錯誤：啟用資料庫但無法匯入 mysql.connector")
        sys.exit(1)
else:
    logging.info("資料庫模式：停用（僅寫入 RRD）")
    mysql = None

class FinalCollector:
    def __init__(self, rrd_base_dir, db_config=None):
        self.rrd_base_dir = rrd_base_dir
        self.db_config = db_config
        self.db = None
        self.cursor = None
        self.lock_file = None
        
        if self.db_config:
            try:
                self.db = mysql.connector.connect(**self.db_config)
                self.cursor = self.db.cursor(dictionary=True)
                logging.info("✓ 資料庫連線成功")
            except Exception as e:
                logging.error(f"✗ 資料庫連線失敗: {e}")
                logging.warning("將以純 RRD 模式運作")
                self.db = None
                self.cursor = None
    
    def acquire_lock(self, device_ip, slot, port):
        """取得執行鎖"""
        lock_dir = '/tmp/isp_monitor_locks'
        os.makedirs(lock_dir, exist_ok=True)
        
        lock_file_path = f"{lock_dir}/collector_{device_ip}_{slot}_{port}.lock"
        
        try:
            self.lock_file = open(lock_file_path, 'w')
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            self.lock_file.write(f"{os.getpid()}\n")
            self.lock_file.write(f"{datetime.now().isoformat()}\n")
            self.lock_file.flush()
            
            logging.info(f"✓ 取得執行鎖: {lock_file_path}")
            return True
            
        except IOError:
            logging.error(f"✗ 無法取得執行鎖（另一個收集程序正在執行）")
            if self.lock_file:
                self.lock_file.close()
                self.lock_file = None
            return False
    
    def release_lock(self):
        """釋放執行鎖"""
        if self.lock_file:
            try:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
                logging.info("✓ 釋放執行鎖")
            except:
                pass
            self.lock_file = None
    
    def get_snmp_value(self, target, community, ifindex):
        """使用 snmpget 取得單一介面值"""
        oid = f"{OID_IF_HC_OUT_OCTETS}.{ifindex}"
        
        try:
            cmd = [
                'snmpget',
                '-v', SNMP_VERSION,
                '-c', community,
                '-t', str(SNMP_TIMEOUT),
                '-r', str(SNMP_RETRIES),
                '-Oqv',
                target,
                oid
            ]
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                value = result.stdout.strip()
                value = re.sub(r'[^\d]', '', value)
                return (ifindex, int(value) if value else 0)
            
            return (ifindex, 0)
            
        except Exception as e:
            logging.debug(f"取得 ifIndex {ifindex} 失敗: {e}")
            return (ifindex, 0)
    
    def get_snmp_batch_parallel(self, target, community, ifindexes):
        """並行批次查詢"""
        results = {}
        ifindex_list = list(ifindexes)
        total = len(ifindex_list)
        
        logging.info(f"並行批次查詢 {total} 個介面（10 執行緒）...")
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ifindex = {
                executor.submit(self.get_snmp_value, target, community, ifindex): ifindex
                for ifindex in ifindex_list
            }
            
            completed = 0
            for future in as_completed(future_to_ifindex):
                ifindex, value = future.result()
                if value > 0:
                    results[ifindex] = value
                
                completed += 1
                if completed % 100 == 0:
                    logging.info(f"  進度: {completed}/{total}")
        
        elapsed = time.time() - start_time
        
        logging.info(
            f"✓ 並行查詢完成: {len(results)} 個介面, "
            f"耗時 {elapsed:.1f} 秒 ({total/elapsed:.1f} 個/秒)"
        )
        
        return results
    
    def get_user_rrd_path(self, device_ip, slot, port, download_kbps, upload_kbps, vlan):
        """
        生成個別用戶 RRD 路徑
        格式: {IP}_{slot}_{port}_{download}_{upload}_{vlan}.rrd
        """
        filename = f"{device_ip}_{slot}_{port}_{download_kbps}_{upload_kbps}_{vlan}.rrd"
        return f"{self.rrd_base_dir}/{device_ip}/{filename}"
    
    def get_sum_rrd_path(self, base_dir, device_ip, slot, port, download_kbps, upload_kbps):
        """
        生成彙總 RRD 路徑
        格式: {IP}_{slot}_{port}_{download}_{upload}_sum.rrd
        """
        filename = f"{device_ip}_{slot}_{port}_{download_kbps}_{upload_kbps}_sum.rrd"
        return f"{base_dir}/{device_ip}/{filename}"
    
    def create_rrd_counter(self, rrd_path, download_kbps, upload_kbps):
        """建立 COUNTER 類型 RRD"""
        if os.path.exists(rrd_path):
            return True
        
        os.makedirs(os.path.dirname(rrd_path), exist_ok=True)
        
        ds_name = f"{download_kbps}_{upload_kbps}"
        max_ds = download_kbps * 1024 + 10240
        
        try:
            rrdtool.create(
                rrd_path,
                '--step', str(RRD_STEP),
                '--start', str(int(time.time()) - RRD_STEP),
                f'DS:{ds_name}:COUNTER:{RRD_STEP * 2}:0:{max_ds}',
                'RRA:AVERAGE:0.5:1:4465',
                'RRA:AVERAGE:0.5:24:564',
                'RRA:AVERAGE:0.5:144:1096',
                'RRA:MAX:0.5:1:4465',
                'RRA:MAX:0.5:24:564',
                'RRA:MAX:0.5:144:1096'
            )
            logging.debug(f"✓ 建立 COUNTER RRD: {rrd_path}")
            return True
        except Exception as e:
            logging.error(f"建立 RRD 失敗: {e}")
            return False
    
    def create_rrd_gauge(self, rrd_path, speed_key):
        """建立 GAUGE 類型 RRD"""
        if os.path.exists(rrd_path):
            return True
        
        os.makedirs(os.path.dirname(rrd_path), exist_ok=True)
        
        try:
            rrdtool.create(
                rrd_path,
                '--step', str(RRD_STEP),
                '--start', str(int(time.time()) - RRD_STEP),
                f'DS:{speed_key}:GAUGE:600:0:U',
                'RRA:AVERAGE:0.5:1:4465',
                'RRA:AVERAGE:0.5:24:564',
                'RRA:AVERAGE:0.5:144:1096',
                'RRA:MAX:0.5:1:4465',
                'RRA:MAX:0.5:24:564',
                'RRA:MAX:0.5:144:1096'
            )
            logging.debug(f"✓ 建立 GAUGE RRD: {rrd_path}")
            return True
        except Exception as e:
            logging.error(f"建立 GAUGE RRD 失敗: {e}")
            return False
    
    def update_rrd_counter(self, rrd_path, timestamp, counter_bits):
        """更新 COUNTER RRD"""
        try:
            rrdtool.update(rrd_path, f"{timestamp}:{int(counter_bits)}")
            return True
        except Exception as e:
            if 'illegal attempt to update' in str(e):
                logging.debug(f"RRD 已更新: {rrd_path}")
                return True
            logging.error(f"RRD 更新失敗 {rrd_path}: {e}")
            return False
    
    def update_rrd_gauge(self, rrd_path, timestamp, rate_bps):
        """更新 GAUGE RRD"""
        try:
            rrdtool.update(rrd_path, f"{timestamp}:{int(rate_bps)}")
            return True
        except Exception as e:
            if 'illegal attempt to update' in str(e):
                logging.debug(f"RRD 已更新: {rrd_path}")
                return True
            logging.error(f"RRD 更新失敗 {rrd_path}: {e}")
            return False
    
    def read_rrd_rate(self, rrd_path, timestamp):
        """從 RRD 讀取速率"""
        try:
            start_time = timestamp - 5
            end_time = timestamp + RRD_STEP
            
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
    
    def apply_fair_usage_policy(self, bits, speed_key, device_ip, slot, port, user_info):
        """套用 Fair Usage Policy"""
        if bits < 2048000:
            return bits, False
        
        limit = FAIR_USAGE_POLICIES.get(speed_key, FAIR_USAGE_POLICIES['default'])
        
        if bits >= limit:
            overbits = bits - limit
            
            log_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            try:
                os.makedirs(os.path.dirname(OVERBIT_LOG), exist_ok=True)
                with open(OVERBIT_LOG, 'a') as f:
                    f.write(f"{log_time} {device_ip} {slot} {port} {user_info} {overbits}\n")
            except Exception as e:
                logging.error(f"寫入超標日誌失敗: {e}")
            
            return limit, True
        
        return bits, False
    
    def load_users_from_map(self, device_ip, slot, port):
        """
        從 map 檔案讀取用戶列表
        格式: user_code, slot_port_vci, speed_spec, ifindex
        例如: A123456, 1_2_0_100, 8192_640, 5933254
        """
        map_file = os.path.join(MAP_FILE_DIR, f'map_{device_ip}.txt')
        
        if not os.path.exists(map_file):
            logging.error(f"找不到 map 檔案: {map_file}")
            return []
        
        users = []
        
        try:
            with open(map_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split(',')
                    if len(parts) != 4:
                        continue
                    
                    user_code = parts[0].strip()
                    slot_port_vci = parts[1].strip()
                    speed_spec = parts[2].strip()
                    ifindex = parts[3].strip()
                    
                    # 解析 slot_port_vpi_vci
                    spv_parts = slot_port_vci.split('_')
                    if len(spv_parts) != 4:
                        continue
                    
                    user_slot = int(spv_parts[0])
                    user_port = int(spv_parts[1])
                    vpi = spv_parts[2]
                    vci = spv_parts[3]
                    
                    if user_slot != slot or user_port != port:
                        continue
                    
                    # 解析速率
                    speed_parts = speed_spec.split('_')
                    if len(speed_parts) != 2:
                        continue
                    
                    download_kbps = int(speed_parts[0])
                    upload_kbps = int(speed_parts[1])
                    
                    users.append({
                        'user_code': user_code,
                        'interface_index': int(ifindex),
                        'contract_download_rate': download_kbps * 1000,
                        'contract_upload_rate': upload_kbps * 1000,
                        'slot_number': user_slot,
                        'port_number': user_port,
                        'vpi': vpi,
                        'vci': vci,
                        'vlan': vci  # 使用 VCI 作為 VLAN 識別
                    })
        
        except Exception as e:
            logging.error(f"讀取 map 檔案失敗: {e}")
            return []
        
        return users
    
    def collect_device(self, device_ip, device_name, community, slot, port, device_id=None):
        """主收集邏輯（正確的 RRD 結構）"""
        logging.info(f"=" * 70)
        logging.info(f"收集: {device_name} ({device_ip}) Slot {slot} Port {port}")
        logging.info(f"=" * 70)
        
        # 取得執行鎖
        if not self.acquire_lock(device_ip, slot, port):
            logging.error("無法取得執行鎖，退出")
            return
        
        try:
            # 取得用戶列表
            users = self.load_users_from_map(device_ip, slot, port)
            logging.info(f"從 map 檔案載入 {len(users)} 個用戶")
            
            if not users:
                logging.warning("找不到用戶資料")
                return
            
            timestamp = int(time.time())
            timestamp = timestamp - (timestamp % RRD_STEP)
            
            # 取得需要的 ifIndex
            required_indexes = set(str(user['interface_index']) for user in users)
            
            # 並行 SNMP 查詢
            if_out_octets = self.get_snmp_batch_parallel(device_ip, community, required_indexes)
            
            if not if_out_octets:
                logging.error("SNMP 查詢失敗")
                return
            
            logging.info(f"取得 {len(if_out_octets)} 個介面資料")
            
            # Step 1: 寫入個別用戶 RRD（含 VLAN）
            logging.info("Step 1: 寫入個別用戶 RRD...")
            
            user_rrd_paths = {}
            speed_groups = {}
            
            for user in users:
                if_index = str(user['interface_index'])
                
                if if_index not in if_out_octets:
                    continue
                
                out_octets = if_out_octets[if_index]
                out_bits = out_octets * 8
                
                download_kbps = int(user['contract_download_rate'] / 1000)
                upload_kbps = int(user['contract_upload_rate'] / 1000)
                vlan = user['vlan']
                
                # 個別用戶 RRD 路徑（含 VLAN）
                user_rrd_path = self.get_user_rrd_path(
                    device_ip, slot, port,
                    download_kbps, upload_kbps, vlan
                )
                
                # 建立並更新個別用戶 RRD
                self.create_rrd_counter(user_rrd_path, download_kbps, upload_kbps)
                self.update_rrd_counter(user_rrd_path, timestamp, out_bits)
                
                # 記錄到速率組
                speed_key = f"{download_kbps}_{upload_kbps}"
                if speed_key not in speed_groups:
                    speed_groups[speed_key] = []
                
                speed_groups[speed_key].append({
                    'user_code': user['user_code'],
                    'vlan': vlan,
                    'rrd_path': user_rrd_path
                })
                
                user_rrd_paths[user['user_code']] = user_rrd_path
            
            logging.info(f"✓ 寫入 {len(user_rrd_paths)} 個用戶 RRD")
            
            # Step 2: 讀取速率並彙總
            logging.info("Step 2: 讀取速率並彙總...")
            
            aggregated_rate = {}
            
            for speed_key, users_list in speed_groups.items():
                total_bits = 0
                total_bits_2m = 0
                
                for user_info in users_list:
                    # 從個別用戶 RRD 讀取速率
                    bits = self.read_rrd_rate(user_info['rrd_path'], timestamp)
                    
                    if bits > 0:
                        total_bits += bits
                        
                        # 套用 Fair Usage Policy
                        limited_bits, is_over = self.apply_fair_usage_policy(
                            bits,
                            speed_key,
                            device_ip,
                            slot,
                            port,
                            f"{speed_key}_{user_info['vlan']}"
                        )
                        
                        total_bits_2m += limited_bits
                
                aggregated_rate[speed_key] = {
                    'total_bits': total_bits,
                    'total_bits_2m': total_bits_2m,
                    'user_count': len(users_list)
                }
            
            # Step 3: 寫入彙總 RRD
            logging.info("Step 3: 寫入彙總 RRD (sum/)...")
            
            for speed_key, rate_data in aggregated_rate.items():
                download_kbps, upload_kbps = map(int, speed_key.split('_'))
                
                # Sum RRD（無限制）
                sum_rrd_path = self.get_sum_rrd_path(
                    RRD_SUM_DIR,
                    device_ip,
                    slot,
                    port,
                    download_kbps,
                    upload_kbps
                )
                
                self.create_rrd_gauge(sum_rrd_path, speed_key)
                self.update_rrd_gauge(sum_rrd_path, timestamp, rate_data['total_bits'])
                
                # Sum2M RRD（有限制）
                sum2m_rrd_path = self.get_sum_rrd_path(
                    RRD_SUM2M_DIR,
                    device_ip,
                    slot,
                    port,
                    download_kbps,
                    upload_kbps
                )
                
                self.create_rrd_gauge(sum2m_rrd_path, speed_key)
                self.update_rrd_gauge(sum2m_rrd_path, timestamp, rate_data['total_bits_2m'])
                
                logging.info(
                    f"  ✓ {speed_key}: {rate_data['user_count']} 用戶, "
                    f"{rate_data['total_bits']/1000000:.2f} Mbps "
                    f"(2M限制: {rate_data['total_bits_2m']/1000000:.2f} Mbps)"
                )
            
            logging.info(f"=" * 70)
            
        finally:
            self.release_lock()
    
    def close(self):
        """關閉資料庫連線"""
        self.release_lock()
        if self.cursor:
            self.cursor.close()
        if self.db:
            self.db.close()

def main():
    if len(sys.argv) < 4:
        print("=" * 70)
        print("ISP 流量收集器")
        print("=" * 70)
        print()
        print("用法: python3 isp_traffic_collector_final.py <device_ip> <slot> <port> [device_name] [community]")
        print()
        print("範例:")
        print("  python3 isp_traffic_collector_final.py 61.64.191.166 1 2")
        print("  python3 isp_traffic_collector_final.py 61.64.191.166 1 2 ERX1 public")
        print()
        print("設定檔:")
        print(f"  位置: {CONFIG_FILE}")
        print(f"  狀態: {'✓ 存在' if os.path.exists(CONFIG_FILE) else '✗ 不存在（使用預設值）'}")
        print()
        print("RRD 結構:")
        print("  個別用戶: /home/bulks_data/{IP}/{IP}_{slot}_{port}_{down}_{up}_{vlan}.rrd")
        print("  彙總 Sum:  /home/bulks_data/sum/{IP}/{IP}_{slot}_{port}_{down}_{up}_sum.rrd")
        print("  彙總 2M:   /home/bulks_data/sum2m/{IP}/{IP}_{slot}_{port}_{down}_{up}_sum.rrd")
        print()
        sys.exit(1)
    
    device_ip = sys.argv[1]
    slot = int(sys.argv[2])
    port = int(sys.argv[3])
    device_name = sys.argv[4] if len(sys.argv) > 4 else device_ip
    community = sys.argv[5] if len(sys.argv) > 5 else DEFAULT_COMMUNITY
    
    logging.info(f"腳本目錄: {SCRIPT_DIR}")
    logging.info(f"設定檔: {CONFIG_FILE}")
    
    collector = FinalCollector(RRD_BASE_DIR, DB_CONFIG if DB_ENABLED else None)
    
    start_time = time.time()
    
    try:
        collector.collect_device(
            device_ip,
            device_name,
            community,
            slot,
            port
        )
    except Exception as e:
        logging.error(f"收集失敗: {e}")
        import traceback
        logging.error(traceback.format_exc())
        raise
    finally:
        collector.close()
    
    elapsed = time.time() - start_time
    
    if elapsed >= 1100:
        logging.warning(f"⚠️  執行時間過長: {elapsed:.1f} 秒")
    else:
        logging.info(f"✓ 執行完成: {elapsed:.1f} 秒")

if __name__ == '__main__':
    main()
