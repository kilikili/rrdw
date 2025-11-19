#!/usr/bin/env python3
"""collector_acx7024.py - ACX7024 設備收集器
DeviceType: 4 - Fixed IP Services
介面格式: ge-fpc/pic/port:vci
"""
import sys, os, logging, argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from collectors.base_collector import BaseCollector, UserData
logger = logging.getLogger(__name__)

class ACX7024Collector(BaseCollector):
    def __init__(self, device_ip: str, map_file: str, config=None):
        super().__init__(device_ip, device_type=4, map_file=map_file, config=config)
    
    def build_interface_name(self, user: UserData) -> str:
        return f"ge-{user.slot}/{user.vpi}/{user.port}:{user.vci}"

def main():
    parser = argparse.ArgumentParser(description='ACX7024 流量收集器')
    parser.add_argument('--ip', required=True, help='設備 IP')
    parser.add_argument('--map', required=True, help='Map 檔案路徑')
    parser.add_argument('--config', help='配置檔案')
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info(f"ACX7024 收集器: {args.ip}")
    
    try:
        from core.config_loader import ConfigLoader
        config = ConfigLoader(args.config) if args.config else ConfigLoader()
        collector = ACX7024Collector(args.ip, args.map, config)
        success = collector.run()
        stats = collector.stats
        logger.info(f"完成: {stats.success}/{stats.total}, 成功率={stats.success_rate:.1f}%")
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"失敗: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
