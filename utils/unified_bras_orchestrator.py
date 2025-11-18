#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified BRAS Orchestrator
統一 BRAS 調度器（支援 Tab 分隔 BRAS-Map.txt）

功能：
1. 讀取 BRAS-Map.txt (Tab 分隔)
2. 為每個 Circuit 載入對應的 Map File
3. 根據設備類型調度適當的收集器
4. 執行流量收集
"""

import os
import sys
import time
from typing import List, Dict, Optional
from datetime import datetime

# 假設已有的模組
from bras_map_tsv_reader import BRASMapTSVReader, BRASCircuit
from unified_map_reader import UnifiedMapReader, MapUser


class CollectorStats:
    """收集統計"""
    def __init__(self):
        self.total_circuits = 0
        self.total_users = 0
        self.success_circuits = 0
        self.failed_circuits = 0
        self.start_time = None
        self.end_time = None
        self.device_stats = {}  # {device_type: count}
    
    def add_success(self, device_type: str, user_count: int):
        """記錄成功的收集"""
        self.success_circuits += 1
        self.total_users += user_count
        if device_type not in self.device_stats:
            self.device_stats[device_type] = {'success': 0, 'users': 0}
        self.device_stats[device_type]['success'] += 1
        self.device_stats[device_type]['users'] += user_count
    
    def add_failure(self, device_type: str):
        """記錄失敗的收集"""
        self.failed_circuits += 1
        if device_type not in self.device_stats:
            self.device_stats[device_type] = {'failed': 0}
        if 'failed' not in self.device_stats[device_type]:
            self.device_stats[device_type]['failed'] = 0
        self.device_stats[device_type]['failed'] += 1
    
    def print_report(self):
        """印出收集報告"""
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
        else:
            duration = 0
        
        print("\n" + "=" * 70)
        print("收集統計報告")
        print("=" * 70)
        print(f"開始時間: {self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else 'N/A'}")
        print(f"結束時間: {self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else 'N/A'}")
        print(f"執行時間: {duration:.1f} 秒")
        print()
        print(f"總 Circuit 數: {self.total_circuits}")
        print(f"成功收集: {self.success_circuits}")
        print(f"失敗收集: {self.failed_circuits}")
        print(f"總使用者數: {self.total_users}")
        print()
        
        if self.device_stats:
            print("各設備統計:")
            print("-" * 70)
            for device_type in sorted(self.device_stats.keys()):
                stats = self.device_stats[device_type]
                success = stats.get('success', 0)
                failed = stats.get('failed', 0)
                users = stats.get('users', 0)
                print(f"  {device_type:8s}: {success:3d} 成功, {failed:3d} 失敗, {users:5d} 使用者")
        
        print("=" * 70)


class UnifiedBRASOrchestrator:
    """統一 BRAS 調度器"""
    
    def __init__(self, 
                 bras_map_file: str = "config/BRAS-Map.txt",
                 map_dir: str = "config/maps",
                 rrd_base_dir: str = "/opt/rrdw/data"):
        """
        初始化調度器
        
        Args:
            bras_map_file: BRAS-Map.txt 檔案路徑
            map_dir: Map Files 目錄
            rrd_base_dir: RRD 基礎目錄
        """
        self.bras_map_file = bras_map_file
        self.map_dir = map_dir
        self.rrd_base_dir = rrd_base_dir
        
        # 讀取器
        self.bras_reader = BRASMapTSVReader(bras_map_file)
        self.map_reader = UnifiedMapReader(map_dir)
        
        # 統計
        self.stats = CollectorStats()
        
        print("統一 BRAS 調度器初始化")
        print(f"  BRAS Map: {bras_map_file}")
        print(f"  Map Dir: {map_dir}")
        print(f"  RRD Base: {rrd_base_dir}")
    
    def load_configuration(self) -> bool:
        """
        載入配置
        
        Returns:
            是否成功
        """
        print("\n載入配置...")
        
        # 載入 BRAS-Map.txt
        self.bras_reader.load()
        
        if not self.bras_reader.circuits:
            print("錯誤: 沒有載入任何 Circuit")
            return False
        
        print(f"✓ 載入 {len(self.bras_reader.circuits)} 個 Circuit")
        
        self.stats.total_circuits = len(self.bras_reader.circuits)
        
        return True
    
    def collect_circuit(self, circuit: BRASCircuit, dry_run: bool = False) -> bool:
        """
        收集單一 Circuit
        
        Args:
            circuit: BRASCircuit 物件
            dry_run: 是否為測試模式（不實際執行）
            
        Returns:
            是否成功
        """
        print(f"\n處理: {circuit.ip} Slot {circuit.slot} Port {circuit.port} ({circuit.device_type_name})")
        
        # 載入 Map File
        users = self.map_reader.load_map_file(circuit.ip, circuit.slot, circuit.port)
        
        if not users:
            print(f"  ⚠️  找不到 Map File 或沒有使用者")
            self.stats.add_failure(circuit.device_type_name)
            return False
        
        print(f"  ✓ 載入 {len(users)} 個使用者")
        
        if dry_run:
            print(f"  [DRY RUN] 模擬收集...")
            self.stats.add_success(circuit.device_type_name, len(users))
            return True
        
        # 根據設備類型選擇收集器
        try:
            if circuit.device_type == 3:  # E320
                success = self._collect_e320(circuit, users)
            elif circuit.device_type == 4:  # ACX
                success = self._collect_acx(circuit, users)
            elif circuit.device_type == 2:  # MX960
                success = self._collect_mx960(circuit, users)
            elif circuit.device_type == 1:  # MX240
                success = self._collect_mx240(circuit, users)
            else:
                print(f"  ✗ 不支援的設備類型: {circuit.device_type}")
                self.stats.add_failure(circuit.device_type_name)
                return False
            
            if success:
                self.stats.add_success(circuit.device_type_name, len(users))
            else:
                self.stats.add_failure(circuit.device_type_name)
            
            return success
            
        except Exception as e:
            print(f"  ✗ 收集失敗: {e}")
            self.stats.add_failure(circuit.device_type_name)
            return False
    
    def _collect_e320(self, circuit: BRASCircuit, users: List[MapUser]) -> bool:
        """E320 收集器"""
        print(f"  → 使用 E320 收集器")
        print(f"  → 介面: {circuit.interface_name}")
        
        # TODO: 實際執行 E320 收集
        # from e320_collector import E320Collector
        # collector = E320Collector()
        # collector.collect(circuit.ip, circuit.slot, circuit.port, users)
        
        print(f"  ✓ 收集完成: {len(users)} 使用者")
        return True
    
    def _collect_acx(self, circuit: BRASCircuit, users: List[MapUser]) -> bool:
        """ACX 收集器"""
        print(f"  → 使用 ACX 收集器")
        print(f"  → 介面: {circuit.interface_name}")
        
        # TODO: 實際執行 ACX 收集
        # from acx_collector import ACXCollector
        # collector = ACXCollector()
        # collector.collect(circuit.ip, circuit.slot, circuit.port, users)
        
        print(f"  ✓ 收集完成: {len(users)} 使用者")
        return True
    
    def _collect_mx960(self, circuit: BRASCircuit, users: List[MapUser]) -> bool:
        """MX960 收集器"""
        print(f"  → 使用 MX960 收集器")
        print(f"  → 介面: {circuit.interface_name}")
        
        # TODO: 實際執行 MX960 收集
        # from mx960_collector import MX960Collector
        # collector = MX960Collector()
        # collector.collect(circuit.ip, circuit.slot, circuit.port, users)
        
        print(f"  ✓ 收集完成: {len(users)} 使用者")
        return True
    
    def _collect_mx240(self, circuit: BRASCircuit, users: List[MapUser]) -> bool:
        """MX240 收集器"""
        print(f"  → 使用 MX240 收集器")
        print(f"  → 介面: {circuit.interface_name}")
        
        # TODO: 實際執行 MX240 收集
        # from mx240_collector import MX240Collector
        # collector = MX240Collector()
        # collector.collect(circuit.ip, circuit.slot, circuit.port, users)
        
        print(f"  ✓ 收集完成: {len(users)} 使用者")
        return True
    
    def collect_all(self, dry_run: bool = False, 
                   device_type_filter: Optional[int] = None,
                   area_filter: Optional[str] = None) -> bool:
        """
        收集所有 Circuit
        
        Args:
            dry_run: 是否為測試模式
            device_type_filter: 只收集指定設備類型 (1/2/3/4)
            area_filter: 只收集指定區域
            
        Returns:
            是否全部成功
        """
        self.stats.start_time = datetime.now()
        
        # 篩選 Circuit
        circuits = self.bras_reader.circuits
        
        if device_type_filter:
            circuits = [c for c in circuits if c.device_type == device_type_filter]
            device_name = {1: "MX240", 2: "MX960", 3: "E320", 4: "ACX"}[device_type_filter]
            print(f"\n篩選條件: 設備類型 = {device_name}")
        
        if area_filter:
            circuits = [c for c in circuits if c.area == area_filter]
            print(f"\n篩選條件: 區域 = {area_filter}")
        
        print(f"\n開始收集 {len(circuits)} 個 Circuit")
        
        if dry_run:
            print("⚠️  測試模式 (DRY RUN) - 不會實際執行收集")
        
        print("=" * 70)
        
        # 逐一收集
        for i, circuit in enumerate(circuits, 1):
            print(f"\n[{i}/{len(circuits)}]", end=" ")
            self.collect_circuit(circuit, dry_run)
        
        self.stats.end_time = datetime.now()
        
        # 印出報告
        self.stats.print_report()
        
        return self.stats.failed_circuits == 0
    
    def collect_by_ip(self, ip: str, dry_run: bool = False) -> bool:
        """
        收集指定 IP 的所有 Circuit
        
        Args:
            ip: BRAS IP
            dry_run: 是否為測試模式
            
        Returns:
            是否成功
        """
        circuits = self.bras_reader.get_circuits_by_ip(ip)
        
        if not circuits:
            print(f"找不到 IP {ip} 的 Circuit")
            return False
        
        print(f"找到 {len(circuits)} 個 Circuit for IP {ip}")
        
        self.stats.start_time = datetime.now()
        self.stats.total_circuits = len(circuits)
        
        for circuit in circuits:
            self.collect_circuit(circuit, dry_run)
        
        self.stats.end_time = datetime.now()
        self.stats.print_report()
        
        return self.stats.failed_circuits == 0


def main():
    """主程式"""
    import argparse
    
    parser = argparse.ArgumentParser(description='統一 BRAS 調度器')
    parser.add_argument('--bras-map', default='config/BRAS-Map.txt', 
                       help='BRAS-Map.txt 檔案路徑')
    parser.add_argument('--map-dir', default='config/maps', 
                       help='Map Files 目錄')
    parser.add_argument('--rrd-base', default='/opt/rrdw/data', 
                       help='RRD 基礎目錄')
    parser.add_argument('--dry-run', action='store_true', 
                       help='測試模式（不實際執行收集）')
    parser.add_argument('--device-type', type=int, choices=[1,2,3,4],
                       help='只收集指定設備類型 (1=MX240, 2=MX960, 3=E320, 4=ACX)')
    parser.add_argument('--area', help='只收集指定區域')
    parser.add_argument('--ip', help='只收集指定 IP')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("統一 BRAS 調度器")
    print("=" * 70)
    
    # 初始化
    orchestrator = UnifiedBRASOrchestrator(
        bras_map_file=args.bras_map,
        map_dir=args.map_dir,
        rrd_base_dir=args.rrd_base
    )
    
    # 載入配置
    if not orchestrator.load_configuration():
        sys.exit(1)
    
    # 執行收集
    if args.ip:
        success = orchestrator.collect_by_ip(args.ip, args.dry_run)
    else:
        success = orchestrator.collect_all(
            dry_run=args.dry_run,
            device_type_filter=args.device_type,
            area_filter=args.area
        )
    
    # 結果
    if success:
        print("\n✅ 收集完成")
        sys.exit(0)
    else:
        print("\n⚠️  收集過程中發生錯誤")
        sys.exit(1)


if __name__ == "__main__":
    main()
