#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Circuit Congestion Analysis Report
Circuit 擁塞分析報表

功能：
- 分析最近 N 日的 Circuit 流量
- 識別連續擁塞時段（流量 > 95% 頻寬上限）
- 計算擁塞時數和占比
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
import argparse


@dataclass
class CongestionRecord:
    """擁塞記錄"""
    timestamp: int
    rate_mbps: float
    limit_mbps: int
    congestion_ratio: float  # 擁塞比例
    is_congested: bool
    
    def __repr__(self):
        status = "🔴" if self.is_congested else "🟢"
        return f"{status} {self.rate_mbps:.1f}/{self.limit_mbps} Mbps ({self.congestion_ratio:.1%})"


@dataclass
class CircuitCongestionReport:
    """Circuit 擁塞報表"""
    circuit_id: str
    bras_ip: str
    interface: str
    area: str
    bandwidth_limit_mbps: int
    analysis_days: int
    
    # 統計資料
    peak_rate_mbps: float
    avg_rate_mbps: float
    congestion_hours: float
    congestion_percentage: float
    
    # 每日明細
    daily_stats: List[Dict]
    
    # 擁塞時段
    congestion_periods: List[Dict]


class CongestionAnalyzer:
    """Circuit 擁塞分析器"""
    
    def __init__(self, rrd_circuit_dir: str = "/home/bulks_data/circuit",
                 bras_map_file: str = "BRAS-Map.txt",
                 congestion_threshold: float = 0.95,
                 min_congestion_minutes: int = 15):
        """
        初始化分析器
        
        Args:
            rrd_circuit_dir: Circuit RRD 目錄
            bras_map_file: BRAS-Map.txt 檔案
            congestion_threshold: 擁塞閾值（預設 95%）
            min_congestion_minutes: 最小擁塞時間（預設 15 分鐘）
        """
        self.rrd_circuit_dir = rrd_circuit_dir
        self.bras_map_file = bras_map_file
        self.congestion_threshold = congestion_threshold
        self.min_congestion_minutes = min_congestion_minutes
        
        # 載入 BRAS Map（取得頻寬上限）
        self.bandwidth_limits = self.load_bandwidth_limits()
    
    def load_bandwidth_limits(self) -> Dict[str, int]:
        """
        從 BRAS-Map.txt 載入頻寬上限
        
        Returns:
            {circuit_id: bandwidth_mbps}
        """
        limits = {}
        
        if not os.path.exists(self.bras_map_file):
            return limits
        
        with open(self.bras_map_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split(',')
                if len(parts) >= 13:
                    bras_ip = parts[2]
                    slot = parts[10]
                    port = parts[11]
                    bandwidth_kbps = int(parts[12]) if parts[12].isdigit() else 0
                    
                    # 組合 circuit_id
                    circuit_id = f"{bras_ip}_{slot}_{port}"
                    
                    # 轉換為 Mbps
                    bandwidth_mbps = bandwidth_kbps // 1024 if bandwidth_kbps > 0 else 1000
                    limits[circuit_id] = bandwidth_mbps
        
        return limits
    
    def get_circuit_rrd_files(self) -> List[str]:
        """
        取得所有 Circuit RRD 檔案
        
        Returns:
            RRD 檔案路徑列表
        """
        pattern = os.path.join(self.rrd_circuit_dir, "**/*_circuit.rrd")
        rrd_files = glob.glob(pattern, recursive=True)
        return rrd_files
    
    def parse_circuit_id(self, rrd_file: str) -> Tuple[str, str, str]:
        """
        解析 Circuit ID
        格式: {IP}_{interface}_circuit.rrd
        
        Args:
            rrd_file: RRD 檔案路徑
            
        Returns:
            (bras_ip, interface, circuit_id)
        """
        basename = os.path.basename(rrd_file)
        name_parts = basename.replace('_circuit.rrd', '').split('_')
        
        if len(name_parts) < 5:
            return None, None, None
        
        # IP 部分
        bras_ip = '.'.join(name_parts[:4])
        
        # 介面部分
        interface = '_'.join(name_parts[4:])
        interface = interface.replace('-', '/')  # ge-1-2 -> ge/1/2
        
        # Circuit ID
        circuit_id = f"{bras_ip}_{interface}"
        
        return bras_ip, interface, circuit_id
    
    def analyze_circuit(self, rrd_file: str, days: int = 3) -> CircuitCongestionReport:
        """
        分析單一 Circuit
        
        Args:
            rrd_file: Circuit RRD 檔案
            days: 分析天數
            
        Returns:
            CircuitCongestionReport
        """
        bras_ip, interface, circuit_id = self.parse_circuit_id(rrd_file)
        
        if not circuit_id:
            return None
        
        # 取得頻寬上限
        bandwidth_limit = self.bandwidth_limits.get(circuit_id, 1000)
        
        # 計算時間範圍
        end_time = int(time.time())
        start_time = end_time - (days * 86400)
        
        try:
            # 讀取 RRD 資料
            result = rrdtool.fetch(
                rrd_file,
                'AVERAGE',
                '--start', str(start_time),
                '--end', str(end_time)
            )
            
            (fetch_start, fetch_end, fetch_step), ds_names, data = result
            
            # 處理資料
            records = []
            total_rate = 0
            peak_rate = 0
            valid_points = 0
            
            current_time = fetch_start
            for row in data:
                if row[0] is not None:  # total_traffic (bps)
                    rate_bps = row[0]
                    rate_mbps = rate_bps / 1000000
                    
                    # 計算擁塞比例
                    congestion_ratio = rate_mbps / bandwidth_limit
                    is_congested = congestion_ratio >= self.congestion_threshold
                    
                    record = CongestionRecord(
                        timestamp=current_time,
                        rate_mbps=rate_mbps,
                        limit_mbps=bandwidth_limit,
                        congestion_ratio=congestion_ratio,
                        is_congested=is_congested
                    )
                    records.append(record)
                    
                    total_rate += rate_mbps
                    peak_rate = max(peak_rate, rate_mbps)
                    valid_points += 1
                
                current_time += fetch_step
            
            # 計算擁塞時數
            congestion_hours, periods = self.calculate_congestion_hours(records, fetch_step)
            
            # 計算擁塞百分比
            total_hours = days * 24
            congestion_percentage = (congestion_hours / total_hours * 100) if total_hours > 0 else 0
            
            # 計算平均速率
            avg_rate = total_rate / valid_points if valid_points > 0 else 0
            
            # 每日統計
            daily_stats = self.calculate_daily_stats(records, fetch_step, days)
            
            return CircuitCongestionReport(
                circuit_id=circuit_id,
                bras_ip=bras_ip,
                interface=interface,
                area="",  # TODO: 從 BRAS-Map 取得
                bandwidth_limit_mbps=bandwidth_limit,
                analysis_days=days,
                peak_rate_mbps=peak_rate,
                avg_rate_mbps=avg_rate,
                congestion_hours=congestion_hours,
                congestion_percentage=congestion_percentage,
                daily_stats=daily_stats,
                congestion_periods=periods
            )
            
        except Exception as e:
            print(f"分析失敗 {rrd_file}: {e}")
            return None
    
    def calculate_congestion_hours(self, records: List[CongestionRecord], 
                                   step: int) -> Tuple[float, List[Dict]]:
        """
        計算連續擁塞時數
        
        Args:
            records: 擁塞記錄列表
            step: 時間間隔（秒）
            
        Returns:
            (總擁塞時數, 擁塞時段列表)
        """
        total_hours = 0
        periods = []
        
        current_period = None
        
        for record in records:
            if record.is_congested:
                if current_period is None:
                    # 開始新的擁塞時段
                    current_period = {
                        'start_time': record.timestamp,
                        'end_time': record.timestamp,
                        'peak_rate': record.rate_mbps,
                        'duration_minutes': 0
                    }
                else:
                    # 延續擁塞時段
                    current_period['end_time'] = record.timestamp
                    current_period['peak_rate'] = max(current_period['peak_rate'], 
                                                      record.rate_mbps)
            else:
                if current_period is not None:
                    # 結束擁塞時段
                    duration_minutes = (current_period['end_time'] - 
                                      current_period['start_time']) / 60
                    current_period['duration_minutes'] = duration_minutes
                    
                    # 只記錄超過最小時長的擁塞
                    if duration_minutes >= self.min_congestion_minutes:
                        periods.append(current_period)
                        total_hours += duration_minutes / 60
                    
                    current_period = None
        
        # 處理最後一個時段
        if current_period is not None:
            duration_minutes = (current_period['end_time'] - 
                              current_period['start_time']) / 60
            current_period['duration_minutes'] = duration_minutes
            
            if duration_minutes >= self.min_congestion_minutes:
                periods.append(current_period)
                total_hours += duration_minutes / 60
        
        return total_hours, periods
    
    def calculate_daily_stats(self, records: List[CongestionRecord], 
                             step: int, days: int) -> List[Dict]:
        """
        計算每日統計
        
        Args:
            records: 擁塞記錄列表
            step: 時間間隔（秒）
            days: 天數
            
        Returns:
            每日統計列表
        """
        daily_stats = []
        
        if not records:
            return daily_stats
        
        # 依日期分組
        date_groups = {}
        for record in records:
            date = datetime.fromtimestamp(record.timestamp).date()
            if date not in date_groups:
                date_groups[date] = []
            date_groups[date].append(record)
        
        # 計算每日統計
        for date in sorted(date_groups.keys()):
            day_records = date_groups[date]
            
            # 尖峰速率
            peak_rate = max(r.rate_mbps for r in day_records)
            
            # 平均速率
            avg_rate = sum(r.rate_mbps for r in day_records) / len(day_records)
            
            # 擁塞時數
            congested_count = sum(1 for r in day_records if r.is_congested)
            congestion_hours = congested_count * step / 3600
            
            # 擁塞比例
            congestion_ratio = (congested_count / len(day_records) * 100) if day_records else 0
            
            daily_stats.append({
                'date': date,
                'weekday': date.strftime('%a'),
                'peak_rate': peak_rate,
                'avg_rate': avg_rate,
                'congestion_hours': congestion_hours,
                'congestion_ratio': congestion_ratio
            })
        
        return daily_stats
    
    def analyze_all_circuits(self, days: int = 3) -> List[CircuitCongestionReport]:
        """
        分析所有 Circuit
        
        Args:
            days: 分析天數
            
        Returns:
            CircuitCongestionReport 列表
        """
        rrd_files = self.get_circuit_rrd_files()
        
        print(f"找到 {len(rrd_files)} 個 Circuit")
        print(f"分析最近 {days} 天的資料...")
        print()
        
        reports = []
        
        for rrd_file in rrd_files:
            report = self.analyze_circuit(rrd_file, days)
            if report and report.congestion_hours > 0:
                reports.append(report)
        
        # 依擁塞時數排序
        reports.sort(key=lambda r: r.congestion_hours, reverse=True)
        
        return reports
    
    def output_text(self, reports: List[CircuitCongestionReport], output_file: str = None):
        """輸出文字格式報表"""
        lines = []
        
        # 標題
        report_date = datetime.now().strftime('%Y/%m/%d')
        lines.append("=" * 80)
        lines.append(f"Circuit 擁塞分析報告 - {report_date}")
        lines.append("=" * 80)
        lines.append()
        
        for report in reports:
            lines.append(f"Circuit: {report.circuit_id}")
            lines.append("-" * 80)
            lines.append(f"  頻寬上限: {report.bandwidth_limit_mbps} Mbps")
            lines.append(f"  尖峰速率: {report.peak_rate_mbps:.1f} Mbps")
            lines.append(f"  平均速率: {report.avg_rate_mbps:.1f} Mbps")
            lines.append(f"  擁塞時數: {report.congestion_hours:.1f} 小時")
            lines.append(f"  擁塞比例: {report.congestion_percentage:.1f}%")
            lines.append()
            
            # 每日明細
            if report.daily_stats:
                lines.append("  每日明細:")
                for day in report.daily_stats:
                    lines.append(
                        f"    {day['date']} ({day['weekday']}): "
                        f"尖峰 {day['peak_rate']:.1f} Mbps, "
                        f"平均 {day['avg_rate']:.1f} Mbps, "
                        f"擁塞 {day['congestion_hours']:.1f} 小時 ({day['congestion_ratio']:.1f}%)"
                    )
                lines.append()
        
        lines.append("=" * 80)
        lines.append(f"擁塞定義: 流量 > {self.congestion_threshold*100}% 頻寬上限")
        lines.append(f"最小擁塞時間: {self.min_congestion_minutes} 分鐘")
        lines.append("=" * 80)
        
        output = '\n'.join(lines)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"報表已儲存: {output_file}")
        else:
            print(output)


def main():
    """主程式"""
    parser = argparse.ArgumentParser(description='Circuit 擁塞分析報表')
    parser.add_argument('--days', type=int, default=3, help='分析天數')
    parser.add_argument('--circuit-dir', default='/home/bulks_data/circuit',
                       help='Circuit RRD 目錄')
    parser.add_argument('--bras-map', default='BRAS-Map.txt',
                       help='BRAS-Map.txt 檔案')
    parser.add_argument('--threshold', type=float, default=0.95,
                       help='擁塞閾值（預設 0.95 = 95%%）')
    parser.add_argument('--format', choices=['text', 'html', 'csv'],
                       default='text', help='輸出格式')
    parser.add_argument('--output-dir', default='./reports',
                       help='輸出目錄')
    
    args = parser.parse_args()
    
    # 建立輸出目錄
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 初始化分析器
    analyzer = CongestionAnalyzer(
        args.circuit_dir,
        args.bras_map,
        args.threshold
    )
    
    # 分析所有 Circuit
    print("=" * 80)
    print("Circuit 擁塞分析")
    print("=" * 80)
    print()
    
    reports = analyzer.analyze_all_circuits(args.days)
    
    if not reports:
        print("沒有發現擁塞的 Circuit")
        return
    
    print(f"發現 {len(reports)} 個擁塞的 Circuit")
    print()
    
    # 輸出報表
    date_str = datetime.now().strftime('%Y%m%d')
    output_file = os.path.join(args.output_dir, f'congestion_{args.days}days_{date_str}.txt')
    
    analyzer.output_text(reports, output_file)
    
    print()
    print("完成！")


if __name__ == "__main__":
    main()
