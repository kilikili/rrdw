#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Collector Dispatcher
智能收集器調度系統

根據 BRAS-Map.txt 中的 device_type 自動選擇正確的收集器：
- device_type = 3 (E320): 使用 Map File + ifindex 方式
- device_type = 1,2,4 (MX/ACX): 使用介面名稱方式（可擴充）

使用方式:
  python3 collector_dispatcher.py
  python3 collector_dispatcher.py --device-group A
  python3 collector_dispatcher.py --bras-ip 61.64.191.1
"""

import os
import sys
import time
import argparse
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

# 導入我們的讀取器
from bras_map_reader import BRASMapReader, DEVICE_TYPE_E320, DEVICE_TYPE_MX240, DEVICE_TYPE_MX960, DEVICE_TYPE_ACX7024
from map_file_reader import MapFileReader


@dataclass
class CollectionTask:
    """收集任務"""
    bras_hostname: str
    device_type: int
    bras_ip: str
    circuit_id: str
    slot: int
    port: int
    circuit_type: str
    bandwidth: int
    
    @property
    def device_type_name(self) -> str:
        """設備類型名稱"""
        names = {
            DEVICE_TYPE_MX240: "MX240",
            DEVICE_TYPE_MX960: "MX960",
            DEVICE_TYPE_E320: "E320",
            DEVICE_TYPE_ACX7024: "ACX7024"
        }
        return names.get(self.device_type, f"Unknown({self.device_type})")
    
    @property
    def is_e320(self) -> bool:
        """是否為 E320 設備"""
        return self.device_type == DEVICE_TYPE_E320
    
    @property
    def collector_type(self) -> str:
        """收集器類型"""
        if self.is_e320:
            return "E320_MAP_FILE"
        else:
            return "MX_ACX_INTERFACE"


class CollectorDispatcher:
    """收集器調度系統"""
    
    def __init__(self, bras_map_file: str = "BRAS-Map.txt", map_dir: str = "maps"):
        """
        初始化調度器
        
        Args:
            bras_map_file: BRAS-Map.txt 檔案路徑
            map_dir: Map File 目錄
        """
        self.bras_map_file = bras_map_file
        self.map_dir = map_dir
        
        # 初始化讀取器
        self.bras_reader = BRASMapReader(bras_map_file)
        self.map_reader = MapFileReader(map_dir)
        
        # 收集結果
        self.results = {
            'success': [],
            'failed': [],
            'skipped': []
        }
    
    def load_tasks(self) -> None:
        """載入所有收集任務"""
        print("=" * 70)
        print("載入 BRAS-Map.txt")
        print("=" * 70)
        
        self.bras_reader.load()
        
        # 顯示統計
        self.bras_reader.print_statistics()
    
    def get_tasks_by_ip(self, bras_ip: str) -> List[CollectionTask]:
        """
        取得指定 IP 的所有任務
        
        Args:
            bras_ip: BRAS IP 位址
            
        Returns:
            CollectionTask 列表
        """
        circuits = self.bras_reader.get_circuits_by_ip(bras_ip)
        
        tasks = []
        for circuit in circuits:
            task = CollectionTask(
                bras_hostname=circuit.bras_hostname,
                device_type=circuit.device_type,
                bras_ip=circuit.bras_ip,
                circuit_id=circuit.trunk_number,
                slot=circuit.slot,
                port=circuit.port,
                circuit_type="GE",  # 從 BRAS-Map 取得
                bandwidth=0  # 從 BRAS-Map 取得
            )
            tasks.append(task)
        
        return tasks
    
    def get_all_tasks(self) -> List[CollectionTask]:
        """取得所有收集任務"""
        all_tasks = []
        
        for bras_ip in self.bras_reader.get_all_bras_ips():
            tasks = self.get_tasks_by_ip(bras_ip)
            all_tasks.extend(tasks)
        
        return all_tasks
    
    def collect_e320(self, task: CollectionTask) -> Dict:
        """
        收集 E320 設備資料
        使用 Map File + ifindex 方式
        
        Args:
            task: 收集任務
            
        Returns:
            收集結果
        """
        print(f"\n{'='*70}")
        print(f"E320 收集: {task.bras_hostname} ({task.bras_ip})")
        print(f"  Slot: {task.slot}, Port: {task.port}")
        print(f"{'='*70}")
        
        start_time = time.time()
        
        try:
            # 1. 載入 Map File
            print(f"步驟 1: 載入 Map File...")
            users = self.map_reader.load_map_file(
                task.bras_ip,
                slot=task.slot,
                port=task.port
            )
            
            if not users:
                return {
                    'status': 'skipped',
                    'message': f'未找到使用者 (slot={task.slot}, port={task.port})',
                    'task': task,
                    'elapsed': time.time() - start_time
                }
            
            print(f"  ✓ 載入 {len(users)} 個使用者")
            
            # 2. 顯示速率分組
            speed_groups = self.map_reader.get_users_by_speed(users)
            print(f"  ✓ {len(speed_groups)} 個速率方案")
            
            for speed_key, group_users in speed_groups.items():
                download, upload = speed_key.split('_')
                print(f"    - {speed_key} ({int(download)/1024:.1f}/{int(upload)/1024:.1f} Mbps): {len(group_users)} 用戶")
            
            # 3. 取得 ifindex 列表
            ifindexes = self.map_reader.get_all_ifindexes(users)
            print(f"\n步驟 2: 需要查詢 {len(ifindexes)} 個 ifindex")
            
            # 4. 這裡會調用實際的 SNMP 收集
            # 目前只是模擬
            print(f"步驟 3: SNMP 收集 (模擬)")
            print(f"  ✓ 將使用 isp_traffic_collector_e320.py 的邏輯")
            print(f"  ✓ 並行查詢 ifindex: {ifindexes[:3]}...")
            
            # 5. RRD 路徑範例
            print(f"\n步驟 4: RRD 檔案路徑範例")
            for user in users[:3]:
                rrd_path = user.get_rrd_path("/home/bulks_data", task.bras_ip)
                print(f"  - {user.user_code}: {Path(rrd_path).name}")
            
            elapsed = time.time() - start_time
            
            return {
                'status': 'success',
                'message': f'成功收集 {len(users)} 個使用者',
                'task': task,
                'user_count': len(users),
                'speed_groups': len(speed_groups),
                'elapsed': elapsed
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'message': f'收集失敗: {e}',
                'task': task,
                'elapsed': time.time() - start_time
            }
    
    def collect_mx_acx(self, task: CollectionTask) -> Dict:
        """
        收集 MX/ACX 設備資料
        使用介面名稱方式
        
        Args:
            task: 收集任務
            
        Returns:
            收集結果
        """
        print(f"\n{'='*70}")
        print(f"{task.device_type_name} 收集: {task.bras_hostname} ({task.bras_ip})")
        print(f"  Slot: {task.slot}, Port: {task.port}")
        print(f"{'='*70}")
        
        start_time = time.time()
        
        try:
            # MX/ACX 收集邏輯
            # 這裡可以實作介面名稱推算 ifindex 的方式
            print(f"步驟 1: 查詢介面資訊")
            print(f"  ✓ 介面格式: xe-{task.slot}/0/{task.port} 或 ge-{task.slot}/0/{task.port}")
            
            print(f"\n步驟 2: SNMP Walk 收集 (模擬)")
            print(f"  ✓ 將使用 SNMP Walk 取得所有介面")
            
            print(f"\n步驟 3: 介面過濾")
            print(f"  ✓ 篩選符合 slot={task.slot}, port={task.port} 的介面")
            
            elapsed = time.time() - start_time
            
            return {
                'status': 'success',
                'message': f'成功收集 MX/ACX 設備',
                'task': task,
                'elapsed': elapsed
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'message': f'收集失敗: {e}',
                'task': task,
                'elapsed': time.time() - start_time
            }
    
    def dispatch_task(self, task: CollectionTask) -> Dict:
        """
        調度單一任務到正確的收集器
        
        Args:
            task: 收集任務
            
        Returns:
            收集結果
        """
        print(f"\n{'='*70}")
        print(f"調度任務: {task.bras_hostname} ({task.bras_ip})")
        print(f"  設備類型: {task.device_type_name}")
        print(f"  收集器: {task.collector_type}")
        print(f"{'='*70}")
        
        if task.is_e320:
            # E320 使用 Map File 方式
            return self.collect_e320(task)
        else:
            # MX/ACX 使用介面名稱方式
            return self.collect_mx_acx(task)
    
    def collect_all(self, max_workers: int = 3) -> None:
        """
        收集所有設備
        
        Args:
            max_workers: 最大並行數
        """
        tasks = self.get_all_tasks()
        
        print(f"\n{'='*70}")
        print(f"開始收集")
        print(f"{'='*70}")
        print(f"總任務數: {len(tasks)}")
        print(f"並行數: {max_workers}")
        print(f"{'='*70}")
        
        # 依設備類型分組顯示
        e320_tasks = [t for t in tasks if t.is_e320]
        mx_acx_tasks = [t for t in tasks if not t.is_e320]
        
        print(f"\n任務分布:")
        print(f"  E320: {len(e320_tasks)} 個任務")
        print(f"  MX/ACX: {len(mx_acx_tasks)} 個任務")
        
        # 按優先序排序（新設備優先）
        tasks.sort(key=lambda t: t.device_type)
        
        start_time = time.time()
        
        # 並行執行（但由於是模擬，這裡使用順序執行）
        for task in tasks:
            result = self.dispatch_task(task)
            
            # 記錄結果
            if result['status'] == 'success':
                self.results['success'].append(result)
            elif result['status'] == 'failed':
                self.results['failed'].append(result)
            else:
                self.results['skipped'].append(result)
        
        total_elapsed = time.time() - start_time
        
        # 顯示總結
        self.print_summary(total_elapsed)
    
    def collect_by_ip(self, bras_ip: str) -> None:
        """
        收集指定 IP 的設備
        
        Args:
            bras_ip: BRAS IP 位址
        """
        tasks = self.get_tasks_by_ip(bras_ip)
        
        if not tasks:
            print(f"找不到 IP {bras_ip} 的任務")
            return
        
        print(f"\n{'='*70}")
        print(f"收集 {bras_ip}")
        print(f"{'='*70}")
        print(f"任務數: {len(tasks)}")
        
        for task in tasks:
            result = self.dispatch_task(task)
            
            if result['status'] == 'success':
                self.results['success'].append(result)
            elif result['status'] == 'failed':
                self.results['failed'].append(result)
            else:
                self.results['skipped'].append(result)
        
        # 顯示總結
        self.print_summary()
    
    def print_summary(self, total_elapsed: Optional[float] = None) -> None:
        """印出執行總結"""
        print(f"\n{'='*70}")
        print("執行總結")
        print(f"{'='*70}")
        
        success_count = len(self.results['success'])
        failed_count = len(self.results['failed'])
        skipped_count = len(self.results['skipped'])
        total = success_count + failed_count + skipped_count
        
        print(f"總任務: {total}")
        print(f"  ✓ 成功: {success_count}")
        print(f"  ✗ 失敗: {failed_count}")
        print(f"  ⊘ 跳過: {skipped_count}")
        
        if total_elapsed:
            print(f"\n總耗時: {total_elapsed:.2f} 秒")
        
        # 成功的任務
        if self.results['success']:
            print(f"\n成功的任務:")
            for result in self.results['success']:
                task = result['task']
                print(f"  ✓ {task.bras_hostname} ({task.device_type_name}): {result['message']}")
                if 'user_count' in result:
                    print(f"    - 用戶數: {result['user_count']}")
                    print(f"    - 速率方案: {result['speed_groups']}")
                print(f"    - 耗時: {result['elapsed']:.2f}s")
        
        # 失敗的任務
        if self.results['failed']:
            print(f"\n失敗的任務:")
            for result in self.results['failed']:
                task = result['task']
                print(f"  ✗ {task.bras_hostname} ({task.device_type_name}): {result['message']}")
        
        # 跳過的任務
        if self.results['skipped']:
            print(f"\n跳過的任務:")
            for result in self.results['skipped']:
                task = result['task']
                print(f"  ⊘ {task.bras_hostname} ({task.device_type_name}): {result['message']}")
        
        print(f"{'='*70}")


def main():
    """主程式"""
    parser = argparse.ArgumentParser(description='智能收集器調度系統')
    parser.add_argument('--bras-map', default='BRAS-Map.txt', help='BRAS-Map.txt 檔案路徑')
    parser.add_argument('--map-dir', default='maps', help='Map File 目錄')
    parser.add_argument('--bras-ip', help='只收集指定 IP 的設備')
    parser.add_argument('--device-type', type=int, choices=[1, 2, 3, 4], help='只收集指定類型的設備')
    parser.add_argument('--max-workers', type=int, default=3, help='最大並行數')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("智能收集器調度系統")
    print("=" * 70)
    print()
    
    # 初始化調度器
    dispatcher = CollectorDispatcher(args.bras_map, args.map_dir)
    
    # 載入任務
    dispatcher.load_tasks()
    
    # 執行收集
    if args.bras_ip:
        # 只收集指定 IP
        dispatcher.collect_by_ip(args.bras_ip)
    else:
        # 收集所有設備
        dispatcher.collect_all(args.max_workers)


if __name__ == "__main__":
    main()
