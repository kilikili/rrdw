#!/usr/bin/env python3
"""
collector_e320.py - E320 設備收集器

E320 特性:
- DeviceType: 1
- 介面格式: ge-slot/port/pic.vci 或 xe-slot/port/pic.vci
- 較慢的 SNMP 回應，需要較長 timeout (10s)
- Legacy BRAS 設備
"""

import sys
import os
import logging
import argparse

# 添加父目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from collectors.base_collector import BaseCollector, UserData

logger = logging.getLogger(__name__)


class E320Collector(BaseCollector):
    """E320 收集器"""
    
    def __init__(self, device_ip: str, map_file: str, config=None):
        """
        初始化 E320 收集器
        
        Args:
            device_ip: 設備 IP
            map_file: Map 檔案路徑
            config: 配置載入器
        """
        super().__init__(device_ip, device_type=3, map_file=map_file, config=config)
    
    def build_interface_name(self, user: UserData) -> str:
        """
        建立 E320 介面名稱
        
        格式: ge-slot/port/pic.vci
        範例: ge-1/2/0.3490
        
        Args:
            user: 用戶資料
        
        Returns:
            介面名稱
        """
        # E320 介面格式: ge-slot/port/pic.vci
        # 可能是 GE 或 XE，這裡假設是 GE，如果需要可以從 map 檔案擴展
        interface_type = 'ge'  # 預設使用 GE
        
        return f"{interface_type}-{user.slot}/{user.port}/{user.vpi}.{user.vci}"


def main():
    """主程式"""
    # 參數解析
    parser = argparse.ArgumentParser(
        description='E320 流量收集器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  python3 collector_e320.py --ip 61.64.191.78 --map /path/to/map_61.64.191.78.txt
  python3 collector_e320.py --ip 61.64.191.78 --map ../config/maps/map_61.64.191.78.txt --debug
        """
    )
    
    parser.add_argument('--ip', required=True, help='設備 IP 位址')
    parser.add_argument('--map', required=True, help='Map 檔案路徑')
    parser.add_argument('--config', help='配置檔案路徑（選用）')
    parser.add_argument('--debug', action='store_true', help='啟用除錯模式')
    
    args = parser.parse_args()
    
    # 設定日誌
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("="*60)
    logger.info("E320 流量收集器啟動")
    logger.info(f"設備 IP: {args.ip}")
    logger.info(f"Map 檔案: {args.map}")
    logger.info("="*60)
    
    try:
        # 建立收集器
        from core.config_loader import ConfigLoader
        config = ConfigLoader(args.config) if args.config else ConfigLoader()
        
        collector = E320Collector(args.ip, args.map, config)
        
        # 執行收集
        success = collector.run()
        
        # 顯示統計
        stats = collector.stats
        logger.info("\n" + "="*60)
        logger.info("收集統計")
        logger.info("="*60)
        logger.info(f"總用戶數: {stats.total}")
        logger.info(f"成功: {stats.success}")
        logger.info(f"失敗: {stats.failed}")
        logger.info(f"跳過: {stats.skipped}")
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
