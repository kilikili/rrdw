#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOP100 Traffic Ranking Report
TOP100 流量統計報表

功能：
- 統計指定期間的客戶流量
- 產生 TOP100 排名
- 支援日/週/月報表
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
class UserTrafficReport:
    """使用者流量報表資料"""
    user_code: str
    bras_ip: str
    slot: int
    port: int
    vlan: int
    speed_profile: str
    download_gb: float
    upload_gb: float
    total_gb: float
    rrd_file: str
    
    def to_dict(self) -> Dict:
        """轉為字典"""
        return {
            'user_code': self.user_code,
            'bras_ip': self.bras_ip,
            'slot': self.slot,
            'port': self.port,
            'vlan': self.vlan,
            'speed_profile': self.speed_profile,
            'download_gb': self.download_gb,
            'upload_gb': self.upload_gb,
            'total_gb': self.total_gb
        }


class TrafficRankingReport:
    """流量排名報表系統"""
    
    def __init__(self, rrd_base_dir: str = "/home/bulks_data"):
        """
        初始化報表系統
        
        Args:
            rrd_base_dir: RRD 基礎目錄
        """
        self.rrd_base_dir = rrd_base_dir
    
    def get_time_range(self, period: str) -> Tuple[int, int]:
        """
        取得時間範圍
        
        Args:
            period: 'daily', 'weekly', 'monthly'
            
        Returns:
            (start_time, end_time) Unix timestamp
        """
        now = datetime.now()
        end_time = int(now.timestamp())
        
        if period == 'daily':
            # 昨天 00:00 到今天 00:00
            start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
            start_time = int(start.timestamp())
        elif period == 'weekly':
            # 上週一到本週一
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            start = start - timedelta(days=start.weekday() + 7)
            start_time = int(start.timestamp())
        elif period == 'monthly':
            # 上月 1 日到本月 1 日
            if now.month == 1:
                start = now.replace(year=now.year-1, month=12, day=1, 
                                  hour=0, minute=0, second=0, microsecond=0)
            else:
                start = now.replace(month=now.month-1, day=1,
                                  hour=0, minute=0, second=0, microsecond=0)
            start_time = int(start.timestamp())
        else:
            raise ValueError(f"未知的期間類型: {period}")
        
        return start_time, end_time
    
    def parse_rrd_filename(self, rrd_file: str) -> Dict:
        """
        解析 RRD 檔案名稱
        格式: {IP}_{slot}_{port}_{download}_{upload}_{vlan}.rrd
        
        Args:
            rrd_file: RRD 檔案路徑
            
        Returns:
            解析後的資訊字典
        """
        basename = os.path.basename(rrd_file)
        name_parts = basename.replace('.rrd', '').split('_')
        
        if len(name_parts) < 6:
            return None
        
        try:
            # 處理 IP 可能有多個部分
            ip_parts = []
            i = 0
            while i < len(name_parts):
                if name_parts[i].isdigit() and len(name_parts[i]) <= 3:
                    # 這是 IP 的一部分
                    ip_parts.append(name_parts[i])
                    i += 1
                    if len(ip_parts) == 4:
                        break
                else:
                    break
            
            if len(ip_parts) != 4:
                return None
            
            bras_ip = '.'.join(ip_parts)
            
            # 剩餘部分
            remaining = name_parts[4:]
            if len(remaining) < 5:
                return None
            
            return {
                'bras_ip': bras_ip,
                'slot': int(remaining[0]),
                'port': int(remaining[1]),
                'download': int(remaining[2]),
                'upload': int(remaining[3]),
                'vlan': int(remaining[4])
            }
        except (ValueError, IndexError):
            return None
    
    def get_user_code_from_map(self, bras_ip: str, vlan: int) -> str:
        """
        從 Map File 取得使用者代碼
        (簡化版，實際應該從資料庫或 Map File 查詢)
        
        Args:
            bras_ip: BRAS IP
            vlan: VLAN ID
            
        Returns:
            使用者代碼
        """
        # TODO: 實際應該查詢 Map File 或資料庫
        return f"user_{vlan}"
    
    def calculate_traffic(self, rrd_file: str, start_time: int, end_time: int) -> float:
        """
        計算指定時間範圍的總流量 (GB)
        
        Args:
            rrd_file: RRD 檔案路徑
            start_time: 開始時間
            end_time: 結束時間
            
        Returns:
            總流量 (GB)
        """
        try:
            # 讀取 RRD 資料
            result = rrdtool.fetch(
                rrd_file,
                'AVERAGE',
                '--start', str(start_time),
                '--end', str(end_time)
            )
            
            (fetch_start, fetch_end, fetch_step), ds_names, data = result
            
            # 累計流量 (bits)
            total_bits = 0
            for row in data:
                if row[0] is not None:
                    # row[0] 是 bps (bits per second)
                    # 乘以 step 得到這段時間的總 bits
                    total_bits += row[0] * fetch_step
            
            # 轉換為 GB (bits / 8 / 1024 / 1024 / 1024)
            total_gb = total_bits / 8 / 1024 / 1024 / 1024
            
            return total_gb
            
        except Exception as e:
            print(f"計算流量失敗 {rrd_file}: {e}")
            return 0.0
    
    def collect_all_users(self, period: str) -> List[UserTrafficReport]:
        """
        收集所有使用者的流量資料
        
        Args:
            period: 時間期間
            
        Returns:
            UserTrafficReport 列表
        """
        start_time, end_time = self.get_time_range(period)
        
        print(f"收集流量資料: {period}")
        print(f"時間範圍: {datetime.fromtimestamp(start_time)} ~ {datetime.fromtimestamp(end_time)}")
        print()
        
        users = []
        
        # 掃描所有使用者 RRD
        pattern = os.path.join(self.rrd_base_dir, "**/*.rrd")
        rrd_files = glob.glob(pattern, recursive=True)
        
        # 排除 sum, sum2m, circuit 目錄
        rrd_files = [f for f in rrd_files 
                    if '/sum/' not in f and '/sum2m/' not in f and '/circuit/' not in f]
        
        print(f"找到 {len(rrd_files)} 個 RRD 檔案")
        print("計算流量中...")
        
        processed = 0
        for rrd_file in rrd_files:
            # 解析檔名
            info = self.parse_rrd_filename(rrd_file)
            if not info:
                continue
            
            # 計算流量
            total_gb = self.calculate_traffic(rrd_file, start_time, end_time)
            
            if total_gb > 0:
                # 取得使用者代碼
                user_code = self.get_user_code_from_map(info['bras_ip'], info['vlan'])
                
                # 建立報表資料
                # 注意：這裡假設下載 = 總流量，上傳 = 0
                # 實際應該分別計算入/出流量
                user = UserTrafficReport(
                    user_code=user_code,
                    bras_ip=info['bras_ip'],
                    slot=info['slot'],
                    port=info['port'],
                    vlan=info['vlan'],
                    speed_profile=f"{info['download']}_{info['upload']}",
                    download_gb=total_gb,
                    upload_gb=0.0,  # TODO: 實際應計算上傳流量
                    total_gb=total_gb,
                    rrd_file=rrd_file
                )
                users.append(user)
            
            processed += 1
            if processed % 1000 == 0:
                print(f"  已處理: {processed}/{len(rrd_files)}")
        
        print(f"完成！找到 {len(users)} 個有流量的使用者")
        return users
    
    def generate_top100(self, users: List[UserTrafficReport], top_n: int = 100) -> List[UserTrafficReport]:
        """
        產生 TOP N 排名
        
        Args:
            users: 使用者列表
            top_n: 前 N 名
            
        Returns:
            排序後的 TOP N 使用者
        """
        # 依總流量排序
        users.sort(key=lambda u: u.total_gb, reverse=True)
        return users[:top_n]
    
    def output_text(self, top_users: List[UserTrafficReport], period: str, output_file: str = None):
        """
        輸出文字格式報表
        
        Args:
            top_users: TOP 使用者列表
            period: 時間期間
            output_file: 輸出檔案（None 則輸出到 stdout）
        """
        # 建立輸出內容
        lines = []
        
        # 標題
        period_name = {'daily': '日報', 'weekly': '週報', 'monthly': '月報'}.get(period, period)
        report_date = datetime.now().strftime('%Y年%m月%d日')
        
        lines.append("=" * 80)
        lines.append(f"TOP100 客戶流量統計 - {report_date} ({period_name})")
        lines.append("=" * 80)
        lines.append("")
        
        # 表頭
        lines.append(f"{'排名':^4} {'用戶代碼':^15} {'BRAS IP':^15} {'速率方案':^15} "
                    f"{'下載(GB)':>12} {'上傳(GB)':>12} {'總計(GB)':>12}")
        lines.append("=" * 80)
        
        # 資料
        for i, user in enumerate(top_users, 1):
            download_kbps, upload_kbps = map(int, user.speed_profile.split('_'))
            speed_display = f"{download_kbps//1024}M/{upload_kbps//1024}M"
            
            lines.append(
                f"{i:4d} {user.user_code:15s} {user.bras_ip:15s} {speed_display:15s} "
                f"{user.download_gb:12.2f} {user.upload_gb:12.2f} {user.total_gb:12.2f}"
            )
        
        lines.append("=" * 80)
        
        # 統計摘要
        total_traffic = sum(u.total_gb for u in top_users)
        lines.append(f"\nTOP100 總流量: {total_traffic:,.2f} GB")
        lines.append(f"平均流量: {total_traffic/len(top_users):,.2f} GB/戶")
        lines.append("")
        
        # 輸出
        output = '\n'.join(lines)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"報表已儲存: {output_file}")
        else:
            print(output)
    
    def output_csv(self, top_users: List[UserTrafficReport], output_file: str):
        """
        輸出 CSV 格式報表
        
        Args:
            top_users: TOP 使用者列表
            output_file: 輸出檔案
        """
        import csv
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 表頭
            writer.writerow([
                '排名', '用戶代碼', 'BRAS IP', 'Slot', 'Port', 'VLAN',
                '速率方案', '下載(GB)', '上傳(GB)', '總計(GB)'
            ])
            
            # 資料
            for i, user in enumerate(top_users, 1):
                writer.writerow([
                    i,
                    user.user_code,
                    user.bras_ip,
                    user.slot,
                    user.port,
                    user.vlan,
                    user.speed_profile,
                    f"{user.download_gb:.2f}",
                    f"{user.upload_gb:.2f}",
                    f"{user.total_gb:.2f}"
                ])
        
        print(f"CSV 報表已儲存: {output_file}")
    
    def output_html(self, top_users: List[UserTrafficReport], period: str, output_file: str):
        """
        輸出 HTML 格式報表
        
        Args:
            top_users: TOP 使用者列表
            period: 時間期間
            output_file: 輸出檔案
        """
        period_name = {'daily': '日報', 'weekly': '週報', 'monthly': '月報'}.get(period, period)
        report_date = datetime.now().strftime('%Y年%m月%d日')
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>TOP100 客戶流量統計 - {report_date}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; text-align: center; }}
        .meta {{ text-align: center; color: #666; margin-bottom: 20px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        tr:hover {{ background-color: #ddd; }}
        .rank {{ text-align: center; font-weight: bold; }}
        .number {{ text-align: right; }}
        .summary {{ margin-top: 20px; padding: 15px; background-color: #f9f9f9; border-left: 4px solid #4CAF50; }}
    </style>
</head>
<body>
    <h1>TOP100 客戶流量統計</h1>
    <div class="meta">
        <p>{report_date} ({period_name})</p>
    </div>
    
    <table>
        <thead>
            <tr>
                <th class="rank">排名</th>
                <th>用戶代碼</th>
                <th>BRAS IP</th>
                <th>Slot</th>
                <th>Port</th>
                <th>VLAN</th>
                <th>速率方案</th>
                <th class="number">下載 (GB)</th>
                <th class="number">上傳 (GB)</th>
                <th class="number">總計 (GB)</th>
            </tr>
        </thead>
        <tbody>
"""
        
        for i, user in enumerate(top_users, 1):
            download_kbps, upload_kbps = map(int, user.speed_profile.split('_'))
            speed_display = f"{download_kbps//1024}M/{upload_kbps//1024}M"
            
            html += f"""            <tr>
                <td class="rank">{i}</td>
                <td>{user.user_code}</td>
                <td>{user.bras_ip}</td>
                <td>{user.slot}</td>
                <td>{user.port}</td>
                <td>{user.vlan}</td>
                <td>{speed_display}</td>
                <td class="number">{user.download_gb:,.2f}</td>
                <td class="number">{user.upload_gb:,.2f}</td>
                <td class="number">{user.total_gb:,.2f}</td>
            </tr>
"""
        
        total_traffic = sum(u.total_gb for u in top_users)
        avg_traffic = total_traffic / len(top_users)
        
        html += f"""        </tbody>
    </table>
    
    <div class="summary">
        <h3>統計摘要</h3>
        <p><strong>TOP100 總流量:</strong> {total_traffic:,.2f} GB</p>
        <p><strong>平均流量:</strong> {avg_traffic:,.2f} GB/戶</p>
        <p><strong>產生時間:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>
"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"HTML 報表已儲存: {output_file}")


def main():
    """主程式"""
    parser = argparse.ArgumentParser(description='TOP100 流量統計報表')
    parser.add_argument('--period', choices=['daily', 'weekly', 'monthly'],
                       default='daily', help='統計期間')
    parser.add_argument('--rrd-dir', default='/home/bulks_data',
                       help='RRD 基礎目錄')
    parser.add_argument('--top-n', type=int, default=100,
                       help='TOP N 排名')
    parser.add_argument('--format', choices=['text', 'csv', 'html', 'all'],
                       default='text', help='輸出格式')
    parser.add_argument('--output-dir', default='./reports',
                       help='輸出目錄')
    
    args = parser.parse_args()
    
    # 建立輸出目錄
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 初始化報表系統
    reporter = TrafficRankingReport(args.rrd_dir)
    
    # 收集資料
    print("=" * 80)
    print("TOP100 流量統計報表")
    print("=" * 80)
    print()
    
    users = reporter.collect_all_users(args.period)
    
    if not users:
        print("沒有找到流量資料")
        return
    
    # 產生 TOP N
    top_users = reporter.generate_top100(users, args.top_n)
    
    print()
    print(f"產生 TOP{args.top_n} 報表...")
    print()
    
    # 輸出報表
    date_str = datetime.now().strftime('%Y%m%d')
    
    if args.format == 'text' or args.format == 'all':
        output_file = os.path.join(args.output_dir, f'top{args.top_n}_{args.period}_{date_str}.txt')
        reporter.output_text(top_users, args.period, output_file)
    
    if args.format == 'csv' or args.format == 'all':
        output_file = os.path.join(args.output_dir, f'top{args.top_n}_{args.period}_{date_str}.csv')
        reporter.output_csv(top_users, output_file)
    
    if args.format == 'html' or args.format == 'all':
        output_file = os.path.join(args.output_dir, f'top{args.top_n}_{args.period}_{date_str}.html')
        reporter.output_html(top_users, args.period, output_file)
    
    print()
    print("完成！")


if __name__ == "__main__":
    main()
