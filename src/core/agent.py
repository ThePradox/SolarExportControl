import logging
import config.customize as customize
import core.appconfig as appconfig
from core.limit import LimitCalculator
from core.helper import AppMqttHelper
from typing import Any


class ExportControlAgent:
    def __init__(self, config: appconfig.AppConfig, mqtt_log: bool = False) -> None:
        self.config: appconfig.AppConfig = config
        self.limitcalc: LimitCalculator = LimitCalculator(config)
        self.mqtt_log: bool = mqtt_log

        self.helper: AppMqttHelper = AppMqttHelper(self.config, mqttLogging=self.mqtt_log)
        self.helper.on_connect(self.__on_connect_success, self.__on_connect_error)
        self.helper.on_power_reading(self.__on_power_reading, self.__parser_power_reading)
        self.helper.on_inverter_status(self.__on_inverter_status, self.__parser_inverter_status)
        self.helper.on_meta_cmd_enabled(self.__on_meta_cmd_active)
        self.helper.setup_will()

        self.__setup_mode: bool = True
        self.__meta_status: bool = True
        self.__inverter_status: bool = self.__get_inverter_status_init()
        self.__published_discovery = False

# region Events

    def __on_connect_success(self) -> None:
        self.helper.subscribe_meta_cmd_enabled()
        self.helper.subscribe_inverter_status()
        self.helper.publish_meta_status_online(True)
        self.__start_setup_mode()

    def __on_connect_error(self, rc: Any) -> None:
        self.__inverter_status = False
        self.__meta_status = False
        self.__setup_mode = False

    def __on_inverter_status(self, value: bool) -> None:
        self.__set_status(inverter_status=value)

    def __on_meta_cmd_active(self, active: bool) -> None:
        self.__set_status(meta_status=active)

    def __on_power_reading(self, value: float) -> None:
        # Possible buffered message in pipeline after unsubscribe
        if not self.__inverter_status or not self.__meta_status or self.__setup_mode:
            #TODO: Remove
            logging.warning("Power reading: Received unwanted message!")
            return

        result = self.limitcalc.add_reading(value)
        self.helper.publish_meta_teles(result.reading, result.sample, result.overshoot, result.limit)

        if result.command is not None:
            self.__send_command(result.command)

# endregion

    def __parser_power_reading(self, payload: bytes) -> float | None:
        return customize.parse_power_payload(payload, self.config.command.min_power, self.config.command.max_power)

    def __parser_inverter_status(self, payload: bytes) -> bool | None:
        return customize.parse_inverter_status_payload(payload, self.__inverter_status)

    def __start_setup_mode(self) -> None:
        self.__setup_mode = True
        setup_mode_duration = 2
        logging.debug(f"Setup mode start: Waiting {setup_mode_duration}s for potential retained messages to arrive...")
        self.helper.schedule(2, self.__stop_setup_mode)

    def __stop_setup_mode(self) -> None:
        self.__setup_mode = False
        logging.debug("Setup mode end.")
        self.__set_status(meta_status=None, inverter_status=None, force=True)

    def __set_status(self, meta_status: bool | None = None, inverter_status: bool | None = None, force: bool = False) -> None:
        meta_status_retr = meta_status is None
        inverter_status_retr = inverter_status is None

        if meta_status_retr:
            meta_status = self.__meta_status

        if inverter_status_retr:
            inverter_status = self.__inverter_status

        if not force and self.__inverter_status == inverter_status and self.__meta_status == meta_status:
            return

        self.__meta_status = meta_status
        self.__inverter_status = inverter_status

        if self.__setup_mode:
            return

        active = meta_status and inverter_status
        self.helper.publish_meta_status_enabled(meta_status)
        self.helper.publish_meta_status_inverter(inverter_status)
        self.helper.publish_meta_status_active(active)
        
        if active:
            logging.info("Application status: Active")
            self.limitcalc.reset()
            self.helper.subscribe_power_reading()
            self.__ha_discovery()
        else:
            logging.info("Application status: Inactive")
            self.helper.unsubscribe_power_reading()
            if not meta_status and not meta_status_retr and self.config.meta.reset_inverter_on_inactive:
                self.__send_command(self.limitcalc.get_command_max())

    def __get_inverter_status_init(self) -> bool:
        if not self.helper.has_inverter_status:
            return True

        status = True

        try:
            status = customize.get_status_init(self.config.customize.status)
        except Exception as ex:
            logging.warning(f"customize.get_status_init failed: {ex}")

        return status

    def __send_command(self, command: float) -> None:
        try:
            cmdpayload = customize.command_to_payload(command, self.config.command.type, self.config.command.min_power, self.config.command.max_power)
        except Exception as ex:
            logging.warning(f"customize.command_to_payload failed: {ex}")
            return

        if cmdpayload is None:
            return

        self.helper.publish_command(cmdpayload)
        self.helper.publish_meta_tele_command(command)

        try:
            customize.command_to_generic(command, self.config.command.type, self.config.command.min_power, self.config.command.max_power, self.config.customize.command)
        except Exception as ex:
            logging.warning(f"customize.command_to_generic failed: {ex}")

    def __ha_discovery(self) -> None:
        if self.__published_discovery or not self.helper.has_discovery:
            return

        self.helper.publish_meta_ha_discovery()
        self.__published_discovery = True

    def run(self) -> None:
        self.helper.connect()
        self.helper.loop_forever()
