#!/usr/bin/env python3
"""
collector_mx240.py - MX240 設備收集器

MX240 特性:
- DeviceType: 3
- 介面格式: ge-fpc/pic/port:vci
- Dynamic IP with PPPoE 支援
- 標準 SNMP timeout (5s)
"""

import sys
import os
import logging
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from collectors.base_collector import BaseCollector, UserData

logger = logging.getLogger(__name__)


class MX240Collector(BaseCollector):
    """MX240 收集器"""
    
    def __init__(self, device_ip: str, map_file: str, config=None):
        super().__init__(device_ip, device_type=1, map_file=map_file, config=config)
    
    def build_interface_name(self, user: UserData) -> str:
        """
        建立 MX240 介面名稱
        
        格式: ge-fpc/pic/port:vci
        範例: ge-1/0/2:3490
        
        Note:
            MX 系列格式: slot=fpc, vpi=pic
        """
        interface_type = 'ge'  # 預設使用 GE
        
        # MX 系列格式: ge-fpc/pic/port:vci
        return f"{interface_type}-{user.slot}/{user.vpi}/{user.port}:{user.vci}"


def main():
    parser = argparse.ArgumentParser(
        description='MX240 流量收集器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  python3 collector_mx240.py --ip 61.64.191.74 --map ../config/maps/map_61.64.191.74.txt
  python3 collector_mx240.py --ip 61.64.191.74 --map /path/to/map.txt --debug
        """
    )
    
    parser.add_argument('--ip', required=True, help='設備 IP 位址')
    parser.add_argument('--map', required=True, help='Map 檔案路徑')
    parser.add_argument('--config', help='配置檔案路徑（選用）')
    parser.add_argument('--debug', action='store_true', help='啟用除錯模式')
    
    args = parser.parse_args()
    
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("="*60)
    logger.info("MX240 流量收集器啟動")
    logger.info(f"設備 IP: {args.ip}")
    logger.info(f"Map 檔案: {args.map}")
    logger.info("="*60)
    
    try:
        from core.config_loader import ConfigLoader
        config = ConfigLoader(args.config) if args.config else ConfigLoader()
        
        collector = MX240Collector(args.ip, args.map, config)
        success = collector.run()
        
        stats = collector.stats
        logger.info("\n" + "="*60)
        logger.info("收集統計")
        logger.info("="*60)
        logger.info(f"總用戶數: {stats.total}")
        logger.info(f"成功: {stats.success}")
        logger.info(f"失敗: {stats.failed}")
        logger.info(f"耗時: {stats.duration:.1f} 秒")
        logger.info(f"成功率: {stats.success_rate:.1f}%")
        logger.info("="*60)
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.warning("\n收集被用戶中斷")
        sys.exit(130)
    except Exception as e:
        logger.error(f"收集器執行失敗: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
