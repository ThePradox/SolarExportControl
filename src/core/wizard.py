from enum import IntEnum
from typing import Callable, Any, List, Tuple
import core.appconfig as appconfig
import json
import time
import math
import os.path
import pathlib

HOYMILES_MIN_POWER_PERCENT = float(0.03)
HOYMILES_THROTTLE = int(10)
HYSTERESIS_FACTOR = float(0.02)


class ConfigWizardPresetType(IntEnum):
    NONE = 1
    HOYMILES_OPENDTU = 2


class ConfigWizardReadPowerInterval(IntEnum):
    UNDER_10 = 1,
    UNDER_60 = 2,
    OVER_60 = 3


class ConfigWizard:
    def __init__(self, config_path: str) -> None:
        self.config_path = config_path

    def run(self) -> None:
        self.__print_disclaimer()

        preset = self.__prompt_preset()
        host = self.__prompt_host()
        port = self.__prompt_port()
        protocol = self.__prompt_protocol()
        client_id = f"sec_{str(int(time.time()))}"

        use_auth = self.__prompt_use_auth()
        config_auth = None

        if use_auth:
            auth_user = self.__prompt_auth_user()
            auth_pw = self.__prompt_auth_pw()
            config_auth = appconfig.MqttAuthConfig(auth_user, auth_pw)

        topic_read_power = self.__prompt_topic_read_power()
        interval = self.__prompt_interval()
        topic_write_command = self.__prompt_topic_write_command()
        topic_inv_status = self.__prompt_topic_inverter_status()
        topic_inv_power = self.__prompt_topic_inverter_power()

        config_topics = appconfig.MqttTopicConfig(topic_read_power, topic_write_command, topic_inv_status, topic_inv_power)
        config_mqtt = appconfig.MqttConfig(
            host=host,
            port=port,
            keepalive=None,
            protocol=protocol,
            client_id=client_id,
            topics=config_topics,
            auth=config_auth
        )

        command_max_power = self.__prompt_command_max_power()
        command_min_power = self.__prompt_command_min_power(command_max_power, preset)
        command_target = self.__prompt_command_target()
        command_type = self.__prompt_command_type()
        command_throttle = self.__prompt_command_throttle(preset)
        command_hysteresis = self.__prompt_command_hysteresis(command_max_power)
        config_command = appconfig.CommandConfig(
            target=command_target,
            min_power=command_min_power,
            max_power=command_max_power,
            type=command_type,
            throttle=command_throttle,
            hysteresis=command_hysteresis,
            retransmit=0,
            default_limit=command_max_power,
            hint_multiplier=1.05
        )

        reading_smoothing = self.__prompt_reading_smoothing(interval)
        config_reading = appconfig.ReadingConfig(reading_smoothing[0], reading_smoothing[1], 0)

        use_ha = self.__prompt_use_ha()
        config_telemetry = self.__prompt_telemetry()

        config_meta = appconfig.MetaControlConfig(
            prefix="solarexportcontrol",
            reset_inverter_on_inactive=True,
            telemetry=config_telemetry,
            ha_discovery=appconfig.HA_DiscoveryConfig(
                enabled=use_ha,
                prefix="homeassistant",
                id=1,
                name="SEC"
            )
        )

        config_app = appconfig.AppConfig(
            mqtt=config_mqtt,
            cmd=config_command,
            reading=config_reading,
            meta=config_meta,
            customize=appconfig.CustomizeConfig({}))

        self.__prompt_outfile(config_app)
        input("Press <ENTER> to exit.")

    def __print_disclaimer(self) -> None:
        print("\n|----------------------------------------------------------------------------------------\n| DISCLAIMER: This wizard helps you to create a basic config file.\n| It does not cover every possible scenario or feature.\n| Please consult the '/docs/Config.md' for detailed config file documentation.\n|----------------------------------------------------------------------------------------\n")

    def __prompt_preset(self) -> ConfigWizardPresetType:
        prompt = "Preset: Do you use a Hoymiles inverter with OpenDTU?\n"
        prompt += "[Y]: Yes\n"
        prompt += "[N]: No\n"

        def __vali_preset(input) -> Tuple[bool, ConfigWizardPresetType]:
            input = str.lower(input)
            match input:
                case "y":
                    return (True, ConfigWizardPresetType.HOYMILES_OPENDTU)
                case "n":
                    return (True, ConfigWizardPresetType.NONE)
                case _:
                    return (False, ConfigWizardPresetType.NONE)

        return self.__prompt_input(prompt, __vali_preset)

    def __prompt_host(self) -> str:
        prompt = "Connectivity: Enter IP or hostname of your mqtt broker (without port)\n"
        return self.__prompt_input(prompt, self.__vali_req_str)

    def __prompt_port(self) -> int | None:
        prompt = "Connectivity: Enter port of your mqtt broker. Keep empty for default port\n"

        def __vali_port(input: str) -> Tuple[bool, int | None]:
            if input == "":
                return (True, None)
            else:
                try:
                    return (True, int(input))
                except ValueError:
                    return (False, None)

        return self.__prompt_input(prompt, __vali_port)

    def __prompt_protocol(self) -> int:
        prompt = "Connectivity: Enter broker supported mqtt protocol version. Keep empty for default: 4\n"
        prompt += "[3]: MQTTv31\n"
        prompt += "[4]: MQTTv311\n"
        prompt += "[5]: MQTTv5\n"

        def __vali_prot(input: str) -> Tuple[bool, int]:
            if input == "":
                return (True, 4)
            elif input == "3":
                return (True, 3)
            elif input == "4":
                return (True, 4)
            elif input == "5":
                return (True, 5)
            else:
                return (False, 0)

        return self.__prompt_input(prompt, __vali_prot)

    def __prompt_use_auth(self) -> bool:
        prompt = "Authentication: Does your broker require authentication?\n"
        prompt += "[Y]: Yes\n"
        prompt += "[N]: No\n"
        return self.__prompt_input(prompt, self.__vali_req_bool)

    def __prompt_auth_user(self) -> str:
        prompt = "Authentication: Enter username:\n"
        return self.__prompt_input(prompt, self.__vali_req_str)

    def __prompt_auth_pw(self) -> str | None:
        prompt = "Authentication: [Optional] Enter password (leave empty if not required):\n"
        return self.__prompt_input(prompt, lambda x: (True, x if x != "" else None))

    def __prompt_topic_read_power(self) -> str:
        prompt = "Topics: Enter mqtt topic to read current power draw from:\n"
        return self.__prompt_input(prompt, lambda x: self.__vali_req_str(x.strip()))

    def __prompt_topic_write_command(self) -> str | None:
        prompt = "Topics: Enter mqtt topic to write the inverter limit command to:\n"
        return self.__prompt_input(prompt, lambda x: self.__vali_req_str(x.strip()))

    def __prompt_topic_inverter_status(self) -> str | None:
        prompt = "Topics: [Optional] Enter mqtt topic to read the ongoing inverter status (is producing) from.\nThis allows to sleep when the inverter is not producing.\nLeave empty to deactivate this feature.\n"
        return self.__prompt_input(prompt, lambda x: (True, x.strip() if x.strip() != "" else None))

    def __prompt_topic_inverter_power(self) -> str | None:
        prompt = "Topics: [Optional] Enter mqtt topic to read the ongoing inverter power production from.\nThis allows for faster limit adjustment.\nLeave empty to deactivate this feature.\n"
        return self.__prompt_input(prompt, lambda x: (True, x.strip() if x.strip() != "" else None))    

    def __prompt_command_max_power(self) -> int:
        prompt = "Core: Enter the max power output (AC) of your inverter in watts:\n"
        return self.__prompt_input(prompt, self.__vali_req_pos_int)

    def __prompt_command_min_power(self, max_power: int, preset: ConfigWizardPresetType) -> int:
        if preset == ConfigWizardPresetType.HOYMILES_OPENDTU:
            return int(math.ceil(max_power * HOYMILES_MIN_POWER_PERCENT))

        prompt = "Core: Enter the smallest power output your inverter can be limited to. When in doubt enter 0.\n"
        return self.__prompt_input(prompt, self.__vali_req_pos_int)

    def __prompt_command_target(self) -> int:
        prompt = "Core: Enter your power target in watts (can be negative):\n"
        return self.__prompt_input(prompt, self.__vali_req_int)

    def __prompt_command_type(self) -> appconfig.InverterCommandType:
        prompt = "Core: Should the calculated inverter power limit be send as relative (percent) or absolute (watts) value?\n"
        prompt += "[1]: Relative\n"
        prompt += "[2]: Absolute\n"

        def __vali_type(input: str) -> Tuple[bool, appconfig.InverterCommandType]:
            match input:
                case "1":
                    return (True, appconfig.InverterCommandType.RELATIVE)
                case "2":
                    return (True, appconfig.InverterCommandType.ABSOLUTE)
                case _:
                    return (False, appconfig.InverterCommandType.RELATIVE)

        return self.__prompt_input(prompt, __vali_type)

    def __prompt_command_throttle(self, preset: ConfigWizardPresetType) -> int:
        if preset == ConfigWizardPresetType.HOYMILES_OPENDTU:
            return HOYMILES_THROTTLE

        prompt = "Core: What is the required waiting period (in seconds) before a new power limit can be sent after a power limit has been sent?\n"
        return self.__prompt_input(prompt, self.__vali_req_pos_int)

    def __prompt_command_hysteresis(self, max_power: int) -> float:
        return float(math.ceil(max_power*HYSTERESIS_FACTOR))

    def __prompt_reading_smoothing(self, interval: ConfigWizardReadPowerInterval) -> Tuple[appconfig.PowerReadingSmoothingType, int]:
        match interval:
            case ConfigWizardReadPowerInterval.UNDER_10:
                return (appconfig.PowerReadingSmoothingType.AVG, 8)
            case ConfigWizardReadPowerInterval.UNDER_60:
                return (appconfig.PowerReadingSmoothingType.AVG, 4)
            case ConfigWizardReadPowerInterval.OVER_60:
                return (appconfig.PowerReadingSmoothingType.NONE, 0)
            case _:
                return (appconfig.PowerReadingSmoothingType.NONE, 0)

    def __prompt_telemetry(self) -> appconfig.MetaTelemetryConfig:
        prompt = "Telemetry: What level of telemetry should be written to mqtt (and therefore the home assistant integration)?\n"
        prompt += "[1]: None\n"
        prompt += "[2]: Basic (Sample, Limit, Overshoot)\n"
        prompt += "[3]: Full (Power, Sample, Overshoot, Limit, Command)\n"

        def __vali_tele(input: str) -> Tuple[bool, appconfig.MetaTelemetryConfig]:
            match input:
                case "1":
                    return (True, appconfig.MetaTelemetryConfig(power=False, sample=False, overshoot=False, limit=False, command=False))
                case "2":
                    return (True, appconfig.MetaTelemetryConfig(power=False, sample=True, overshoot=True, limit=True, command=False))
                case "3":
                    return (True, appconfig.MetaTelemetryConfig(power=True, sample=True, overshoot=True, limit=True, command=True))
                case _:
                    return (False, appconfig.MetaTelemetryConfig(False, False, False, False, False))

        return self.__prompt_input(prompt, __vali_tele)

    def __prompt_use_ha(self) -> bool:
        prompt = "Home Assistant: Do you want to use the home assistant integration?\n"
        prompt += "[Y]: Yes\n"
        prompt += "[N]: No\n"

        return self.__prompt_input(prompt, self.__vali_req_bool)

    def __prompt_interval(self) -> ConfigWizardReadPowerInterval:
        prompt = "How often does this topic receives an update?\n"
        prompt += "[1]: Faster than 10 seconds\n"
        prompt += "[2]: Faster than 60 seconds\n"
        prompt += "[3]: Slower than 60 seconds\n"

        def __vali_interval(input: str) -> Tuple[bool, ConfigWizardReadPowerInterval]:
            match input:
                case "1":
                    return (True, ConfigWizardReadPowerInterval.UNDER_10)
                case "2":
                    return (True, ConfigWizardReadPowerInterval.UNDER_60)
                case "3":
                    return (True, ConfigWizardReadPowerInterval.OVER_60)
                case _:
                    return (False, ConfigWizardReadPowerInterval.OVER_60)

        return self.__prompt_input(prompt, __vali_interval)

    def __prompt_outfile(self, config: appconfig.AppConfig) -> None:

        def __write_file(filepath) -> bool:
            try:
                with open(filepath,"x",encoding="utf-8") as outfile:
                    json.dump(config.to_json(), outfile, indent=4)
                    return True
            except OSError:
                print(f"Failed to create: '{filepath}'\n")
                return False


        def __vali_proxy(input)-> Tuple[bool, str]:
            filepath = str(pathlib.Path(self.config_path).parent.joinpath(input))
            return (__write_file(filepath), filepath)

        filepath = self.config_path
        success = __write_file(filepath)

        if not success:
            filepath = self.__prompt_input("File already exists or missing write/create permissions\nEnter a new file name:\n", __vali_proxy)

        print(f"Config successfully created: '{filepath}'\n")

    @staticmethod
    def __prompt_input(prompt: str, validator: Callable[[str], Tuple[bool, Any]]) -> Any:
        while True:
            in_str = input(prompt)
            val_res = validator(in_str)

            if val_res[0]:
                print("")
                return val_res[1]

            print("Invalid input!")
            print("")

    @staticmethod
    def __vali_req_bool(input: str) -> Tuple[bool, bool]:
        input = input.lower()
        match input:
            case "y":
                return (True, True)
            case "n":
                return (True, False)
            case _:
                return (False, False)

    @staticmethod
    def __vali_req_str(input: str) -> Tuple[bool, str]:
        if input.isspace() or input == "":
            return (False, input)

        return (True, input)

    @staticmethod
    def __vali_req_pos_int(input: str) -> Tuple[bool, int]:
        try:
            val = int(input)

            if val < 0:
                return (False, 0)

            return (True, val)
        except ValueError:
            return (False, 0)

    @staticmethod
    def __vali_req_int(input: str) -> Tuple[bool, int]:
        try:
            val = int(input)
            return (True, val)
        except ValueError:
            return (False, 0)

    def __vali_valid_file(self, filename:str) -> Tuple[bool, str]:
        filepath = str(pathlib.Path(self.config_path).parent.joinpath(filename))
        
        try:
            with open(filepath, 'x') as tempfile:
                pass
        except OSError:
            print(f"Failed to create: '{filepath}'\n")
            return (False, filepath)

        return (True, filepath)