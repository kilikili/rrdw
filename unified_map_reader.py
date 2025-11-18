#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Map Reader
統一 Map File 讀取器（基於 E320 格式）

所有設備（E320/ACX/MX960/MX240）使用統一的 Map File 格式
"""

import os
import glob
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class MapUser:
    """Map File 使用者資料（統一格式）"""
    user_code: str          # 使用者代碼
    download_kbps: int      # 下載速率 (Kbps)
    upload_kbps: int        # 上傳速率 (Kbps)
    ifindex: int            # SNMP ifindex
    vlan: int               # VLAN ID
    
    @property
    def speed_key(self) -> str:
        """速率鍵值"""
        return f"{self.download_kbps}_{self.upload_kbps}"
    
    def get_rrd_path(self, base_dir: str, bras_ip: str, slot: int, port: int) -> str:
        """
        取得 RRD 檔案路徑
        格式: {base_dir}/{IP}/{IP}_{slot}_{port}_{download}_{upload}_{vlan}.rrd
        """
        filename = f"{bras_ip}_{slot}_{port}_{self.download_kbps}_{self.upload_kbps}_{self.vlan}.rrd"
        return os.path.join(base_dir, bras_ip, filename)


@dataclass
class BRASDevice:
    """BRAS 設備資訊"""
    bras_ip: str            # BRAS IP
    device_type: str        # 設備類型 (E320/ACX/MX960/MX240)
    hostname: str           # 主機名稱
    area: str              # 區域
    bandwidth_mbps: int    # 頻寬上限 (Mbps)


class UnifiedMapReader:
    """統一 Map File 讀取器"""
    
    def __init__(self, map_dir: str = "maps", devices_file: str = "BRAS-Devices.txt"):
        """
        初始化讀取器
        
        Args:
            map_dir: Map File 目錄
            devices_file: 設備清單檔案
        """
        self.map_dir = map_dir
        self.devices_file = devices_file
        
        # 載入設備清單
        self.devices = self.load_devices()
    
    def load_devices(self) -> Dict[str, BRASDevice]:
        """
        載入 BRAS 設備清單
        
        格式: BRAS_IP,設備類型,主機名稱,區域,頻寬上限(Mbps)
        
        Returns:
            {bras_ip: BRASDevice}
        """
        devices = {}
        
        if not os.path.exists(self.devices_file):
            print(f"警告: 找不到設備清單檔案 {self.devices_file}")
            return devices
        
        with open(self.devices_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split(',')
                if len(parts) >= 5:
                    device = BRASDevice(
                        bras_ip=parts[0],
                        device_type=parts[1],
                        hostname=parts[2],
                        area=parts[3],
                        bandwidth_mbps=int(parts[4]) if parts[4].isdigit() else 1000
                    )
                    devices[device.bras_ip] = device
        
        return devices
    
    def get_map_file_path(self, bras_ip: str, slot: int, port: int) -> Optional[str]:
        """
        取得 Map File 路徑
        
        格式: map_{IP}_{slot}_{port}.txt
        
        Args:
            bras_ip: BRAS IP
            slot: 插槽
            port: 埠號
            
        Returns:
            Map File 路徑，不存在則返回 None
        """
        filename = f"map_{bras_ip}_{slot}_{port}.txt"
        filepath = os.path.join(self.map_dir, filename)
        
        if os.path.exists(filepath):
            return filepath
        
        return None
    
    def load_map_file(self, bras_ip: str, slot: int, port: int) -> List[MapUser]:
        """
        載入 Map File（統一格式）
        
        格式: 使用者代碼,下載速率,上傳速率,ifindex,VLAN
        
        Args:
            bras_ip: BRAS IP
            slot: 插槽
            port: 埠號
            
        Returns:
            MapUser 列表
        """
        map_file = self.get_map_file_path(bras_ip, slot, port)
        
        if not map_file:
            print(f"找不到 Map File: {bras_ip} slot={slot} port={port}")
            return []
        
        users = []
        line_number = 0
        
        with open(map_file, 'r', encoding='utf-8') as f:
            for line in f:
                line_number += 1
                line = line.strip()
                
                # 跳過空行和註解
                if not line or line.startswith('#'):
                    continue
                
                # 解析欄位
                parts = line.split(',')
                if len(parts) < 5:
                    print(f"警告: 第 {line_number} 行格式錯誤（欄位不足）: {line}")
                    continue
                
                try:
                    user = MapUser(
                        user_code=parts[0].strip(),
                        download_kbps=int(parts[1]),
                        upload_kbps=int(parts[2]),
                        ifindex=int(parts[3]),
                        vlan=int(parts[4])
                    )
                    users.append(user)
                    
                except ValueError as e:
                    print(f"警告: 第 {line_number} 行解析失敗: {e}")
                    continue
        
        print(f"載入 {len(users)} 個使用者: {map_file}")
        return users
    
    def get_all_map_files(self) -> List[Tuple[str, int, int]]:
        """
        取得所有 Map File
        
        Returns:
            [(bras_ip, slot, port), ...]
        """
        pattern = os.path.join(self.map_dir, "map_*.txt")
        map_files = glob.glob(pattern)
        
        result = []
        
        for map_file in map_files:
            # 解析檔名: map_61.64.191.1_1_2.txt
            basename = os.path.basename(map_file)
            parts = basename.replace('map_', '').replace('.txt', '').split('_')
            
            if len(parts) < 6:  # IP 有 4 部分 + slot + port
                continue
            
            try:
                # IP 部分
                bras_ip = '.'.join(parts[0:4])
                
                # slot 和 port
                slot = int(parts[4])
                port = int(parts[5])
                
                result.append((bras_ip, slot, port))
                
            except ValueError:
                continue
        
        return result
    
    def get_device_type(self, bras_ip: str) -> str:
        """
        取得設備類型
        
        Args:
            bras_ip: BRAS IP
            
        Returns:
            設備類型 (E320/ACX/MX960/MX240)
        """
        if bras_ip in self.devices:
            return self.devices[bras_ip].device_type
        return "Unknown"
    
    def get_device_info(self, bras_ip: str) -> Optional[BRASDevice]:
        """
        取得設備資訊
        
        Args:
            bras_ip: BRAS IP
            
        Returns:
            BRASDevice 或 None
        """
        return self.devices.get(bras_ip)
    
    def get_users_by_speed(self, users: List[MapUser]) -> Dict[str, List[MapUser]]:
        """
        依速率方案分組
        
        Args:
            users: MapUser 列表
            
        Returns:
            {speed_key: [MapUser]}
        """
        groups = {}
        
        for user in users:
            if user.speed_key not in groups:
                groups[user.speed_key] = []
            groups[user.speed_key].append(user)
        
        return groups
    
    def get_all_ifindexes(self, users: List[MapUser]) -> List[int]:
        """
        取得所有 ifindex（不重複）
        
        Args:
            users: MapUser 列表
            
        Returns:
            ifindex 列表
        """
        return list(set(user.ifindex for user in users))
    
    def validate_map_file(self, bras_ip: str, slot: int, port: int) -> Tuple[bool, List[str]]:
        """
        驗證 Map File 格式
        
        Args:
            bras_ip: BRAS IP
            slot: 插槽
            port: 埠號
            
        Returns:
            (是否有效, 錯誤訊息列表)
        """
        errors = []
        
        # 檢查檔案是否存在
        map_file = self.get_map_file_path(bras_ip, slot, port)
        if not map_file:
            errors.append(f"找不到 Map File: map_{bras_ip}_{slot}_{port}.txt")
            return False, errors
        
        # 載入並驗證
        try:
            users = self.load_map_file(bras_ip, slot, port)
            
            if not users:
                errors.append("Map File 沒有有效的使用者資料")
            
            # 檢查重複的 VLAN
            vlans = [u.vlan for u in users]
            if len(vlans) != len(set(vlans)):
                errors.append("存在重複的 VLAN")
            
            # 檢查重複的 ifindex
            ifindexes = [u.ifindex for u in users]
            if len(ifindexes) != len(set(ifindexes)):
                errors.append("存在重複的 ifindex")
            
        except Exception as e:
            errors.append(f"驗證失敗: {e}")
        
        return len(errors) == 0, errors
    
    def print_statistics(self):
        """印出統計資訊"""
        print("=" * 70)
        print("BRAS 設備統計")
        print("=" * 70)
        
        if not self.devices:
            print("未載入任何設備")
            return
        
        # 依設備類型分組
        type_groups = {}
        for device in self.devices.values():
            if device.device_type not in type_groups:
                type_groups[device.device_type] = []
            type_groups[device.device_type].append(device)
        
        print(f"總設備數: {len(self.devices)}")
        print()
        
        for device_type in sorted(type_groups.keys()):
            devices = type_groups[device_type]
            print(f"{device_type}:")
            for device in devices:
                print(f"  - {device.bras_ip:15s} {device.hostname:20s} {device.area:10s} {device.bandwidth_mbps:5d} Mbps")
        
        print("=" * 70)
        
        # Map File 統計
        map_files = self.get_all_map_files()
        print(f"\n找到 {len(map_files)} 個 Map File")
        
        for bras_ip, slot, port in sorted(map_files):
            device = self.get_device_info(bras_ip)
            device_type = device.device_type if device else "Unknown"
            users = self.load_map_file(bras_ip, slot, port)
            
            print(f"  - {bras_ip:15s} slot={slot} port={port} {device_type:6s} {len(users):4d} users")
        
        print("=" * 70)


def main():
    """主程式"""
    import argparse
    
    parser = argparse.ArgumentParser(description='統一 Map File 讀取器')
    parser.add_argument('--map-dir', default='maps', help='Map File 目錄')
    parser.add_argument('--devices', default='BRAS-Devices.txt', help='設備清單檔案')
    parser.add_argument('--bras-ip', help='BRAS IP')
    parser.add_argument('--slot', type=int, help='插槽編號')
    parser.add_argument('--port', type=int, help='埠號')
    parser.add_argument('--validate', action='store_true', help='驗證 Map File')
    parser.add_argument('--statistics', action='store_true', help='顯示統計')
    
    args = parser.parse_args()
    
    # 初始化讀取器
    reader = UnifiedMapReader(args.map_dir, args.devices)
    
    if args.statistics:
        # 顯示統計
        reader.print_statistics()
    
    elif args.bras_ip and args.slot is not None and args.port is not None:
        # 載入指定的 Map File
        print(f"載入 Map File: {args.bras_ip} slot={args.slot} port={args.port}")
        print("=" * 70)
        
        users = reader.load_map_file(args.bras_ip, args.slot, args.port)
        
        if users:
            # 顯示設備資訊
            device = reader.get_device_info(args.bras_ip)
            if device:
                print(f"設備類型: {device.device_type}")
                print(f"主機名稱: {device.hostname}")
                print(f"區域: {device.area}")
                print(f"頻寬上限: {device.bandwidth_mbps} Mbps")
                print()
            
            # 顯示使用者統計
            print(f"使用者數: {len(users)}")
            
            # 速率分組
            speed_groups = reader.get_users_by_speed(users)
            print(f"速率方案: {len(speed_groups)} 種")
            
            for speed_key, group_users in sorted(speed_groups.items()):
                download, upload = map(int, speed_key.split('_'))
                print(f"  {speed_key} ({download//1024}M/{upload//1024}M): {len(group_users)} 用戶")
            
            # 顯示範例
            print(f"\n前 5 個使用者:")
            for user in users[:5]:
                print(f"  {user.user_code:15s} {user.speed_key:15s} ifindex={user.ifindex:10d} vlan={user.vlan}")
            
            # 驗證
            if args.validate:
                print(f"\n驗證 Map File:")
                is_valid, errors = reader.validate_map_file(args.bras_ip, args.slot, args.port)
                
                if is_valid:
                    print("✓ 格式正確")
                else:
                    print("✗ 格式錯誤:")
                    for error in errors:
                        print(f"  - {error}")
        else:
            print("未找到使用者資料")
    
    else:
        # 顯示所有 Map File
        map_files = reader.get_all_map_files()
        
        print(f"找到 {len(map_files)} 個 Map File:")
        print("=" * 70)
        
        for bras_ip, slot, port in sorted(map_files):
            device = reader.get_device_info(bras_ip)
            device_type = device.device_type if device else "Unknown"
            users = reader.load_map_file(bras_ip, slot, port)
            
            print(f"{bras_ip:15s} slot={slot:2d} port={port:2d} {device_type:6s} {len(users):4d} users")
        
        print("=" * 70)


if __name__ == "__main__":
    main()
