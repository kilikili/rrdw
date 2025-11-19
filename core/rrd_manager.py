#!/usr/bin/env python3
"""
rrd_manager.py - RRD 管理器

負責 RRD 檔案的建立、更新和管理
"""

import os
import time
import logging
import subprocess
from typing import Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class RRDManager:
    """RRD 管理器類別"""
    
    def __init__(self, base_dir: str, step: int = 1200, heartbeat: int = 2400):
        """
        初始化 RRD 管理器
        
        Args:
            base_dir: RRD 基礎目錄
            step: RRD step (秒)
            heartbeat: RRD heartbeat (秒)
        """
        self.base_dir = base_dir
        self.step = step
        self.heartbeat = heartbeat
        
        # 各層目錄
        self.user_dir = os.path.join(base_dir, 'user')
        self.sum_dir = os.path.join(base_dir, 'sum')
        self.sum2m_dir = os.path.join(base_dir, 'sum2m')
        self.circuit_dir = os.path.join(base_dir, 'circuit')
        
        # 確保目錄存在
        for directory in [self.user_dir, self.sum_dir, self.sum2m_dir, self.circuit_dir]:
            os.makedirs(directory, exist_ok=True)
        
        logger.debug(f"RRD Manager 初始化: {base_dir}")
    
    def _create_rrd(self, rrd_path: str, ds_definitions: List[str], 
                   rra_definitions: List[str] = None) -> bool:
        """
        建立 RRD 檔案
        
        Args:
            rrd_path: RRD 檔案路徑
            ds_definitions: DS 定義列表
            rra_definitions: RRA 定義列表，None 則使用預設
        
        Returns:
            是否成功
        """
        if os.path.exists(rrd_path):
            return True
        
        # 預設 RRA 定義
        if rra_definitions is None:
            rra_definitions = [
                'RRA:AVERAGE:0.5:1:2160',    # 20分鐘 * 2160 = 30天
                'RRA:AVERAGE:0.5:6:1460',    # 2小時 * 1460 = ~4個月
                'RRA:AVERAGE:0.5:72:1095',   # 1天 * 1095 = ~3年
                'RRA:MAX:0.5:1:2160',
                'RRA:MAX:0.5:6:1460',
                'RRA:MAX:0.5:72:1095',
            ]
        
        # 建立命令
        cmd = [
            'rrdtool', 'create', rrd_path,
            '--step', str(self.step),
            '--start', str(int(time.time()) - self.step),
        ]
        cmd.extend(ds_definitions)
        cmd.extend(rra_definitions)
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(f"建立 RRD: {rrd_path}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"建立 RRD 失敗: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"建立 RRD 異常: {e}")
            return False
    
    def _update_rrd(self, rrd_path: str, values: str, timestamp: int = None) -> bool:
        """
        更新 RRD 檔案
        
        Args:
            rrd_path: RRD 檔案路徑
            values: 更新值字串（例如: "N:1234:5678"）
            timestamp: 時間戳記，None 則使用 N
        
        Returns:
            是否成功
        """
        if not os.path.exists(rrd_path):
            logger.error(f"RRD 檔案不存在: {rrd_path}")
            return False
        
        if timestamp is None:
            update_str = f"N:{values}"
        else:
            update_str = f"{timestamp}:{values}"
        
        try:
            cmd = ['rrdtool', 'update', rrd_path, update_str]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.debug(f"更新 RRD: {os.path.basename(rrd_path)} = {update_str}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"更新 RRD 失敗: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"更新 RRD 異常: {e}")
            return False
    
    # Layer 1: User Layer
    
    def create_user_rrd(self, username: str) -> bool:
        """
        建立用戶 RRD 檔案
        
        Args:
            username: 用戶名稱
        
        Returns:
            是否成功
        """
        rrd_path = os.path.join(self.user_dir, f"{username}.rrd")
        
        ds_definitions = [
            f'DS:inbound:COUNTER:{self.heartbeat}:0:U',
            f'DS:outbound:COUNTER:{self.heartbeat}:0:U',
        ]
        
        return self._create_rrd(rrd_path, ds_definitions)
    
    def update_user_rrd(self, username: str, inbound: int, outbound: int, 
                       timestamp: int = None) -> bool:
        """
        更新用戶 RRD
        
        Args:
            username: 用戶名稱
            inbound: 入站流量（bytes）
            outbound: 出站流量（bytes）
            timestamp: 時間戳記
        
        Returns:
            是否成功
        """
        rrd_path = os.path.join(self.user_dir, f"{username}.rrd")
        
        # 確保 RRD 存在
        if not os.path.exists(rrd_path):
            self.create_user_rrd(username)
        
        return self._update_rrd(rrd_path, f"{inbound}:{outbound}", timestamp)
    
    # Layer 2: Sum Layer
    
    def create_sum_rrd(self, device_ip: str, bandwidth: str) -> bool:
        """
        建立 Sum Layer RRD 檔案
        
        Args:
            device_ip: 設備 IP
            bandwidth: 頻寬字串（例如: "102400_40960"）
        
        Returns:
            是否成功
        """
        # 清理 IP 中的點號
        ip_str = device_ip.replace('.', '_')
        rrd_filename = f"{ip_str}_{bandwidth}.rrd"
        rrd_path = os.path.join(self.sum_dir, rrd_filename)
        
        ds_definitions = [
            f'DS:inbound:COUNTER:{self.heartbeat}:0:U',
            f'DS:outbound:COUNTER:{self.heartbeat}:0:U',
            f'DS:user_count:GAUGE:{self.heartbeat}:0:U',
        ]
        
        return self._create_rrd(rrd_path, ds_definitions)
    
    def update_sum_rrd(self, device_ip: str, bandwidth: str, 
                      inbound: int, outbound: int, user_count: int,
                      timestamp: int = None) -> bool:
        """
        更新 Sum Layer RRD
        
        Args:
            device_ip: 設備 IP
            bandwidth: 頻寬字串
            inbound: 入站流量總和
            outbound: 出站流量總和
            user_count: 用戶數量
            timestamp: 時間戳記
        
        Returns:
            是否成功
        """
        ip_str = device_ip.replace('.', '_')
        rrd_filename = f"{ip_str}_{bandwidth}.rrd"
        rrd_path = os.path.join(self.sum_dir, rrd_filename)
        
        # 確保 RRD 存在
        if not os.path.exists(rrd_path):
            self.create_sum_rrd(device_ip, bandwidth)
        
        return self._update_rrd(rrd_path, f"{inbound}:{outbound}:{user_count}", timestamp)
    
    # Layer 3: Sum2m Layer
    
    def create_sum2m_rrd(self, device_ip: str) -> bool:
        """
        建立 Sum2m Layer RRD 檔案（Fair Usage Policy）
        
        Args:
            device_ip: 設備 IP
        
        Returns:
            是否成功
        """
        ip_str = device_ip.replace('.', '_')
        rrd_filename = f"{ip_str}.rrd"
        rrd_path = os.path.join(self.sum2m_dir, rrd_filename)
        
        ds_definitions = [
            f'DS:inbound:COUNTER:{self.heartbeat}:0:U',
            f'DS:outbound:COUNTER:{self.heartbeat}:0:U',
            f'DS:fup_users:GAUGE:{self.heartbeat}:0:U',
        ]
        
        # Sum2m 使用較長的保留期限
        rra_definitions = [
            'RRA:AVERAGE:0.5:1:2160',    # 20分鐘 * 2160 = 30天
            'RRA:AVERAGE:0.5:6:1460',    # 2小時 * 1460 = ~4個月
            'RRA:AVERAGE:0.5:72:1095',   # 1天 * 1095 = ~3年
            'RRA:AVERAGE:0.5:288:1095',  # 4天 * 1095 = ~12年（長期趨勢）
            'RRA:MAX:0.5:1:2160',
            'RRA:MAX:0.5:72:1095',
        ]
        
        return self._create_rrd(rrd_path, ds_definitions, rra_definitions)
    
    def update_sum2m_rrd(self, device_ip: str, inbound: int, outbound: int, 
                        fup_users: int, timestamp: int = None) -> bool:
        """
        更新 Sum2m Layer RRD
        
        Args:
            device_ip: 設備 IP
            inbound: 入站流量總和
            outbound: 出站流量總和
            fup_users: FUP 用戶數量
            timestamp: 時間戳記
        
        Returns:
            是否成功
        """
        ip_str = device_ip.replace('.', '_')
        rrd_filename = f"{ip_str}.rrd"
        rrd_path = os.path.join(self.sum2m_dir, rrd_filename)
        
        # 確保 RRD 存在
        if not os.path.exists(rrd_path):
            self.create_sum2m_rrd(device_ip)
        
        return self._update_rrd(rrd_path, f"{inbound}:{outbound}:{fup_users}", timestamp)
    
    # Layer 4: Circuit Layer
    
    def create_circuit_rrd(self, circuit_id: str) -> bool:
        """
        建立 Circuit Layer RRD 檔案
        
        Args:
            circuit_id: 電路 ID
        
        Returns:
            是否成功
        """
        rrd_filename = f"{circuit_id}.rrd"
        rrd_path = os.path.join(self.circuit_dir, rrd_filename)
        
        ds_definitions = [
            f'DS:inbound:COUNTER:{self.heartbeat}:0:U',
            f'DS:outbound:COUNTER:{self.heartbeat}:0:U',
            f'DS:device_count:GAUGE:{self.heartbeat}:0:U',
            f'DS:user_count:GAUGE:{self.heartbeat}:0:U',
        ]
        
        return self._create_rrd(rrd_path, ds_definitions)
    
    def update_circuit_rrd(self, circuit_id: str, inbound: int, outbound: int,
                          device_count: int, user_count: int,
                          timestamp: int = None) -> bool:
        """
        更新 Circuit Layer RRD
        
        Args:
            circuit_id: 電路 ID
            inbound: 入站流量總和
            outbound: 出站流量總和
            device_count: 設備數量
            user_count: 用戶數量
            timestamp: 時間戳記
        
        Returns:
            是否成功
        """
        rrd_filename = f"{circuit_id}.rrd"
        rrd_path = os.path.join(self.circuit_dir, rrd_filename)
        
        # 確保 RRD 存在
        if not os.path.exists(rrd_path):
            self.create_circuit_rrd(circuit_id)
        
        values = f"{inbound}:{outbound}:{device_count}:{user_count}"
        return self._update_rrd(rrd_path, values, timestamp)
    
    def get_rrd_info(self, rrd_path: str) -> Optional[dict]:
        """
        取得 RRD 資訊
        
        Args:
            rrd_path: RRD 檔案路徑
        
        Returns:
            RRD 資訊字典
        """
        if not os.path.exists(rrd_path):
            return None
        
        try:
            cmd = ['rrdtool', 'info', rrd_path]
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # 解析輸出
            info = {}
            for line in result.stdout.split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    info[key.strip()] = value.strip()
            
            return info
        except Exception as e:
            logger.error(f"取得 RRD 資訊失敗: {e}")
            return None


# 測試程式
if __name__ == '__main__':
    import sys
    
    # 設定日誌
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 測試目錄
    test_dir = '/tmp/rrd_test'
    
    print(f"\n=== RRD Manager 測試 ===")
    print(f"測試目錄: {test_dir}\n")
    
    # 建立 RRD Manager
    rrd = RRDManager(test_dir)
    
    # 測試 User Layer
    print("=== 測試 User Layer ===")
    username = "test_user_001"
    if rrd.create_user_rrd(username):
        print(f"✓ 建立用戶 RRD: {username}")
        
        # 更新資料
        if rrd.update_user_rrd(username, 1000000, 500000):
            print(f"✓ 更新用戶 RRD: {username}")
        else:
            print(f"✗ 更新失敗")
    
    # 測試 Sum Layer
    print("\n=== 測試 Sum Layer ===")
    device_ip = "192.168.1.1"
    bandwidth = "102400_40960"
    if rrd.create_sum_rrd(device_ip, bandwidth):
        print(f"✓ 建立 Sum RRD: {device_ip}_{bandwidth}")
        
        if rrd.update_sum_rrd(device_ip, bandwidth, 5000000, 2500000, 50):
            print(f"✓ 更新 Sum RRD")
    
    # 測試 Sum2m Layer
    print("\n=== 測試 Sum2m Layer ===")
    if rrd.create_sum2m_rrd(device_ip):
        print(f"✓ 建立 Sum2m RRD: {device_ip}")
        
        if rrd.update_sum2m_rrd(device_ip, 10000000, 5000000, 100):
            print(f"✓ 更新 Sum2m RRD")
    
    # 測試 Circuit Layer
    print("\n=== 測試 Circuit Layer ===")
    circuit_id = "TEST_CIRCUIT_001"
    if rrd.create_circuit_rrd(circuit_id):
        print(f"✓ 建立 Circuit RRD: {circuit_id}")
        
        if rrd.update_circuit_rrd(circuit_id, 20000000, 10000000, 5, 250):
            print(f"✓ 更新 Circuit RRD")
    
    # 顯示建立的檔案
    print("\n=== 建立的 RRD 檔案 ===")
    for root, dirs, files in os.walk(test_dir):
        level = root.replace(test_dir, '').count(os.sep)
        indent = ' ' * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            if file.endswith('.rrd'):
                file_path = os.path.join(root, file)
                size = os.path.getsize(file_path)
                print(f"{subindent}{file} ({size} bytes)")
    
    print("\n✓ RRD Manager 測試完成")
    print(f"\n測試檔案位於: {test_dir}")
