#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RRD Helper - RRD 輔助工具
提供統一的 RRD 建立、更新、讀取功能

支援四層 RRD 結構:
1. User Layer: 個別用戶（VLAN）
2. Sum Layer: 速率彙總（無限制）
3. Sum2M Layer: 速率彙總（Fair Usage）
4. Circuit Layer: Circuit 彙總 ⭐
"""

import os
import time
import rrdtool
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class RRDHelper:
    """RRD 輔助工具類別"""
    
    # RRD Step (20 分鐘)
    RRD_STEP = 1200
    
    # RRA 定義
    RRA_DEFINITIONS = [
        # 20 分鐘粒度，保留 62 天
        'RRA:AVERAGE:0.5:1:4465',     # 1200s * 4465 = ~62 days
        'RRA:MAX:0.5:1:4465',
        # 1 天粒度，保留 2 年
        'RRA:AVERAGE:0.5:72:730',     # 72 * 1200s = 1 day, 730 days
        'RRA:MAX:0.5:72:730',
        # 1 週粒度，保留 5 年
        'RRA:AVERAGE:0.5:504:260',    # 504 * 1200s = 1 week, 260 weeks
        'RRA:MAX:0.5:504:260'
    ]
    
    def __init__(self, base_dir: str = "/home/bulks_data"):
        """
        初始化 RRD Helper
        
        Args:
            base_dir: RRD 基礎目錄
        """
        self.base_dir = Path(base_dir)
        
        # 建立子目錄
        self.user_dir = self.base_dir
        self.sum_dir = self.base_dir / "sum"
        self.sum2m_dir = self.base_dir / "sum2m"
        self.circuit_dir = self.base_dir / "circuit"
    
    # ========== Layer 1: User VLAN RRD ==========
    
    def get_user_rrd_path(self, bras_ip: str, slot: int, port: int,
                          download_kbps: int, upload_kbps: int, vlan: int) -> Path:
        """
        取得個別用戶 RRD 路徑
        
        格式: {IP}/{IP}_{slot}_{port}_{download}_{upload}_{vlan}.rrd
        """
        filename = f"{bras_ip}_{slot}_{port}_{download_kbps}_{upload_kbps}_{vlan}.rrd"
        return self.user_dir / bras_ip / filename
    
    def create_user_rrd(self, rrd_path: Path, download_kbps: int, upload_kbps: int) -> bool:
        """
        建立個別用戶 RRD (COUNTER)
        
        Args:
            rrd_path: RRD 檔案路徑
            download_kbps: 下載速率 (kbps)
            upload_kbps: 上傳速率 (kbps)
            
        Returns:
            True if created or exists, False if failed
        """
        if rrd_path.exists():
            return True
        
        # 建立目錄
        rrd_path.parent.mkdir(parents=True, exist_ok=True)
        
        # DS 名稱
        ds_name = f"{download_kbps}_{upload_kbps}"
        
        # 最大值 (bits/s)
        max_value = (download_kbps * 1024) + 10240
        
        try:
            rrdtool.create(
                str(rrd_path),
                '--step', str(self.RRD_STEP),
                '--start', str(int(time.time()) - self.RRD_STEP),
                f'DS:{ds_name}:COUNTER:{self.RRD_STEP * 2}:0:{max_value}',
                *self.RRA_DEFINITIONS
            )
            return True
        except Exception as e:
            print(f"建立用戶 RRD 失敗: {e}")
            return False
    
    def update_user_rrd(self, rrd_path: Path, timestamp: int, counter_bits: int) -> bool:
        """
        更新個別用戶 RRD
        
        Args:
            rrd_path: RRD 檔案路徑
            timestamp: 時間戳記
            counter_bits: Counter 值 (bits)
        """
        try:
            rrdtool.update(str(rrd_path), f"{timestamp}:{int(counter_bits)}")
            return True
        except Exception as e:
            if 'illegal attempt to update' not in str(e):
                print(f"更新用戶 RRD 失敗: {e}")
            return False
    
    # ========== Layer 2 & 3: Sum RRD ==========
    
    def get_sum_rrd_path(self, sum_dir: Path, bras_ip: str, slot: int, port: int,
                         download_kbps: int, upload_kbps: int) -> Path:
        """
        取得彙總 RRD 路徑
        
        格式: sum/{IP}/{IP}_{slot}_{port}_{download}_{upload}_sum.rrd
        """
        filename = f"{bras_ip}_{slot}_{port}_{download_kbps}_{upload_kbps}_sum.rrd"
        return sum_dir / bras_ip / filename
    
    def create_sum_rrd(self, rrd_path: Path, speed_key: str) -> bool:
        """
        建立彙總 RRD (GAUGE)
        
        Args:
            rrd_path: RRD 檔案路徑
            speed_key: 速率鍵值 (download_upload)
        """
        if rrd_path.exists():
            return True
        
        rrd_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            rrdtool.create(
                str(rrd_path),
                '--step', str(self.RRD_STEP),
                '--start', str(int(time.time()) - self.RRD_STEP),
                f'DS:{speed_key}:GAUGE:2400:0:U',
                *self.RRA_DEFINITIONS
            )
            return True
        except Exception as e:
            print(f"建立彙總 RRD 失敗: {e}")
            return False
    
    def update_sum_rrd(self, rrd_path: Path, timestamp: int, rate_bps: int) -> bool:
        """
        更新彙總 RRD
        
        Args:
            rrd_path: RRD 檔案路徑
            timestamp: 時間戳記
            rate_bps: 速率 (bits/s)
        """
        try:
            rrdtool.update(str(rrd_path), f"{timestamp}:{int(rate_bps)}")
            return True
        except Exception as e:
            if 'illegal attempt to update' not in str(e):
                print(f"更新彙總 RRD 失敗: {e}")
            return False
    
    # ========== Layer 4: Circuit RRD ⭐ ==========
    
    def get_circuit_rrd_path(self, bras_ip: str, interface: str) -> Path:
        """
        取得 Circuit RRD 路徑
        
        格式: circuit/{IP}/{IP}_{interface}_circuit.rrd
        
        Args:
            bras_ip: BRAS IP
            interface: 介面名稱 (ge-1-2 或 xe-0-0-1)
        
        範例:
            - 61.64.191.1_ge-1-2_circuit.rrd
            - 10.1.1.1_xe-0-0-1_circuit.rrd
        """
        # 將介面名稱中的 / 替換為 -
        safe_interface = interface.replace('/', '-')
        filename = f"{bras_ip}_{safe_interface}_circuit.rrd"
        return self.circuit_dir / bras_ip / filename
    
    def create_circuit_rrd(self, rrd_path: Path, bandwidth_mbps: Optional[int] = None) -> bool:
        """
        建立 Circuit RRD (GAUGE)
        
        Args:
            rrd_path: RRD 檔案路徑
            bandwidth_mbps: 頻寬 (Mbps)，None 表示不限制
        
        DS:
            - in_bits: 流入位元數 (bits/s)
            - out_bits: 流出位元數 (bits/s)
            - vlan_count: VLAN 數量 (每次收集時計算)
        """
        if rrd_path.exists():
            return True
        
        rrd_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 最大值（如果有設定頻寬）
        max_value = (bandwidth_mbps * 1024 * 1024) if bandwidth_mbps else 'U'
        
        try:
            rrdtool.create(
                str(rrd_path),
                '--step', str(self.RRD_STEP),
                '--start', str(int(time.time()) - self.RRD_STEP),
                f'DS:in_bits:GAUGE:2400:0:{max_value}',
                f'DS:out_bits:GAUGE:2400:0:{max_value}',
                f'DS:vlan_count:GAUGE:2400:0:U',
                *self.RRA_DEFINITIONS
            )
            return True
        except Exception as e:
            print(f"建立 Circuit RRD 失敗: {e}")
            return False
    
    def update_circuit_rrd(self, rrd_path: Path, timestamp: int,
                          in_bits: int, out_bits: int, vlan_count: int) -> bool:
        """
        更新 Circuit RRD
        
        Args:
            rrd_path: RRD 檔案路徑
            timestamp: 時間戳記
            in_bits: 流入位元數 (bits/s)
            out_bits: 流出位元數 (bits/s)
            vlan_count: VLAN 數量
        """
        try:
            rrdtool.update(
                str(rrd_path),
                f"{timestamp}:{int(in_bits)}:{int(out_bits)}:{int(vlan_count)}"
            )
            return True
        except Exception as e:
            if 'illegal attempt to update' not in str(e):
                print(f"更新 Circuit RRD 失敗: {e}")
            return False
    
    # ========== 讀取 RRD 資料 ==========
    
    def read_rrd_rate(self, rrd_path: Path, timestamp: int) -> int:
        """
        從 RRD 讀取速率
        
        Args:
            rrd_path: RRD 檔案路徑
            timestamp: 時間戳記
            
        Returns:
            速率 (bits/s)
        """
        try:
            start_time = timestamp - 5
            end_time = timestamp + self.RRD_STEP
            
            result = rrdtool.fetch(
                str(rrd_path),
                'AVERAGE',
                '--start', str(start_time),
                '--end', str(end_time)
            )
            
            (fetch_start, fetch_end, fetch_step), ds_names, data = result
            
            # 從後往前找第一個非 None 值
            for row in reversed(data):
                if row[0] is not None:
                    return int(row[0] + 0.9)
            
            return 0
            
        except Exception as e:
            return 0
    
    def read_rrd_data(self, rrd_path: Path, start_time: str, end_time: str = 'now',
                      cf: str = 'AVERAGE') -> List[Tuple]:
        """
        讀取 RRD 資料
        
        Args:
            rrd_path: RRD 檔案路徑
            start_time: 開始時間 ('-1d', '-1w', '-1m' 或 timestamp)
            end_time: 結束時間 ('now' 或 timestamp)
            cf: Consolidation Function ('AVERAGE' 或 'MAX')
            
        Returns:
            [(timestamp, value1, value2, ...), ...]
        """
        try:
            result = rrdtool.fetch(
                str(rrd_path),
                cf,
                '--start', str(start_time),
                '--end', str(end_time)
            )
            
            (fetch_start, fetch_end, fetch_step), ds_names, data = result
            
            # 組合時間戳記和資料
            current_time = fetch_start
            result_data = []
            
            for row in data:
                result_data.append((current_time, *row))
                current_time += fetch_step
            
            return result_data
            
        except Exception as e:
            print(f"讀取 RRD 資料失敗: {e}")
            return []
    
    # ========== 掃描 RRD 檔案 ==========
    
    def scan_user_rrds(self, bras_ip: Optional[str] = None) -> List[Path]:
        """
        掃描所有用戶 RRD
        
        Args:
            bras_ip: 只掃描指定 IP，None 表示全部
        """
        if bras_ip:
            search_dir = self.user_dir / bras_ip
            if not search_dir.exists():
                return []
            return list(search_dir.glob("*.rrd"))
        else:
            # 掃描所有 IP 目錄
            all_rrds = []
            for ip_dir in self.user_dir.glob("*"):
                if ip_dir.is_dir() and ip_dir.name not in ['sum', 'sum2m', 'circuit']:
                    all_rrds.extend(ip_dir.glob("*.rrd"))
            return all_rrds
    
    def scan_circuit_rrds(self, bras_ip: Optional[str] = None) -> List[Path]:
        """
        掃描所有 Circuit RRD
        
        Args:
            bras_ip: 只掃描指定 IP，None 表示全部
        """
        if bras_ip:
            search_dir = self.circuit_dir / bras_ip
            if not search_dir.exists():
                return []
            return list(search_dir.glob("*_circuit.rrd"))
        else:
            all_rrds = []
            for ip_dir in self.circuit_dir.glob("*"):
                if ip_dir.is_dir():
                    all_rrds.extend(ip_dir.glob("*_circuit.rrd"))
            return all_rrds
    
    # ========== 解析 RRD 檔名 ==========
    
    def parse_user_rrd(self, rrd_path: Path) -> Dict:
        """
        解析用戶 RRD 檔名
        
        格式: {IP}_{slot}_{port}_{download}_{upload}_{vlan}.rrd
        
        Returns:
            {
                'bras_ip': str,
                'slot': int,
                'port': int,
                'download_kbps': int,
                'upload_kbps': int,
                'vlan': int
            }
        """
        filename = rrd_path.stem  # 去除 .rrd
        parts = filename.split('_')
        
        if len(parts) != 6:
            raise ValueError(f"無效的用戶 RRD 檔名: {filename}")
        
        return {
            'bras_ip': parts[0],
            'slot': int(parts[1]),
            'port': int(parts[2]),
            'download_kbps': int(parts[3]),
            'upload_kbps': int(parts[4]),
            'vlan': int(parts[5])
        }
    
    def parse_circuit_rrd(self, rrd_path: Path) -> Tuple[str, str]:
        """
        解析 Circuit RRD 檔名
        
        格式: {IP}_{interface}_circuit.rrd
        
        Returns:
            (bras_ip, interface)
        
        範例:
            '61.64.191.1_ge-1-2_circuit.rrd' -> ('61.64.191.1', 'ge-1-2')
        """
        filename = rrd_path.stem  # 去除 .rrd
        
        # 移除 _circuit 後綴
        if not filename.endswith('_circuit'):
            raise ValueError(f"無效的 Circuit RRD 檔名: {filename}")
        
        name = filename[:-8]  # 移除 '_circuit'
        
        # 分離 IP 和介面
        # IP 格式: xxx.xxx.xxx.xxx
        parts = name.split('_')
        if len(parts) < 2:
            raise ValueError(f"無效的 Circuit RRD 檔名: {filename}")
        
        # 第一部分是 IP（可能包含 .）
        # 從後往前找到第一個非數字部分
        ip_parts = []
        interface_parts = []
        
        in_interface = False
        for part in parts:
            if not in_interface and part.replace('.', '').replace('-', '').isdigit():
                ip_parts.append(part)
            else:
                in_interface = True
                interface_parts.append(part)
        
        bras_ip = '_'.join(ip_parts) if ip_parts else parts[0]
        interface = '_'.join(interface_parts) if interface_parts else '_'.join(parts[1:])
        
        return bras_ip, interface


def main():
    """測試主程式"""
    helper = RRDHelper("/tmp/test_rrd")
    
    print("=" * 70)
    print("RRD Helper 測試")
    print("=" * 70)
    
    # 測試 1: 建立用戶 RRD
    print("\n測試 1: 建立用戶 RRD")
    user_rrd = helper.get_user_rrd_path("127.0.0.1", 1, 2, 35840, 6144, 3490)
    print(f"路徑: {user_rrd}")
    
    if helper.create_user_rrd(user_rrd, 35840, 6144):
        print("✓ 建立成功")
    
    # 測試 2: 建立 Circuit RRD
    print("\n測試 2: 建立 Circuit RRD")
    circuit_rrd = helper.get_circuit_rrd_path("127.0.0.1", "ge-1-2")
    print(f"路徑: {circuit_rrd}")
    
    if helper.create_circuit_rrd(circuit_rrd, bandwidth_mbps=1000):
        print("✓ 建立成功")
    
    # 測試 3: 更新 RRD
    print("\n測試 3: 更新 RRD")
    timestamp = int(time.time())
    timestamp = timestamp - (timestamp % 1200)
    
    if helper.update_circuit_rrd(circuit_rrd, timestamp, 100000000, 50000000, 10):
        print("✓ 更新成功")
    
    # 測試 4: 解析檔名
    print("\n測試 4: 解析檔名")
    parsed = helper.parse_user_rrd(user_rrd)
    print(f"解析結果: {parsed}")
    
    bras_ip, interface = helper.parse_circuit_rrd(circuit_rrd)
    print(f"Circuit 解析: IP={bras_ip}, Interface={interface}")
    
    print("\n" + "=" * 70)
    print("測試完成")


if __name__ == "__main__":
    main()
