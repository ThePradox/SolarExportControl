from __future__ import annotations
from enum import IntEnum
import paho.mqtt.client as mqtt
import json


class InverterCommandType(IntEnum):
    ABSOLUTE = 1
    RELATIVE = 2


class PowerReadingSmoothingType(IntEnum):
    NONE = 1,
    AVG = 2


class AppConfig:
    def __init__(self, mqtt: MqttConfig, cmd: CommandConfig, reading: ReadingConfig, meta: MetaControlConfig, customize: CustomizeConfig) -> None:
        self.mqtt = mqtt
        self.command = cmd
        self.reading = reading
        self.meta = meta
        self.customize = customize

    def to_json(self) -> dict:
        return {
            "mqtt": self.mqtt.to_json(),
            "command": self.command.to_json(),
            "reading": self.reading.to_json(),
            "meta": self.meta.to_json(),
            "customize": self.customize.to_json()
        }

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

        j_meta = jf.get("meta")
        if type(j_meta) is not dict:
            raise ValueError("Missing config segment: meta")

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
                 client_id: str | None = None,          
                 auth: MqttAuthConfig | None = None) -> None:
        self.host: str = host
        self.port: int = port if port is not None else 1883
        self.keepalive: int = keepalive if keepalive is not None else 60
        self.protocol: int = protocol if protocol is not None else mqtt.MQTTv311      
        self.client_id: str = client_id if client_id is not None else "solar-export-control"
        self.topics: MqttTopicConfig = topics
        self.auth: MqttAuthConfig | None = auth

    def to_json(self) -> dict:

        return {
            "host": str(self.host),
            "port": self.port,
            "keepalive": self.keepalive,
            "protocol": self.protocol,
            "clientId": self.client_id,
            "topics": self.topics.to_json(),
            "auth": self.auth.to_json() if self.auth is not None else None
        }

    @staticmethod
    def from_json(json: dict) -> MqttConfig:
        j_host = json.get("host")

        if type(j_host) is not str or not j_host:
            raise ValueError(f"MqttConfig: Invalid host: '{j_host}'")

        j_port: int | None = None
        j_keepalive: int | None = None
        j_protocol: int | None = None
        j_client_id: str | None = None

        t = json.get("port")
        if type(t) is int and t > 0:
            j_port = t

        t = json.get("keepalive")
        if type(t) is int and t > 0:
            j_keepalive = t

        t = json.get("protocol")
        if type(t) is int:
            j_protocol = t

        t = json.get("clientId")
        if type(t) is str:
            j_client_id = t

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
                          client_id=j_client_id,
                          auth=o_auth)


class MqttTopicConfig:
    def __init__(self, read_power: str, write_command: str | None, status: str | None) -> None:
        self.read_power: str = read_power
        self.write_command: str | None = write_command
        self.inverter_status: str | None = status

    def to_json(self) -> dict:
        return {
            "readPower": str(self.read_power),
            "writeCommand": self.write_command,
            "inverterStatus": self.inverter_status
        }

    @staticmethod
    def from_json(json: dict) -> MqttTopicConfig:
        j_read_power = json.get("readPower")
        if type(j_read_power) is not str or not j_read_power:
            raise ValueError(f"MqttTopicConfig: Invalid readPower: '{j_read_power}'")

        j_write_command = json.get("writeCommand")
        if type(j_write_command) is not str or not j_write_command:
            j_write_command = None

        j_status = json.get("inverterStatus")
        if type(j_status) is not str or not j_status:
            j_status = None

        return MqttTopicConfig(read_power=j_read_power, write_command=j_write_command, status=j_status)


class MqttAuthConfig:
    def __init__(self, username: str, password: str | None) -> None:
        self.username: str = username
        self.password: str | None = password

    def to_json(self) -> dict:
        return {
            "username": str(self.username),
            "password": self.password
        }

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
    def __init__(self, target: int, min_power: float, max_power: float, type: InverterCommandType, throttle: int, hysteresis: float, retransmit: int) -> None:
        self.target: int = target
        self.min_power: float = min_power
        self.max_power: float = max_power
        self.type: InverterCommandType = type
        self.throttle: int = throttle
        self.hysteresis: float = hysteresis
        self.retransmit: int = retransmit

    def to_json(self) -> dict:
        match self.type:
            case InverterCommandType.ABSOLUTE:
                str_type = "absolute"
            case InverterCommandType.RELATIVE:
                str_type = "relative"
            case _:
                str_type = "absolute"

        return {
            "target": int(self.target),
            "minPower": int(self.min_power),
            "maxPower": int(self.max_power),
            "type": str_type,
            "throttle": int(self.throttle),
            "hysteresis": float(self.hysteresis),
            "retransmit": int(self.retransmit)
        }

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

        j_hysteresis = json.get("hysteresis")
        if type(j_hysteresis) is int:
            j_hysteresis = float(j_hysteresis)

        if type(j_hysteresis) is not float or j_hysteresis < 0:
            raise ValueError(f"CommandConfig: Invalid hysteresis: '{j_hysteresis}'")

        j_retransmit = json.get("retransmit")
        if type(j_retransmit) is not int or j_retransmit < 0:
            raise ValueError(f"CommandConfig: Invalid retransmit: '{j_retransmit}'")

        return CommandConfig(
            target=j_target,
            min_power=j_min_power,
            max_power=j_max_power,
            type=e_type,
            throttle=j_throttle,
            hysteresis=j_hysteresis,
            retransmit=j_retransmit
        )


class ReadingConfig:
    def __init__(self, smoothing: PowerReadingSmoothingType, smoothingSampleSize: int, offset: float) -> None:
        self.smoothing = smoothing
        self.smoothingSampleSize = smoothingSampleSize
        self.offset = offset

    def to_json(self) -> dict:
        sm = "avg" if self.smoothing == PowerReadingSmoothingType.AVG else None

        return {
            "offset": int(self.offset),
            "smoothing": sm,
            "smoothingSampleSize": int(self.smoothingSampleSize)
        }

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
    def __init__(self, command: dict) -> None:
        self.command = command

    def to_json(self) -> dict:
        return {        
            "command": self.command
        }

    @staticmethod
    def from_json(json: dict) -> CustomizeConfig:
        j_command = json.get("command")
        if type(j_command) is not dict:
            j_command = {}

        return CustomizeConfig(command=j_command)


class MetaControlConfig:
    def __init__(self, prefix: str, reset_inverter_on_inactive: bool, telemetry: MetaTelemetryConfig, ha_discovery: HA_DiscoveryConfig) -> None:
        self.prefix = prefix
        self.reset_inverter_on_inactive = reset_inverter_on_inactive
        self.telemetry = telemetry
        self.discovery = ha_discovery

    def to_json(self) -> dict:
        return {
            "prefix": str(self.prefix),
            "resetInverterLimitOnInactive": bool(self.reset_inverter_on_inactive),
            "telemetry": self.telemetry.to_json(),
            "homeAssistantDiscovery": self.discovery.to_json()
        }

    @staticmethod
    def from_json(json: dict) -> MetaControlConfig:
        j_reset = json.get("resetInverterLimitOnInactive")
        if type(j_reset) is not bool:
            raise ValueError(f"MetaControlConfig: Invalid resetInverterLimitOnInactive: '{j_reset}'")

        j_prefix = json.get("prefix")
        if type(j_prefix) is not str or not j_prefix:
            raise ValueError(f"MetaControlConfig: Invalid prefix: '{j_prefix}'")
        elif j_prefix.startswith("/"):
            raise ValueError(f"MetaControlConfig: prefix cannot start with slash: '{j_prefix}'")

        j_telemetry = json.get("telemetry")
        if type(j_telemetry) is not dict:
            raise ValueError(f"MetaControlConfig: Invalid telemetry: '{j_telemetry}'")
        o_telemetry = MetaTelemetryConfig.from_json(j_telemetry)

        j_discovery = json.get("homeAssistantDiscovery")
        if type(j_discovery) is not dict:
            raise ValueError(f"MetaControlConfig: Invalid homeAssistantDiscovery: '{j_telemetry}'")

        o_discovery = HA_DiscoveryConfig.from_json(j_discovery)

        return MetaControlConfig(j_prefix, j_reset, o_telemetry, o_discovery)


class MetaTelemetryConfig:
    def __init__(self, power: bool, sample: bool, overshoot: bool, limit: bool, command: bool) -> None:
        self.power = power
        self.sample = sample
        self.overshoot = overshoot
        self.limit = limit
        self.command = command

    def to_json(self) -> dict:
        return {
            "power": bool(self.power),
            "sample": bool(self.sample),
            "overshoot": bool(self.overshoot),
            "limit": bool(self.limit),
            "command": bool(self.command)
        }

    @staticmethod
    def from_json(json: dict) -> MetaTelemetryConfig:
        j_power = json.get("power")
        if type(j_power) is not bool:
            raise ValueError(f"MetaTelemetryConfig: Invalid power: '{j_power}'")

        j_sample = json.get("sample")
        if type(j_sample) is not bool:
            raise ValueError(f"MetaTelemetryConfig: Invalid sample: '{j_sample}'")

        j_overshoot = json.get("overshoot")
        if type(j_overshoot) is not bool:
            raise ValueError(f"MetaTelemetryConfig: Invalid overshoot: '{j_overshoot}'")

        j_limit = json.get("limit")
        if type(j_limit) is not bool:
            raise ValueError(f"MetaTelemetryConfig: Invalid limit: '{j_limit}'")

        j_command = json.get("command")
        if type(j_command) is not bool:
            raise ValueError(f"MetaTelemetryConfig: Invalid command: '{j_command}'")

        return MetaTelemetryConfig(power=j_power, sample=j_sample, overshoot=j_overshoot, limit=j_limit, command=j_command)


class HA_DiscoveryConfig:
    def __init__(self, enabled: bool, prefix: str, id: int, name: str) -> None:
        self.enabled = enabled
        self.prefix = prefix
        self.id = id
        self.name = name

    def to_json(self) -> dict:
        return {
            "enabled": bool(self.enabled),
            "discoveryPrefix": str(self.prefix),
            "id": int(self.id),
            "name": str(self.name)
        }

    @staticmethod
    def from_json(json: dict) -> HA_DiscoveryConfig:
        j_enabled = json.get("enabled")
        if type(j_enabled) is not bool:
            raise ValueError(f"HA_DiscoveryConfig: Invalid enabled: '{j_enabled}'")

        j_prefix = json.get("discoveryPrefix")
        if type(j_prefix) is not str:
            raise ValueError(f"HA_DiscoveryConfig: Invalid discoveryPrefix: '{j_prefix}'")

        j_id = json.get("id")
        if type(j_id) is not int:
            raise ValueError(f"HA_DiscoveryConfig: Invalid id: '{j_id}'")

        j_name = json.get("name")
        if type(j_name) is not str:
            raise ValueError(f"HA_DiscoveryConfig: Invalid name: '{j_name}'")

        return HA_DiscoveryConfig(j_enabled, j_prefix, j_id, j_name)
