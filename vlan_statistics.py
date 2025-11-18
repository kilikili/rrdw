#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VLAN Statistics Report
VLAN 數量統計報表

功能：
- 統計各 Circuit 的 VLAN 數量
- 比較月度增減
- 依分區分組
- 輸出 HTML/CSV/TXT 格式
"""

import os
import sys
import glob
import time
import rrdtool
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from dataclasses import dataclass
from collections import defaultdict
import argparse


@dataclass
class VLANStat:
    """VLAN 統計資料"""
    circuit_id: str
    bras_ip: str
    interface: str
    area: str
    current_count: int
    previous_count: int
    
    @property
    def change(self) -> int:
        """變化量"""
        return self.current_count - self.previous_count
    
    @property
    def change_percentage(self) -> float:
        """變化百分比"""
        if self.previous_count == 0:
            return 0.0
        return (self.change / self.previous_count) * 100


class VLANStatistics:
    """VLAN 統計分析器"""
    
    def __init__(self, rrd_circuit_dir: str = "/home/bulks_data/circuit",
                 bras_map_file: str = "BRAS-Map.txt"):
        """
        初始化統計器
        
        Args:
            rrd_circuit_dir: Circuit RRD 目錄
            bras_map_file: BRAS-Map.txt 檔案
        """
        self.rrd_circuit_dir = rrd_circuit_dir
        self.bras_map_file = bras_map_file
        
        # 載入區域資訊
        self.circuit_areas = self.load_circuit_areas()
    
    def load_circuit_areas(self) -> Dict[str, str]:
        """
        從 BRAS-Map.txt 載入 Circuit 區域資訊
        
        Returns:
            {circuit_id: area}
        """
        areas = {}
        
        if not os.path.exists(self.bras_map_file):
            return areas
        
        with open(self.bras_map_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split(',')
                if len(parts) >= 13:
                    bras_ip = parts[2]
                    area = parts[8] if len(parts) > 8 else "未知"
                    slot = parts[10]
                    port = parts[11]
                    
                    # 組合 circuit_id
                    circuit_id = f"{bras_ip}_{slot}_{port}"
                    areas[circuit_id] = area
        
        return areas
    
    def get_circuit_rrd_files(self) -> List[str]:
        """取得所有 Circuit RRD 檔案"""
        pattern = os.path.join(self.rrd_circuit_dir, "**/*_circuit.rrd")
        return glob.glob(pattern, recursive=True)
    
    def parse_circuit_id(self, rrd_file: str) -> Tuple[str, str, str]:
        """
        解析 Circuit ID
        
        Returns:
            (bras_ip, interface, circuit_id)
        """
        basename = os.path.basename(rrd_file)
        name_parts = basename.replace('_circuit.rrd', '').split('_')
        
        if len(name_parts) < 5:
            return None, None, None
        
        bras_ip = '.'.join(name_parts[:4])
        interface = '_'.join(name_parts[4:])
        interface = interface.replace('-', '/')
        circuit_id = f"{bras_ip}_{interface}"
        
        return bras_ip, interface, circuit_id
    
    def get_vlan_count(self, rrd_file: str, timestamp: int) -> int:
        """
        取得指定時間的 VLAN 數量
        
        Args:
            rrd_file: Circuit RRD 檔案
            timestamp: 時間戳記
            
        Returns:
            VLAN 數量
        """
        try:
            # 讀取該時間點前後的資料
            start_time = timestamp - 3600  # 前 1 小時
            end_time = timestamp + 3600    # 後 1 小時
            
            result = rrdtool.fetch(
                rrd_file,
                'AVERAGE',
                '--start', str(start_time),
                '--end', str(end_time)
            )
            
            (fetch_start, fetch_end, fetch_step), ds_names, data = result
            
            # vlan_count 是第 2 個 DS（索引 1）
            vlan_count_index = 1
            
            # 找最接近的非 None 值
            for row in reversed(data):
                if row[vlan_count_index] is not None:
                    return int(row[vlan_count_index])
            
            return 0
            
        except Exception as e:
            print(f"讀取失敗 {rrd_file}: {e}")
            return 0
    
    def get_month_end_timestamp(self, year: int, month: int) -> int:
        """
        取得月底的時間戳記
        
        Args:
            year: 年
            month: 月
            
        Returns:
            Unix timestamp
        """
        # 下個月的第一天
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        
        # 往前退一天
        month_end = next_month - timedelta(days=1)
        
        # 設定為當天結束時間
        month_end = month_end.replace(hour=23, minute=59, second=59)
        
        return int(month_end.timestamp())
    
    def analyze_monthly_change(self) -> List[VLANStat]:
        """
        分析月度 VLAN 數量變化
        
        Returns:
            VLANStat 列表
        """
        now = datetime.now()
        
        # 本月底
        current_timestamp = self.get_month_end_timestamp(now.year, now.month)
        
        # 上月底
        if now.month == 1:
            previous_timestamp = self.get_month_end_timestamp(now.year - 1, 12)
        else:
            previous_timestamp = self.get_month_end_timestamp(now.year, now.month - 1)
        
        print(f"分析期間:")
        print(f"  上月: {datetime.fromtimestamp(previous_timestamp).strftime('%Y-%m-%d')}")
        print(f"  本月: {datetime.fromtimestamp(current_timestamp).strftime('%Y-%m-%d')}")
        print()
        
        # 取得所有 Circuit
        rrd_files = self.get_circuit_rrd_files()
        
        print(f"找到 {len(rrd_files)} 個 Circuit")
        print("統計 VLAN 數量中...")
        print()
        
        stats = []
        
        for rrd_file in rrd_files:
            bras_ip, interface, circuit_id = self.parse_circuit_id(rrd_file)
            
            if not circuit_id:
                continue
            
            # 取得上月和本月的 VLAN 數量
            previous_count = self.get_vlan_count(rrd_file, previous_timestamp)
            current_count = self.get_vlan_count(rrd_file, current_timestamp)
            
            # 取得區域
            area = self.circuit_areas.get(circuit_id, "未知")
            
            stat = VLANStat(
                circuit_id=circuit_id,
                bras_ip=bras_ip,
                interface=interface,
                area=area,
                current_count=current_count,
                previous_count=previous_count
            )
            
            stats.append(stat)
        
        return stats
    
    def group_by_area(self, stats: List[VLANStat]) -> Dict[str, List[VLANStat]]:
        """
        依區域分組
        
        Args:
            stats: VLANStat 列表
            
        Returns:
            {area: [VLANStat]}
        """
        groups = defaultdict(list)
        
        for stat in stats:
            groups[stat.area].append(stat)
        
        return dict(groups)
    
    def output_text(self, stats: List[VLANStat], output_file: str = None):
        """輸出文字格式報表"""
        lines = []
        
        # 標題
        now = datetime.now()
        current_month = now.strftime('%Y年%m月')
        
        if now.month == 1:
            previous_month = f"{now.year-1}年12月"
        else:
            previous_month = f"{now.year}年{now.month-1:02d}月"
        
        lines.append("=" * 80)
        lines.append(f"Circuit VLAN 數量統計 - {current_month}")
        lines.append("=" * 80)
        lines.append()
        
        # 依區域分組
        area_groups = self.group_by_area(stats)
        
        # 全區總計
        total_previous = sum(s.previous_count for s in stats)
        total_current = sum(s.current_count for s in stats)
        total_change = total_current - total_previous
        
        # 各分區統計
        for area in sorted(area_groups.keys()):
            area_stats = area_groups[area]
            
            lines.append("=" * 80)
            lines.append(f"分區: {area}")
            lines.append("=" * 80)
            lines.append(
                f"{'Circuit':<25} {previous_month:>10} {current_month:>10} "
                f"{'增減':>10} {'變化率':>10}"
            )
            lines.append("-" * 80)
            
            area_previous = 0
            area_current = 0
            
            for stat in sorted(area_stats, key=lambda s: s.change, reverse=True):
                change_str = f"{stat.change:+d}"
                change_pct_str = f"{stat.change_percentage:+.1f}%"
                
                lines.append(
                    f"{stat.circuit_id:<25} {stat.previous_count:>10} "
                    f"{stat.current_count:>10} {change_str:>10} {change_pct_str:>10}"
                )
                
                area_previous += stat.previous_count
                area_current += stat.current_count
            
            # 分區小計
            area_change = area_current - area_previous
            area_change_pct = (area_change / area_previous * 100) if area_previous > 0 else 0
            
            lines.append("-" * 80)
            lines.append(
                f"{'小計':<25} {area_previous:>10} {area_current:>10} "
                f"{area_change:>+10} {area_change_pct:>+9.1f}%"
            )
            lines.append()
        
        # 總計
        lines.append("=" * 80)
        total_change_pct = (total_change / total_previous * 100) if total_previous > 0 else 0
        lines.append(
            f"{'全區總計':<25} {total_previous:>10} {total_current:>10} "
            f"{total_change:>+10} {total_change_pct:>+9.1f}%"
        )
        lines.append("=" * 80)
        
        output = '\n'.join(lines)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"報表已儲存: {output_file}")
        else:
            print(output)
    
    def output_csv(self, stats: List[VLANStat], output_file: str):
        """輸出 CSV 格式報表"""
        import csv
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 表頭
            writer.writerow([
                'Circuit ID', 'BRAS IP', 'Interface', 'Area',
                'Previous Count', 'Current Count', 'Change', 'Change %'
            ])
            
            # 資料
            for stat in stats:
                writer.writerow([
                    stat.circuit_id,
                    stat.bras_ip,
                    stat.interface,
                    stat.area,
                    stat.previous_count,
                    stat.current_count,
                    stat.change,
                    f"{stat.change_percentage:.1f}%"
                ])
        
        print(f"CSV 報表已儲存: {output_file}")


def main():
    """主程式"""
    parser = argparse.ArgumentParser(description='VLAN 數量統計報表')
    parser.add_argument('--circuit-dir', default='/home/bulks_data/circuit',
                       help='Circuit RRD 目錄')
    parser.add_argument('--bras-map', default='BRAS-Map.txt',
                       help='BRAS-Map.txt 檔案')
    parser.add_argument('--format', choices=['text', 'csv', 'all'],
                       default='text', help='輸出格式')
    parser.add_argument('--output-dir', default='./reports',
                       help='輸出目錄')
    
    args = parser.parse_args()
    
    # 建立輸出目錄
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 初始化統計器
    statistics = VLANStatistics(args.circuit_dir, args.bras_map)
    
    # 分析月度變化
    print("=" * 80)
    print("VLAN 數量統計")
    print("=" * 80)
    print()
    
    stats = statistics.analyze_monthly_change()
    
    if not stats:
        print("沒有找到統計資料")
        return
    
    print(f"完成！統計 {len(stats)} 個 Circuit")
    print()
    
    # 輸出報表
    date_str = datetime.now().strftime('%Y%m')
    
    if args.format == 'text' or args.format == 'all':
        output_file = os.path.join(args.output_dir, f'vlan_stats_{date_str}.txt')
        statistics.output_text(stats, output_file)
    
    if args.format == 'csv' or args.format == 'all':
        output_file = os.path.join(args.output_dir, f'vlan_stats_{date_str}.csv')
        statistics.output_csv(stats, output_file)
    
    print()
    print("完成！")


if __name__ == "__main__":
    main()
