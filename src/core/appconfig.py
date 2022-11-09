from __future__ import annotations
from enum import Enum
import paho.mqtt.client as mqtt
import json


class InverterCommandType(Enum):
    ABSOLUTE = 1
    RELATIVE = 2


class PowerReadingSmoothingType(Enum):
    NONE = 1,
    AVG = 2


class AppConfig:
    def __init__(self, mqtt: MqttConfig, cmd: CommandConfig, reading: ReadingConfig, meta: MetaControlConfig | None, customize: CustomizeConfig) -> None:
        self.mqtt = mqtt
        self.command = cmd
        self.reading = reading
        self.meta = meta
        self.customize = customize

    @staticmethod
    def from_json_file(path: str) -> AppConfig:
        fs = open(path, "r")
        jf = json.load(fs)

        j_mqtt = jf.get("mqtt")
        if type(j_mqtt) is not dict:
            raise ValueError("Missing config segment: mqtt")

        o_mqtt = MqttConfig.from_json(j_mqtt)

        j_cmd = jf.get("command")
        if type(j_cmd) is not dict:
            raise ValueError("Missing config segment: command")

        o_cmd = CommandConfig.from_json(j_cmd)

        j_reading = jf.get("reading")
        if type(j_reading) is not dict:
            raise ValueError("Missing config segment: reading")

        o_reading = ReadingConfig.from_json(j_reading)

        o_meta = None
        j_meta = jf.get("meta")
        if type(j_meta) is dict:
            o_meta = MetaControlConfig.from_json(j_meta)

        j_cust = jf.get("customize")
        if type(j_cust) is not dict:
            raise ValueError("Missing config segment: customize")

        o_cust = CustomizeConfig.from_json(j_cust)

        return AppConfig(o_mqtt, o_cmd, o_reading, o_meta,  o_cust)


class MqttConfig:
    def __init__(self, host: str, topics: MqttTopicConfig,
                 port: int | None = None,
                 keepalive: int | None = None,
                 protocol: int | None = None,
                 retain: bool | None = None,
                 client_id: str | None = None,
                 clean_session: bool | None = None,
                 auth: MqttAuthConfig | None = None) -> None:
        self.host: str = host
        self.port: int = port if port is not None else 1883
        self.keepalive: int = keepalive if keepalive is not None else 60
        self.protocol: int = protocol if protocol is not None else mqtt.MQTTv311
        self.retain: bool = retain if retain is not None else False
        self.client_id: str = client_id if client_id is not None else "solar-export-control"
        self.clean_session = clean_session if clean_session is not None else True
        self.topics: MqttTopicConfig = topics
        self.auth: MqttAuthConfig | None = auth

    @staticmethod
    def from_json(json: dict) -> MqttConfig:
        j_host = json.get("host")

        if type(j_host) is not str or not j_host:
            raise ValueError(f"MqttConfig: Invalid host: '{j_host}'")

        j_port: int | None = None
        j_keepalive: int | None = None
        j_protocol: int | None = None
        j_retain: bool | None = None
        j_client_id: str | None = None
        j_clean_session: bool | None = None

        t = json.get("port")
        if type(t) is int and t > 0:
            j_port = t

        t = json.get("keepalive")
        if type(t) is int and t > 0:
            j_keepalive = t

        t = json.get("protocol")
        if type(t) is int:
            j_protocol = t

        t = json.get("retain")
        if type(t) is bool:
            j_retain = t

        t = json.get("clientId")
        if type(t) is str:
            j_client_id = t

        t = json.get("cleanSession")
        if type(t) is bool:
            j_clean_session = t

        j_topics = json.get("topics")
        if type(j_topics) is not dict:
            raise ValueError(f"MqttConfig: Invalid topics: '{j_topics}'")

        o_topics = MqttTopicConfig.from_json(j_topics)

        o_auth: MqttAuthConfig | None = None
        j_auth = json.get("auth")
        if type(j_auth) is dict and j_auth.get("username"):
            o_auth = MqttAuthConfig.from_json(j_auth)

        return MqttConfig(host=j_host,
                          topics=o_topics,
                          port=j_port,
                          keepalive=j_keepalive,
                          protocol=j_protocol,
                          retain=j_retain,
                          client_id=j_client_id,
                          clean_session=j_clean_session,
                          auth=o_auth)


class MqttTopicConfig:
    def __init__(self, read_power: str, write_limit: str | None, status: str | None) -> None:
        self.read_power: str = read_power
        self.write_limit: str | None = write_limit
        self.status: str | None = status

    @staticmethod
    def from_json(json: dict) -> MqttTopicConfig:
        j_read_power = json.get("readPower")
        if type(j_read_power) is not str or not j_read_power:
            raise ValueError(f"MqttTopicConfig: Invalid readPower: '{j_read_power}'")

        j_write_limit = json.get("writeLimit")
        if type(j_write_limit) is not str or not j_write_limit:
            j_write_limit = None

        j_status = json.get("status")
        if type(j_status) is not str or not j_status:
            j_status = None

        return MqttTopicConfig(read_power=j_read_power, write_limit=j_write_limit, status=j_status)


class MqttAuthConfig:
    def __init__(self, username: str, password: str | None) -> None:
        self.username: str = username
        self.password: str | None = password

    @staticmethod
    def from_json(json: dict) -> MqttAuthConfig:
        j_username = json.get("username")
        if type(j_username) is not str or not j_username:
            raise ValueError(f"MqttAuthConfig: Invalid username: '{j_username}'")

        j_password = json.get("password")
        if type(j_password) is not str:
            j_password = None

        return MqttAuthConfig(j_username, j_password)


class CommandConfig:
    def __init__(self, target: int, min_power: float, max_power: float, type: InverterCommandType, throttle: int, min_diff: float, retransmit: int) -> None:
        self.target: int = target
        self.min_power: float = min_power
        self.max_power: float = max_power
        self.type: InverterCommandType = type
        self.throttle: int = throttle
        self.min_diff: float = min_diff
        self.retransmit: int = retransmit

    @staticmethod
    def from_json(json: dict) -> CommandConfig:
        j_min_power = json.get("minPower")
        if type(j_min_power) is int:
            j_min_power = float(j_min_power)
        elif type(j_min_power) is not float:
            raise ValueError(f"CommandConfig: Invalid min_power: '{j_min_power}'")

        j_max_power = json.get("maxPower")
        if type(j_max_power) is int:
            j_max_power = float(j_max_power)
        elif type(j_max_power) is not float:
            raise ValueError(f"CommandConfig: Invalid max_power: '{j_max_power}'")

        if j_min_power >= j_max_power:
            raise ValueError("CommandConfig: min_power greater or equal max_power")

        j_target = json.get("target")
        if type(j_target) is not int:
            raise ValueError(f"CommandConfig: Invalid target type: '{j_target}'")

        j_type = json.get("type")
        e_type: InverterCommandType

        if j_type == "absolute":
            e_type = InverterCommandType.ABSOLUTE
        elif j_type == "relative":
            e_type = InverterCommandType.RELATIVE
        else:
            raise ValueError(f"CommandConfig: Invalid type: '{j_type}'")

        j_throttle = json.get("throttle")
        if type(j_throttle) is not int or j_throttle < 0:
            raise ValueError(f"CommandConfig: Invalid throttle: '{j_throttle}'")

        j_min_diff = json.get("minDiff")
        if type(j_min_diff) is int:
            j_min_diff = float(j_min_diff)

        if type(j_min_diff) is not float or j_min_diff < 0:
            raise ValueError(f"CommandConfig: Invalid minDiff: '{j_min_diff}'")

        j_retransmit = json.get("retransmit")
        if type(j_retransmit) is not int or j_retransmit < 0:
            raise ValueError(f"CommandConfig: Invalid retransmit: '{j_retransmit}'")

        return CommandConfig(
            target=j_target,
            min_power=j_min_power,
            max_power=j_max_power,
            type=e_type,
            throttle=j_throttle,
            min_diff=j_min_diff,
            retransmit=j_retransmit
        )


class ReadingConfig:
    def __init__(self, smoothing: PowerReadingSmoothingType, smoothingSampleSize: int, offset: float) -> None:
        self.smoothing = smoothing
        self.smoothingSampleSize = smoothingSampleSize
        self.offset = offset

    @staticmethod
    def from_json(json: dict) -> ReadingConfig:
        j_smoothing = json.get("smoothing")
        e_smoothing: PowerReadingSmoothingType = PowerReadingSmoothingType.NONE

        if j_smoothing == "avg":
            e_smoothing = PowerReadingSmoothingType.AVG

        j_smoothing_sample_size = json.get("smoothingSampleSize")
        if j_smoothing_sample_size is None or type(j_smoothing_sample_size) is not int or j_smoothing_sample_size < 0:
            j_smoothing_sample_size = 0

        j_offset = json.get("offset")
        if type(j_offset) is int:
            j_offset = float(j_offset)

        if type(j_offset) is not float:
            j_offset = float(0)

        return ReadingConfig(smoothing=e_smoothing, smoothingSampleSize=j_smoothing_sample_size, offset=j_offset)


class CustomizeConfig:
    def __init__(self, status: dict, calibration: dict, command: dict):
        self.status = status
        self.calibration = calibration
        self.command = command

    @staticmethod
    def from_json(json: dict) -> CustomizeConfig:
        j_status = json.get("status")

        if type(j_status) is not dict:
            j_status = {}

        j_calib = json.get("calibration")

        if type(j_calib) is not dict:
            j_calib = {}

        j_command = json.get("command")
        if type(j_command) is not dict:
            j_command = {}

        return CustomizeConfig(status=j_status, calibration=j_calib, command=j_command)


class MetaControlConfig:
    def __init__(self, active: bool, prefix: str) -> None:
        self.active = active
        self.prefix = prefix

    @staticmethod
    def from_json(json: dict) -> MetaControlConfig:
        j_active = json.get("active")
        if type(j_active) is not bool:
            raise ValueError(f"MetaControlConfig: Invalid active: '{j_active}'")

        j_prefix = json.get("prefix")
        if type(j_prefix) is not str or not j_prefix:
            raise ValueError(f"MetaControlConfig: Invalid prefix: '{j_prefix}'")

        return MetaControlConfig(j_active, j_prefix)
