import os
from pathlib import Path
import config
from agent import ExportControlAgent


__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
config_path = str(Path(__location__).parent.joinpath("config.json").absolute())

appconfig = config.config_from_json(config_path)

agent = ExportControlAgent(appconfig)
agent.run()
