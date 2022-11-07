import sys
MIN_PYTHON = (3, 10)
if sys.version_info < MIN_PYTHON:
    print (sys.version_info)
    sys.exit("Python %s.%s or later is required.\n" % MIN_PYTHON)

import argparse, logging, pathlib
import core.setup
from core.agent import ExportControlAgent


argparser = argparse.ArgumentParser(prog="SolarExportControl", description="Listens to a mqtt power reading topic and publishes power limits to mqtt topic based on a configured power target.")
argparser.add_argument("config", type=str, help="path to config file")
argparser.add_argument("-v", "--verbose",help="enables detailed logging", action="store_true")
argparser.add_argument("--mqttdiag", help="enables extra mqtt diagnostics", action="store_true")
args = argparser.parse_args()

config_path = pathlib.Path(args.config).resolve()

if not config_path.exists():
    sys.exit(f"Config: '{str(config_path)}' does not exist")

loglvl = logging.DEBUG if args.verbose else logging.INFO
logging.basicConfig(level=loglvl, format="%(asctime)s | %(levelname).3s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")


try:
    appconfig = core.setup.AppConfig.from_json_file(str(config_path))
except Exception as ex:
    sys.exit(f"Failed to load config: '{ex.args}'")


agent = ExportControlAgent(appconfig, args.mqttdiag)
agent.run()
