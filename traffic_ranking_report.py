#!/usr/bin/env python3
# traffic_ranking_report.py - 流量排名報表產生器

import os
import sys
import time
import rrdtool
import argparse
from datetime import datetime, timedelta
from collections import defaultdict
import configparser
import glob
import re

# ========== 設定 ==========
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, 'config.ini')

# 讀取設定
config = configparser.ConfigParser()
if os.path.exists(CONFIG_FILE):
    config.read(CONFIG_FILE)
    RRD_BASE_DIR = config.get('rrd', 'base_dir', fallback='/home/bulks_data')
    MAP_FILE_DIR = config.get('paths', 'map_file_dir', fallback='/home/bulks_script')
else:
    RRD_BASE_DIR = '/home/bulks_data'
    MAP_FILE_DIR = '/home/bulks_script'

class TrafficRankingReport:
    def __init__(self, rrd_base_dir, map_file_dir):
        self.rrd_base_dir = rrd_base_dir
        self.map_file_dir = map_file_dir
        self.user_info_cache = {}
    
    def load_user_info(self, device_ip):
        """從 map 檔案載入用戶資訊"""
        if device_ip in self.user_info_cache:
            return self.user_info_cache[device_ip]
        
        map_file = os.path.join(self.map_file_dir, f'map_{device_ip}.txt')
        user_info = {}
        
        if not os.path.exists(map_file):
            print(f"⚠️  找不到 map 檔案: {map_file}")
            return user_info
        
        try:
            with open(map_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split(',')
                    if len(parts) >= 4:
                        user_code = parts[0].strip()
                        slot_port_vci = parts[1].strip()
                        speed_spec = parts[2].strip()
                        
                        # 解析 slot_port_vpi_vci
                        spv_parts = slot_port_vci.split('_')
                        if len(spv_parts) == 4:
                            slot = spv_parts[0]
                            port = spv_parts[1]
                            vlan = spv_parts[3]
                            
                            key = f"{device_ip}_{slot}_{port}_{vlan}"
                            user_info[key] = {
                                'user_code': user_code,
                                'speed_spec': speed_spec,
                                'slot': slot,
                                'port': port,
                                'vlan': vlan
                            }
        
        except Exception as e:
            print(f"讀取 map 檔案失敗: {e}")
        
        self.user_info_cache[device_ip] = user_info
        return user_info
    
    def parse_rrd_filename(self, rrd_path):
        """
        解析 RRD 檔名
        格式: {IP}_{slot}_{port}_{down}_{up}_{vlan}.rrd
        """
        filename = os.path.basename(rrd_path)
        
        # 移除 .rrd
        filename = filename.replace('.rrd', '')
        
        # 分割
        parts = filename.split('_')
        
        if len(parts) >= 6:
            # IP 可能包含點，需要重組
            # 格式: 61.64.191.166_1_2_20480_5120_3342
            # 最後6個部分：IP最後段_slot_port_down_up_vlan
            ip_parts = parts[:-5]  # IP 的所有部分
            device_ip = '_'.join(ip_parts).replace('_', '.')
            
            slot = parts[-5]
            port = parts[-4]
            download_kbps = parts[-3]
            upload_kbps = parts[-2]
            vlan = parts[-1]
            
            return {
                'device_ip': device_ip,
                'slot': slot,
                'port': port,
                'download_kbps': int(download_kbps),
                'upload_kbps': int(upload_kbps),
                'vlan': vlan
            }
        
        return None
    
    def get_traffic_from_rrd(self, rrd_path, start_time, end_time):
        """
        從 RRD 取得指定時間範圍的總流量（bytes）
        """
        try:
            # Fetch 資料
            result = rrdtool.fetch(
                rrd_path,
                'AVERAGE',
                '--start', str(start_time),
                '--end', str(end_time)
            )
            
            (fetch_start, fetch_end, fetch_step), ds_names, data = result
            
            # 計算總流量
            total_bits = 0
            data_points = 0
            
            for row in data:
                if row[0] is not None:
                    # COUNTER 類型儲存的是速率（bits/sec）
                    # 總流量 = 速率 * 時間間隔
                    total_bits += row[0] * fetch_step
                    data_points += 1
            
            # 轉換為 bytes
            total_bytes = total_bits / 8
            
            return {
                'total_bytes': int(total_bytes),
                'total_gb': total_bytes / (1024**3),
                'data_points': data_points
            }
        
        except Exception as e:
            print(f"讀取 RRD 失敗 {os.path.basename(rrd_path)}: {e}")
            return None
    
    def find_user_rrds(self, device_ip=None):
        """找出所有用戶 RRD 檔案"""
        rrd_files = []
        
        if device_ip:
            # 指定設備
            pattern = os.path.join(self.rrd_base_dir, device_ip, '*.rrd')
            rrd_files = glob.glob(pattern)
        else:
            # 所有設備
            for device_dir in glob.glob(os.path.join(self.rrd_base_dir, '*')):
                if os.path.isdir(device_dir):
                    device_ip_from_dir = os.path.basename(device_dir)
                    # 排除 sum 和 sum2m 目錄
                    if device_ip_from_dir not in ['sum', 'sum2m']:
                        pattern = os.path.join(device_dir, '*.rrd')
                        rrd_files.extend(glob.glob(pattern))
        
        return rrd_files
    
    def generate_ranking_report(self, period='day', top_n=100, device_ip=None, output_format='text'):
        """
        產生流量排名報表
        
        Args:
            period: 'day', 'week', 'month'
            top_n: 顯示前 N 名
            device_ip: 指定設備 IP（None = 所有設備）
            output_format: 'text', 'csv', 'html'
        """
        print("=" * 80)
        print("流量排名報表產生器")
        print("=" * 80)
        
        # 計算時間範圍
        now = datetime.now()
        
        if period == 'day':
            # 昨天 00:00 到今天 00:00
            end_time = datetime(now.year, now.month, now.day)
            start_time = end_time - timedelta(days=1)
            period_name = "日"
        elif period == 'week':
            # 上週一 00:00 到本週一 00:00
            days_since_monday = now.weekday()
            this_monday = datetime(now.year, now.month, now.day) - timedelta(days=days_since_monday)
            end_time = this_monday
            start_time = end_time - timedelta(days=7)
            period_name = "週"
        elif period == 'month':
            # 上個月 1日 00:00 到這個月 1日 00:00
            first_day_this_month = datetime(now.year, now.month, 1)
            end_time = first_day_this_month
            
            # 上個月第一天
            if now.month == 1:
                start_time = datetime(now.year - 1, 12, 1)
            else:
                start_time = datetime(now.year, now.month - 1, 1)
            period_name = "月"
        else:
            # 今天 00:00 到昨天 00:00
            start_time = datetime(now.year, now.month, now.day)+timedelta(days=1)
            end_time = start_time + timedelta(days=2)
            period_name = "日"
            #print("錯誤：period 必須是 'day', 'week', 或 'month'")
            return
        
        start_timestamp = int(start_time.timestamp())
        end_timestamp = int(end_time.timestamp())
        
        print(f"統計期間: {period_name}")
        print(f"  開始: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  結束: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  設備: {device_ip if device_ip else '所有設備'}")
        print()
        
        # 找出所有 RRD 檔案
        print("掃描 RRD 檔案...")
        rrd_files = self.find_user_rrds(device_ip)
        print(f"找到 {len(rrd_files)} 個 RRD 檔案")
        print()
        
        # 收集流量資料
        print("收集流量資料...")
        user_traffic = []
        processed = 0
        
        for rrd_path in rrd_files:
            processed += 1
            if processed % 100 == 0:
                print(f"  進度: {processed}/{len(rrd_files)}")
            
            # 解析檔名
            rrd_info = self.parse_rrd_filename(rrd_path)
            if not rrd_info:
                continue
            
            # 取得流量
            traffic_data = self.get_traffic_from_rrd(rrd_path, start_timestamp, end_timestamp)
            if not traffic_data or traffic_data['total_bytes'] == 0:
                continue
            
            # 取得用戶資訊
            user_info_map = self.load_user_info(rrd_info['device_ip'])
            key = f"{rrd_info['device_ip']}_{rrd_info['slot']}_{rrd_info['port']}_{rrd_info['vlan']}"
            
            user_info = user_info_map.get(key, {})
            user_code = user_info.get('user_code', f"VLAN{rrd_info['vlan']}")
            
            user_traffic.append({
                'user_code': user_code,
                'device_ip': rrd_info['device_ip'],
                'slot': rrd_info['slot'],
                'port': rrd_info['port'],
                'vlan': rrd_info['vlan'],
                'speed_spec': user_info.get('speed_spec', f"{rrd_info['download_kbps']}_{rrd_info['upload_kbps']}"),
                'total_bytes': traffic_data['total_bytes'],
                'total_gb': traffic_data['total_gb'],
                'data_points': traffic_data['data_points']
            })
        
        print(f"✓ 收集完成，有效數據: {len(user_traffic)} 筆")
        print()
        
        # 排序
        user_traffic.sort(key=lambda x: x['total_bytes'], reverse=True)
        
        # 輸出報表
        if output_format == 'text':
            self.output_text_report(user_traffic[:top_n], period_name, start_time, end_time)
        elif output_format == 'csv':
            self.output_csv_report(user_traffic[:top_n], period_name, start_time, end_time)
        elif output_format == 'html':
            self.output_html_report(user_traffic[:top_n], period_name, start_time, end_time)
        
        return user_traffic[:top_n]
    
    def output_text_report(self, data, period_name, start_time, end_time):
        """輸出文字格式報表"""
        print("=" * 120)
        print(f"流量排名報表 - {period_name}")
        print(f"統計期間: {start_time.strftime('%Y-%m-%d')} ~ {end_time.strftime('%Y-%m-%d')}")
        print("=" * 120)
        print()
        
        # 表頭
        print(f"{'排名':<6} {'用戶代碼':<15} {'設備IP':<16} {'Slot':<5} {'Port':<5} {'VLAN':<6} {'速率':<12} {'流量(GB)':<12} {'流量(MB)':<12}")
        print("-" * 120)
        
        # 資料
        for i, user in enumerate(data, 1):
            print(f"{i:<6} {user['user_code']:<15} {user['device_ip']:<16} "
                  f"{user['slot']:<5} {user['port']:<5} {user['vlan']:<6} "
                  f"{user['speed_spec']:<12} {user['total_gb']:>10.2f}  {user['total_gb']*1024:>10.2f}")
        
        print()
        print("=" * 120)
        
        # 統計
        total_traffic_gb = sum(u['total_gb'] for u in data)
        print(f"前 {len(data)} 名總流量: {total_traffic_gb:.2f} GB ({total_traffic_gb/1024:.2f} TB)")
        print()
    
    def output_csv_report(self, data, period_name, start_time, end_time):
        """輸出 CSV 格式報表"""
        filename = f"traffic_ranking_{period_name}_{start_time.strftime('%Y%m%d')}.csv"
        
        with open(filename, 'w', encoding='utf-8') as f:
            # 標題
            f.write(f"# 流量排名報表 - {period_name}\n")
            f.write(f"# 統計期間: {start_time.strftime('%Y-%m-%d')} ~ {end_time.strftime('%Y-%m-%d')}\n")
            f.write(f"# 產生時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("\n")
            
            # 表頭
            f.write("排名,用戶代碼,設備IP,Slot,Port,VLAN,速率規格,流量(GB),流量(MB),流量(Bytes)\n")
            
            # 資料
            for i, user in enumerate(data, 1):
                f.write(f"{i},{user['user_code']},{user['device_ip']},"
                       f"{user['slot']},{user['port']},{user['vlan']},"
                       f"{user['speed_spec']},{user['total_gb']:.2f},"
                       f"{user['total_gb']*1024:.2f},{user['total_bytes']}\n")
        
        print(f"✓ CSV 報表已儲存: {filename}")
    
    def output_html_report(self, data, period_name, start_time, end_time):
        """輸出 HTML 格式報表"""
        filename = f"traffic_ranking_{period_name}_{start_time.strftime('%Y%m%d')}.html"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>流量排名報表</title>
    <style>
        body {
            font-family: Arial, "Microsoft JhengHei", sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }
        .info {
            background-color: #e7f3ff;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th {
            background-color: #4CAF50;
            color: white;
            padding: 12px;
            text-align: left;
            position: sticky;
            top: 0;
        }
        td {
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .rank-1 { background-color: #ffd700 !important; }
        .rank-2 { background-color: #c0c0c0 !important; }
        .rank-3 { background-color: #cd7f32 !important; }
        .summary {
            margin-top: 20px;
            padding: 15px;
            background-color: #f9f9f9;
            border-left: 4px solid #4CAF50;
        }
        .text-right { text-align: right; }
    </style>
</head>
<body>
    <div class="container">
""")
            
            f.write(f"        <h1>流量排名報表 - {period_name}</h1>\n")
            f.write(f"""
        <div class="info">
            <strong>統計期間:</strong> {start_time.strftime('%Y-%m-%d')} ~ {end_time.strftime('%Y-%m-%d')}<br>
            <strong>產生時間:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
            <strong>排名數量:</strong> 前 {len(data)} 名
        </div>
""")
            
            f.write("""
        <table>
            <thead>
                <tr>
                    <th>排名</th>
                    <th>用戶代碼</th>
                    <th>設備IP</th>
                    <th>Slot</th>
                    <th>Port</th>
                    <th>VLAN</th>
                    <th>速率規格</th>
                    <th class="text-right">流量 (GB)</th>
                    <th class="text-right">流量 (MB)</th>
                </tr>
            </thead>
            <tbody>
""")
            
            for i, user in enumerate(data, 1):
                rank_class = ''
                if i == 1:
                    rank_class = 'rank-1'
                elif i == 2:
                    rank_class = 'rank-2'
                elif i == 3:
                    rank_class = 'rank-3'
                
                f.write(f"""
                <tr class="{rank_class}">
                    <td>{i}</td>
                    <td>{user['user_code']}</td>
                    <td>{user['device_ip']}</td>
                    <td>{user['slot']}</td>
                    <td>{user['port']}</td>
                    <td>{user['vlan']}</td>
                    <td>{user['speed_spec']}</td>
                    <td class="text-right">{user['total_gb']:.2f}</td>
                    <td class="text-right">{user['total_gb']*1024:.2f}</td>
                </tr>
""")
            
            total_traffic_gb = sum(u['total_gb'] for u in data)
            
            f.write(f"""
            </tbody>
        </table>
        
        <div class="summary">
            <strong>統計摘要:</strong><br>
            前 {len(data)} 名總流量: {total_traffic_gb:.2f} GB ({total_traffic_gb/1024:.2f} TB)
        </div>
    </div>
</body>
</html>
""")
        
        print(f"✓ HTML 報表已儲存: {filename}")

def main():
    parser = argparse.ArgumentParser(
        description='ISP 流量排名報表產生器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 產生昨日流量前100名報表
  python3 traffic_ranking_report.py --period day
  
  # 產生上週流量前50名報表（CSV格式）
  python3 traffic_ranking_report.py --period week --top 50 --format csv
  
  # 產生上月指定設備的流量前100名報表（HTML格式）
  python3 traffic_ranking_report.py --period month --device 61.64.191.166 --format html
  
  # 產生所有格式的報表
  python3 traffic_ranking_report.py --period day --format all
        """
    )
    
    parser.add_argument(
        '--period',
        choices=['day', 'week', 'month'],
        default='day',
        help='統計週期: day=昨日, week=上週, month=上月 (預設: day)'
    )
    
    parser.add_argument(
        '--top',
        type=int,
        default=100,
        help='顯示前 N 名 (預設: 100)'
    )
    
    parser.add_argument(
        '--device',
        help='指定設備 IP (預設: 所有設備)'
    )
    
    parser.add_argument(
        '--format',
        choices=['text', 'csv', 'html', 'all'],
        default='text',
        help='輸出格式 (預設: text)'
    )
    
    parser.add_argument(
        '--rrd-dir',
        default=RRD_BASE_DIR,
        help=f'RRD 基礎目錄 (預設: {RRD_BASE_DIR})'
    )
    
    parser.add_argument(
        '--map-dir',
        default=MAP_FILE_DIR,
        help=f'Map 檔案目錄 (預設: {MAP_FILE_DIR})'
    )
    
    args = parser.parse_args()
    
    # 建立報表產生器
    reporter = TrafficRankingReport(args.rrd_dir, args.map_dir)
    
    # 產生報表
    if args.format == 'all':
        for fmt in ['text', 'csv', 'html']:
            print()
            reporter.generate_ranking_report(
                period=args.period,
                top_n=args.top,
                device_ip=args.device,
                output_format=fmt
            )
    else:
        reporter.generate_ranking_report(
            period=args.period,
            top_n=args.top,
            device_ip=args.device,
            output_format=args.format
        )

if __name__ == '__main__':
    main()
