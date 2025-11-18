#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Map File Reader - 相容於實際 E320 系統
讀取和解析 maps/map_{IP}.txt 檔案

格式: user_code,slot_port_vpi_vci,download_upload,ifindex
範例: 0989703334,1_2_0_3490,35840_6144,587247394
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path


@dataclass
class UserMapping:
    """使用者對應資訊"""
    user_code: str          # 用戶代碼
    slot: int              # 插槽
    port: int              # 埠號
    vpi: int               # VPI
    vci: int               # VCI (也是 VLAN)
    download_kbps: int     # 下載速率 (kbps)
    upload_kbps: int       # 上傳速率 (kbps)
    ifindex: int           # SNMP interface index
    
    @property
    def vlan(self) -> int:
        """VLAN ID (使用 VCI 值)"""
        return self.vci
    
    @property
    def speed_key(self) -> str:
        """速率鍵值 (用於分組)"""
        return f"{self.download_kbps}_{self.upload_kbps}"
    
    @property
    def interface_id(self) -> str:
        """介面識別 (slot_port_vpi_vci)"""
        return f"{self.slot}_{self.port}_{self.vpi}_{self.vci}"
    
    def get_rrd_filename(self, bras_ip: str) -> str:
        """
        取得 RRD 檔案名稱
        格式: {IP}_{slot}_{port}_{download}_{upload}_{vlan}.rrd
        """
        return f"{bras_ip}_{self.slot}_{self.port}_{self.download_kbps}_{self.upload_kbps}_{self.vlan}.rrd"
    
    def get_rrd_path(self, base_dir: str, bras_ip: str) -> str:
        """
        取得完整 RRD 路徑
        格式: {base_dir}/{IP}/{IP}_{slot}_{port}_{download}_{upload}_{vlan}.rrd
        """
        filename = self.get_rrd_filename(bras_ip)
        return os.path.join(base_dir, bras_ip, filename)


class MapFileReader:
    """Map File 讀取器"""
    
    def __init__(self, map_dir: str = "maps"):
        """
        初始化讀取器
        
        Args:
            map_dir: Map 檔案目錄
        """
        self.map_dir = Path(map_dir)
        self.users: Dict[str, List[UserMapping]] = {}  # {bras_ip: [UserMapping]}
        
    def get_map_file_path(self, bras_ip: str) -> Path:
        """取得 Map 檔案路徑"""
        return self.map_dir / f"map_{bras_ip}.txt"
    
    def load_map_file(self, bras_ip: str, slot: Optional[int] = None, port: Optional[int] = None) -> List[UserMapping]:
        """
        載入指定 BRAS IP 的 Map 檔案
        
        Args:
            bras_ip: BRAS IP 位址
            slot: 篩選特定 slot (選用)
            port: 篩選特定 port (選用)
            
        Returns:
            UserMapping 列表
        """
        map_file = self.get_map_file_path(bras_ip)
        
        if not map_file.exists():
            print(f"警告：Map 檔案不存在: {map_file}")
            return []
        
        users = []
        line_number = 0
        
        with open(map_file, 'r', encoding='utf-8') as f:
            for line in f:
                line_number += 1
                line = line.strip()
                
                # 跳過註解和空行
                if not line or line.startswith('#'):
                    continue
                
                # 解析資料行
                try:
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) != 4:
                        print(f"警告：第 {line_number} 行欄位數量錯誤，跳過: {line}")
                        continue
                    
                    user_code = parts[0]
                    interface_id = parts[1]
                    speed_spec = parts[2]
                    ifindex_str = parts[3]
                    
                    # 解析 slot_port_vpi_vci
                    interface_parts = interface_id.split('_')
                    if len(interface_parts) != 4:
                        print(f"警告：第 {line_number} 行介面格式錯誤，跳過: {interface_id}")
                        continue
                    
                    user_slot = int(interface_parts[0])
                    user_port = int(interface_parts[1])
                    vpi = int(interface_parts[2])
                    vci = int(interface_parts[3])
                    
                    # 篩選 slot/port (如果指定)
                    if slot is not None and user_slot != slot:
                        continue
                    if port is not None and user_port != port:
                        continue
                    
                    # 解析速率 (download_upload)
                    speed_parts = speed_spec.split('_')
                    if len(speed_parts) != 2:
                        print(f"警告：第 {line_number} 行速率格式錯誤，跳過: {speed_spec}")
                        continue
                    
                    download_kbps = int(speed_parts[0])
                    upload_kbps = int(speed_parts[1])
                    
                    # 解析 ifindex
                    ifindex = int(ifindex_str)
                    
                    # 建立 UserMapping
                    user = UserMapping(
                        user_code=user_code,
                        slot=user_slot,
                        port=user_port,
                        vpi=vpi,
                        vci=vci,
                        download_kbps=download_kbps,
                        upload_kbps=upload_kbps,
                        ifindex=ifindex
                    )
                    
                    users.append(user)
                    
                except (ValueError, IndexError) as e:
                    print(f"警告：第 {line_number} 行解析失敗，跳過: {line}")
                    print(f"  錯誤: {e}")
                    continue
        
        # 快取結果
        self.users[bras_ip] = users
        
        return users
    
    def get_users_by_speed(self, users: List[UserMapping]) -> Dict[str, List[UserMapping]]:
        """
        依速率分組使用者
        
        Args:
            users: UserMapping 列表
            
        Returns:
            {speed_key: [UserMapping]}
        """
        speed_groups = {}
        
        for user in users:
            speed_key = user.speed_key
            if speed_key not in speed_groups:
                speed_groups[speed_key] = []
            speed_groups[speed_key].append(user)
        
        return speed_groups
    
    def get_all_ifindexes(self, users: List[UserMapping]) -> List[int]:
        """取得所有 ifindex"""
        return [user.ifindex for user in users]
    
    def validate_map_file(self, bras_ip: str) -> tuple[bool, List[str]]:
        """
        驗證 Map 檔案格式
        
        Returns:
            (是否有效, 錯誤訊息列表)
        """
        map_file = self.get_map_file_path(bras_ip)
        
        if not map_file.exists():
            return False, [f"Map 檔案不存在: {map_file}"]
        
        errors = []
        line_number = 0
        
        with open(map_file, 'r', encoding='utf-8') as f:
            for line in f:
                line_number += 1
                line = line.strip()
                
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split(',')
                
                # 檢查欄位數量
                if len(parts) != 4:
                    errors.append(f"第 {line_number} 行：欄位數量錯誤 (應為 4，實際 {len(parts)})")
                    continue
                
                user_code, interface_id, speed_spec, ifindex_str = parts
                
                # 檢查 interface_id 格式 (slot_port_vpi_vci)
                if '_' not in interface_id:
                    errors.append(f"第 {line_number} 行：介面格式應使用底線分隔: {interface_id}")
                else:
                    interface_parts = interface_id.split('_')
                    if len(interface_parts) != 4:
                        errors.append(f"第 {line_number} 行：介面應為 4 個部分 (slot_port_vpi_vci): {interface_id}")
                    else:
                        for i, part in enumerate(interface_parts):
                            if not part.isdigit():
                                errors.append(f"第 {line_number} 行：介面部分 {i+1} 應為數字: {part}")
                
                # 檢查速率格式 (download_upload)
                if '_' not in speed_spec:
                    errors.append(f"第 {line_number} 行：速率格式應使用底線分隔: {speed_spec}")
                    # 檢查是否誤用斜線
                    if '/' in speed_spec:
                        errors.append(f"  提示：不要使用斜線 (/)，應使用底線 (_)")
                else:
                    speed_parts = speed_spec.split('_')
                    if len(speed_parts) != 2:
                        errors.append(f"第 {line_number} 行：速率應為 2 個部分 (download_upload): {speed_spec}")
                    else:
                        for i, part in enumerate(speed_parts):
                            if not part.isdigit():
                                errors.append(f"第 {line_number} 行：速率部分 {i+1} 應為數字: {part}")
                
                # 檢查 ifindex
                if not ifindex_str.strip().isdigit():
                    errors.append(f"第 {line_number} 行：ifindex 應為數字: {ifindex_str}")
        
        return len(errors) == 0, errors
    
    def print_statistics(self, bras_ip: str):
        """印出統計資訊"""
        if bras_ip not in self.users:
            print(f"尚未載入 {bras_ip} 的 Map 檔案")
            return
        
        users = self.users[bras_ip]
        speed_groups = self.get_users_by_speed(users)
        
        print("=" * 60)
        print(f"Map File 統計 - {bras_ip}")
        print("=" * 60)
        print(f"總使用者數: {len(users)}")
        print(f"速率方案數: {len(speed_groups)}")
        print()
        
        print("速率方案分布:")
        print("-" * 60)
        for speed_key, speed_users in sorted(speed_groups.items()):
            download, upload = speed_key.split('_')
            print(f"  {speed_key:20s} ({int(download)/1024:6.1f} / {int(upload)/1024:5.1f} Mbps): {len(speed_users):4d} 用戶")
        print("=" * 60)


def main():
    """測試主程式"""
    # 初始化讀取器
    reader = MapFileReader("maps")
    
    # 測試 IP（根據實際環境調整）
    test_ip = "127.0.0.1"
    
    print(f"測試讀取 Map File: {test_ip}")
    print()
    
    # 驗證格式
    is_valid, errors = reader.validate_map_file(test_ip)
    if not is_valid:
        print("❌ Map File 格式驗證失敗:")
        for error in errors:
            print(f"  {error}")
        print()
    else:
        print("✓ Map File 格式驗證通過")
        print()
    
    # 載入 Map File
    users = reader.load_map_file(test_ip)
    print(f"載入 {len(users)} 個使用者")
    print()
    
    # 顯示統計
    reader.print_statistics(test_ip)
    print()
    
    # 顯示範例資料
    if users:
        print("範例資料（前 5 筆）:")
        print("-" * 60)
        for user in users[:5]:
            print(f"用戶: {user.user_code}")
            print(f"  介面: {user.interface_id}")
            print(f"  速率: {user.speed_key} ({user.download_kbps/1024:.1f} / {user.upload_kbps/1024:.1f} Mbps)")
            print(f"  VLAN: {user.vlan}")
            print(f"  ifIndex: {user.ifindex}")
            print(f"  RRD: {user.get_rrd_filename(test_ip)}")
            print()


if __name__ == "__main__":
    main()
