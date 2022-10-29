import logging
import os
from pathlib import Path
import config
from agent import ExportControlAgent

logging.basicConfig(level= 10)

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
config_path = str(Path(__location__).parent.joinpath("config.json").absolute())

appconfig = config.config_from_json(config_path)

agent = ExportControlAgent(appconfig)
agent.run()
