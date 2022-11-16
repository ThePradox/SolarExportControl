import logging
import config.customize as customize
import core.appconfig as appconfig
from core.limit import LimitCalculator
from core.helper import AppMqttHelper
from paho.mqtt import client as mqtt
from typing import Callable


class ExportControlAgent:
    def __init__(self, config: appconfig.AppConfig, mqtt_log: bool = False) -> None:
        self.config: appconfig.AppConfig = config
        self.limitcalc: LimitCalculator = LimitCalculator(config)
        self.mqtt_log = mqtt_log
        self.helper: AppMqttHelper
        self.__setup_mode = True
        self.__meta_active = True
        self.__inverter_status = False

    def on_connect_success(self):
        self.limitcalc.reset()
   
        self.helper.subscribe_cmd_active()
        self.helper.publish_meta_online(True)
        self.start_setup_mode()
     
    def on_connect_error(self, rc):
        self.inverter_status = False
        self.meta_active = False

    def on_inverter_status(self, value: bool):
        # Possible buffered message in pipeline after unsubscribe 
        if not self.__meta_active or self.__setup_mode:
            logging.warning("Test: Received unwanted message!")
            return

        self.set_inverter_status(value)

    def on_power_reading(self, value: float):
        # Possible buffered message in pipeline after unsubscribe 
        if not self.__inverter_status or not self.__meta_active or self.__setup_mode:
            logging.warning("Test: Received unwanted message!")
            return

        result = self.limitcalc.add_reading(value)
        self.helper.publish_meta_teles(result)

        if result.command is not None:
            self.send_command(result.command)


    def on_meta_cmd_active(self, active: bool) -> None:
        self.set_meta_active(active)

    def parser_power_reading(self, payload: bytes) -> float | None:
        return customize.parse_power_payload(payload, self.config.command.min_power, self.config.command.max_power)

    def parser_inverter_status(self, payload: bytes) -> bool | None:
        return customize.parse_inverter_status_payload(payload, self.__inverter_status)

    def start_setup_mode(self) -> None:
        self.__setup_mode = True
        setup_mode_duration = 2
        logging.debug(f"Setup mode start: Waiting {setup_mode_duration}s for potential retained cmd messages to arrive...")
        self.helper.schedule(2, self.stop_setup_mode)

    def stop_setup_mode(self) -> None:
        self.__setup_mode = False
        logging.debug("Setup mode end.")
        self.set_meta_active(self.__meta_active)

    def set_meta_active(self, active: bool):     
        if self.__meta_active == active:
            return

        if active is None:
            active = self.__meta_active
         
        self.__meta_active = active

        if self.__setup_mode:
            return

        if active:
            self.helper.publish_meta_active(True)
            self.set_inverter_status()       
        else:
            if self.config.meta.reset_inverter_on_inactive:
                self.send_command(self.limitcalc.get_command_max())
                
            self.helper.unsubscribe_all_but_cmd_active()
            self.helper.publish_meta_active(False)
           
            
    def set_inverter_status(self, status: bool | None = None):
        if self.__inverter_status == status:
            return

        if status is None:
            status = self.get_inverter_status_init()         
            logging.info(f"Init status: {'Active' if status else 'Inactive'}")

        if status:
            self.helper.subscribe_power_reading()           
        else:
            self.helper.unsubscribe_power_reading()
       
        self.helper.publish_meta_inverter_status(status)
        self.inverter_status = status

    def get_inverter_status_init(self) -> bool:
        status = False

        try:
            status = customize.get_status_init(self.config.customize.status)
        except Exception as ex:
            logging.warning(f"customize.get_status_init failed: {ex}")

        return status
        
    def send_command(self, command: float) -> None:
        try:
            cmdpayload = customize.command_to_payload(command,self.config.command.type, self.config.command.min_power, self.config.command.max_power)
        except Exception as ex:
            logging.warning(f"customize.command_to_payload failed: {ex}")
            return

        if cmdpayload is None:
            return
        
        self.helper.publish_command(cmdpayload)
            
        try:
            customize.command_to_generic(command, self.config.command.type, self.config.command.min_power, self.config.command.max_power, self.config.customize.command)
        except Exception as ex:
            logging.warning(f"customize.command_to_generic failed: {ex}")

    def run(self) -> None:
        self.helper = AppMqttHelper(self.config, mqttLogging=self.mqtt_log)
        self.helper.on_connect(self.on_connect_success, self.on_connect_error)
        self.helper.on_power_reading(self.on_power_reading, self.parser_power_reading)
        self.helper.on_inverter_status(self.on_inverter_status, self.parser_inverter_status)
        self.helper.on_cmd_active(self.on_meta_cmd_active)   
        self.helper.setup_will()
        self.helper.connect()
        self.helper.loop_forever()
