import argparse
import logging
from pathlib import Path
import sys
import config
from agent import ExportControlAgent

argparser = argparse.ArgumentParser(prog="SolarExportControl", description="Listens to a mqtt power reading topic and publishes power limits to mqtt topic based on a configured power target.")
argparser.add_argument("config", type=str, help="path to config file")
argparser.add_argument("-v", "--verbose", action="store_true")
args = argparser.parse_args()

config_path = Path(args.config).resolve()

if not config_path.exists():
    sys.exit(f"Config: '{str(config_path)}' does not exist")

loglvl = logging.DEBUG if args.verbose else logging.INFO
logging.basicConfig(level=loglvl, format="%(asctime)s | %(levelname).3s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")


try:
    appconfig = config.config_from_json(str(config_path))
except Exception as ex:
    sys.exit(f"Failed to load config: '{ex.args}'")


agent = ExportControlAgent(appconfig)
agent.run()
