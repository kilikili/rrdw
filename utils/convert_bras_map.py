#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert BRAS Map Format
將舊的 BRAS-Map.txt 格式轉換為統一的 E320 Map File 格式

舊格式（複雜）:
  bras_hostname,device_type,bras_ip,circuit_id,pvc,trunk_number,phone,area,interface,slot,port,bandwidth,vlan_count

新格式（統一）:
  1. BRAS-Devices.txt: BRAS_IP,設備類型,主機名稱,區域,頻寬上限(Mbps)
  2. map_{IP}_{slot}_{port}.txt: 使用者代碼,下載速率,上傳速率,ifindex,VLAN
"""

import os
import sys
from typing import Dict, List, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class OldBRASMapEntry:
    """舊格式的 BRAS Map 項目"""
    bras_hostname: str
    device_type: int
    bras_ip: str
    circuit_id: str
    pvc: str
    trunk_number: str
    phone: str
    area: str
    interface: str
    slot: int
    port: int
    bandwidth: int
    vlan_count: str
    
    @property
    def device_type_name(self) -> str:
        """設備類型名稱"""
        names = {1: "MX240", 2: "MX960", 3: "E320", 4: "ACX"}
        return names.get(self.device_type, "Unknown")


class BRASMapConverter:
    """BRAS Map 格式轉換器"""
    
    def __init__(self):
        self.entries: List[OldBRASMapEntry] = []
        self.devices: Dict[str, Dict] = {}
        self.map_files: Dict[Tuple[str, int, int], List[Dict]] = defaultdict(list)
    
    def load_old_format(self, filename: str) -> None:
        """
        載入舊格式的 BRAS-Map.txt
        
        Args:
            filename: 舊格式檔案路徑
        """
        if not os.path.exists(filename):
            print(f"錯誤: 找不到檔案 {filename}")
            return
        
        print(f"讀取舊格式: {filename}")
        
        with open(filename, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # 跳過空行和註解
                if not line or line.startswith('#'):
                    continue
                
                # 解析欄位
                parts = line.split(',')
                if len(parts) < 13:
                    print(f"警告: 第 {line_num} 行欄位不足: {line}")
                    continue
                
                try:
                    entry = OldBRASMapEntry(
                        bras_hostname=parts[0],
                        device_type=int(parts[1]),
                        bras_ip=parts[2],
                        circuit_id=parts[3],
                        pvc=parts[4],
                        trunk_number=parts[5],
                        phone=parts[6],
                        area=parts[7],
                        interface=parts[8],
                        slot=int(parts[9]),
                        port=int(parts[10]),
                        bandwidth=int(parts[11]) if parts[11].isdigit() else 0,
                        vlan_count=parts[12]
                    )
                    
                    self.entries.append(entry)
                    
                except (ValueError, IndexError) as e:
                    print(f"警告: 第 {line_num} 行解析失敗: {e}")
                    continue
        
        print(f"載入 {len(self.entries)} 個項目")
    
    def extract_devices(self) -> None:
        """從項目中提取設備清單"""
        print("\n提取設備清單...")
        
        for entry in self.entries:
            if entry.bras_ip not in self.devices:
                self.devices[entry.bras_ip] = {
                    'hostname': entry.bras_hostname,
                    'device_type': entry.device_type_name,
                    'area': entry.area,
                    'bandwidth_mbps': entry.bandwidth // 1024 if entry.bandwidth > 0 else 1000
                }
        
        print(f"找到 {len(self.devices)} 個設備")
    
    def save_devices_file(self, output_file: str) -> None:
        """
        儲存 BRAS-Devices.txt
        
        Args:
            output_file: 輸出檔案路徑
        """
        print(f"\n儲存設備清單: {output_file}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # 表頭
            f.write("# BRAS 設備清單\n")
            f.write("# BRAS_IP,設備類型,主機名稱,區域,頻寬上限(Mbps)\n")
            
            # 資料
            for bras_ip in sorted(self.devices.keys()):
                device = self.devices[bras_ip]
                f.write(f"{bras_ip},{device['device_type']},{device['hostname']},{device['area']},{device['bandwidth_mbps']}\n")
        
        print(f"✓ 已儲存 {len(self.devices)} 個設備")
    
    def generate_map_files_data(self) -> None:
        """
        產生 Map File 資料（但尚未包含 ifindex）
        
        注意: 舊格式沒有 ifindex，需要後續補充
        """
        print("\n產生 Map File 資料...")
        
        for entry in self.entries:
            key = (entry.bras_ip, entry.slot, entry.port)
            
            # 假設的速率方案（需要從其他來源取得）
            # 這裡使用預設值
            download_kbps = 51200  # 50M
            upload_kbps = 20480    # 20M
            
            # ifindex 預留為 0（需要後續填入）
            ifindex = 0
            
            # VLAN（從 trunk_number 或其他欄位取得）
            vlan = 0
            if entry.trunk_number.isdigit():
                vlan = int(entry.trunk_number)
            
            user_data = {
                'user_code': entry.phone if entry.phone else entry.trunk_number,
                'download_kbps': download_kbps,
                'upload_kbps': upload_kbps,
                'ifindex': ifindex,
                'vlan': vlan
            }
            
            self.map_files[key].append(user_data)
        
        print(f"產生 {len(self.map_files)} 個 Map File 的資料")
    
    def save_map_files(self, output_dir: str) -> None:
        """
        儲存 Map File（需要提醒使用者補充 ifindex）
        
        Args:
            output_dir: 輸出目錄
        """
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"\n儲存 Map Files 到: {output_dir}")
        
        for (bras_ip, slot, port), users in sorted(self.map_files.items()):
            filename = f"map_{bras_ip}_{slot}_{port}.txt"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                # 表頭
                device = self.devices.get(bras_ip, {})
                device_type = device.get('device_type', 'Unknown')
                f.write(f"# {device_type} {bras_ip} Slot {slot} Port {port}\n")
                f.write("# 使用者代碼,下載速率(Kbps),上傳速率(Kbps),ifindex,VLAN\n")
                f.write("# 警告: ifindex 需要手動補充！\n")
                f.write("#\n")
                
                # 資料
                for user in users:
                    f.write(f"{user['user_code']},{user['download_kbps']},{user['upload_kbps']},{user['ifindex']},{user['vlan']}\n")
            
            print(f"  ✓ {filename} ({len(users)} 使用者)")
        
        print(f"\n⚠️  重要提醒:")
        print(f"  1. Map File 中的 ifindex 目前為 0，需要手動補充")
        print(f"  2. 速率方案使用預設值，請依實際情況修改")
        print(f"  3. 建議使用 SNMP Walk 或其他工具取得正確的 ifindex")
    
    def print_summary(self) -> None:
        """印出轉換摘要"""
        print("\n" + "=" * 70)
        print("轉換摘要")
        print("=" * 70)
        
        print(f"設備數量: {len(self.devices)}")
        
        # 依設備類型分組
        type_count = defaultdict(int)
        for device in self.devices.values():
            type_count[device['device_type']] += 1
        
        for device_type, count in sorted(type_count.items()):
            print(f"  {device_type}: {count} 個")
        
        print(f"\nMap File 數量: {len(self.map_files)}")
        
        # 總使用者數
        total_users = sum(len(users) for users in self.map_files.values())
        print(f"總使用者數: {total_users}")
        
        print("=" * 70)


def main():
    """主程式"""
    import argparse
    
    parser = argparse.ArgumentParser(description='BRAS Map 格式轉換工具')
    parser.add_argument('--input', default='BRAS-Map.txt', help='舊格式檔案')
    parser.add_argument('--output-dir', default='maps', help='Map File 輸出目錄')
    parser.add_argument('--devices-file', default='BRAS-Devices.txt', help='設備清單輸出檔案')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("BRAS Map 格式轉換工具")
    print("=" * 70)
    print()
    
    # 初始化轉換器
    converter = BRASMapConverter()
    
    # 載入舊格式
    converter.load_old_format(args.input)
    
    if not converter.entries:
        print("錯誤: 沒有載入任何資料")
        sys.exit(1)
    
    # 提取設備清單
    converter.extract_devices()
    
    # 產生 Map File 資料
    converter.generate_map_files_data()
    
    # 儲存檔案
    converter.save_devices_file(args.devices_file)
    converter.save_map_files(args.output_dir)
    
    # 印出摘要
    converter.print_summary()
    
    print("\n✅ 轉換完成！")
    print(f"\n輸出檔案:")
    print(f"  - {args.devices_file} (設備清單)")
    print(f"  - {args.output_dir}/map_*.txt (Map Files)")
    print(f"\n⚠️  下一步:")
    print(f"  1. 檢查並修正 {args.devices_file}")
    print(f"  2. 為每個 Map File 補充正確的 ifindex")
    print(f"  3. 確認速率方案是否正確")
    print(f"  4. 使用 unified_map_reader.py 驗證格式")


if __name__ == "__main__":
    main()
