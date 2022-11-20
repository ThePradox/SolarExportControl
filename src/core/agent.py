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
        self.__setup_mode: bool = True
        self.__meta_active: bool = True
        self.__inverter_status: bool = False

        self.helper: AppMqttHelper = AppMqttHelper(self.config, mqttLogging=self.mqtt_log)
        self.helper.on_connect(self.__on_connect_success, self.__on_connect_error)
        self.helper.on_power_reading(self.__on_power_reading, self.__parser_power_reading)
        self.helper.on_inverter_status(self.__on_inverter_status, self.__parser_inverter_status)
        self.helper.on_cmd_active(self.__on_meta_cmd_active)
        self.helper.setup_will()

# region Events

    def __on_connect_success(self) -> None:
        self.limitcalc.reset()
        self.helper.subscribe_cmd_active()
        self.helper.publish_meta_online(True)
        self.__start_setup_mode()

    def __on_connect_error(self, rc: Any) -> None:
        self.__inverter_status = False
        self.__meta_active = False
        self.__setup_mode = False

    def __on_inverter_status(self, value: bool) -> None:
        # Possible buffered message in pipeline after unsubscribe
        if not self.__meta_active or self.__setup_mode:
            logging.warning("Inverter status: Received unwanted message!")
            return

        self.__set_inverter_status(value)

    def __on_power_reading(self, value: float) -> None:
        # Possible buffered message in pipeline after unsubscribe
        if not self.__inverter_status or not self.__meta_active or self.__setup_mode:
            logging.warning("Inverter status: Received unwanted message!")
            return

        result = self.limitcalc.add_reading(value)
        self.helper.publish_meta_teles(result.reading, result.sample, result.overshoot, result.limit)

        if result.command is not None:
            self.__send_command(result.command)

    def __on_meta_cmd_active(self, active: bool) -> None:
        self.__set_meta_active(active)

# endregion

    def __parser_power_reading(self, payload: bytes) -> float | None:
        return customize.parse_power_payload(payload, self.config.command.min_power, self.config.command.max_power)

    def __parser_inverter_status(self, payload: bytes) -> bool | None:
        return customize.parse_inverter_status_payload(payload, self.__inverter_status)

    def __start_setup_mode(self) -> None:
        self.__setup_mode = True
        setup_mode_duration = 2
        logging.debug(f"Setup mode start: Waiting {setup_mode_duration}s for potential retained cmd messages to arrive...")
        self.helper.schedule(2, self.__stop_setup_mode)

    def __stop_setup_mode(self) -> None:
        self.__setup_mode = False
        logging.debug("Setup mode end.")
        self.__set_meta_active(None)

    def __set_meta_active(self, active: bool | None) -> None:
        active_applied = active is None
        if self.__meta_active == active:
            return

        if active is None:
            active = self.__meta_active

        self.__meta_active = active

        if self.__setup_mode:
            return

        if active:
            logging.info("Application status: Active")
            self.helper.publish_meta_active(True)
            self.__set_inverter_status()
        else:
            logging.info("Application status: Inactive")
            if not active_applied and self.config.meta.reset_inverter_on_inactive:
                self.__send_command(self.limitcalc.get_command_max())

            self.helper.unsubscribe_all_but_cmd_active()
            self.helper.publish_meta_active(False)

    def __set_inverter_status(self, status: bool | None = None) -> None:
        if self.__inverter_status == status:
            return

        if status is None:
            status = self.__get_inverter_status_init()
            logging.info(f"Inverter status: {'Active' if status else 'Inactive'}")

        if status:
            self.helper.subscribe_power_reading()
        else:
            self.helper.unsubscribe_power_reading()

        self.helper.publish_meta_inverter_status(status)
        self.__inverter_status = status

    def __get_inverter_status_init(self) -> bool:
        status = False

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
        self.helper.publish_meta_command(command)

        try:
            customize.command_to_generic(command, self.config.command.type, self.config.command.min_power, self.config.command.max_power, self.config.customize.command)
        except Exception as ex:
            logging.warning(f"customize.command_to_generic failed: {ex}")

    def run(self) -> None:
        self.helper.connect()
        self.helper.loop_forever()
