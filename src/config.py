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
    def __init__(self, host: str, topic_read_power: str, topic_write_limit: str,
                 inverter_command_throttle: int, inverter_command_min_diff:float, inverter_command_type: InverterCommandType, inverter_max_power: int,
                 power_reading_target:int, power_reading_smoothing: PowerReadingSmoothingType, power_reading_smoothing_sample_size: int,
                 last_will_topic: str | None = None,
                 last_will_payload: str | None = None,
                 last_will_retain: bool | None = None,
                 cred_username: str | None = None,
                 cred_password: str | None = None,
                 port: int | None = None,
                 keepalive: int | None = None,
                 protocol: int | None = None,
                 retain: bool | None = None,
                 client_id: str | None = None,
                 clean_session: bool | None = None,
                 ) -> None:

        self.host: str = host
        self.topic_read_power: str = topic_read_power
        self.topic_write_limit: str = topic_write_limit
        self.inverter_command_throttle: int = inverter_command_throttle
        self.inverter_command_type: InverterCommandType = inverter_command_type
        self.inverter_command_min_diff: float = inverter_command_min_diff
        self.inverter_max_power: int = inverter_max_power
        self.power_reading_target: int = power_reading_target
        self.power_reading_smoothing: PowerReadingSmoothingType = power_reading_smoothing
        self.power_reading_smoothing_sample_size: int = power_reading_smoothing_sample_size
        self.last_will_topic: str | None = last_will_topic
        self.last_will_payload: str | None = last_will_payload
        self.last_will_retain: bool = last_will_retain if last_will_retain is not None else False
        self.cred_username: str | None = cred_username
        self.cred_password: str | None = cred_password
        self.port: int = port if port is not None else 1883
        self.keepalive: int = keepalive if keepalive is not None else 60
        self.protocol: int = protocol if protocol is not None else mqtt.MQTTv311
        self.retain: bool = retain if retain is not None else False
        self.client_id: str = client_id if client_id is not None else "solar-export-control"
        self.clean_session = clean_session if clean_session is not None else True


def config_from_json(path: str) -> AppConfig:
    fs = open(path, "r")
    jf = json.load(fs)

    j_host: str = jf.get("host")
    if j_host is None or type(j_host) is not str or j_host == "":
        raise ValueError("Config: Invalid host")

    j_topic_read_power: str = jf.get("topicReadPower")
    if j_topic_read_power is None or j_topic_read_power == "":
        raise ValueError("Config: Invalid topicReadPower")

    j_topic_write_limit: str = jf.get("topicWriteLimit")
    if j_topic_write_limit is None or j_topic_write_limit == "":
        raise ValueError("Config: Invalid topicWriteLimit")

    j_inverter_command_throttle: int = jf.get("inverterCommandThrottle")
    if j_inverter_command_throttle is None or type(j_inverter_command_throttle) is not int:
        raise ValueError("Config: Invalid inverterCommandThrottle")

    j_inverter_command_type = jf.get("inverterCommandType")
    e_inverter_command_type: InverterCommandType

    if j_inverter_command_type == "absolute":
        e_inverter_command_type = InverterCommandType.ABSOLUTE
    elif j_inverter_command_type == "relative":
        e_inverter_command_type = InverterCommandType.RELATIVE
    else:
        raise ValueError("Config: Invalid inverterCommandType")

    j_inverter_min_diff = jf.get("inverterCommandMinDiff")
    if type(j_inverter_min_diff) is not float or j_inverter_min_diff < 0:
        raise ValueError("Config: Invalid inverterCommandMinDiff")

    j_inverter_max_power = jf.get("inverterMaxPower")
    if type(j_inverter_max_power) is not int or j_inverter_max_power < 0:
        raise ValueError("Config: Invalid inverterMaxPower")


    j_power_reading_target:int = jf.get("powerReadingTarget")
    if type(j_power_reading_target) is not int:
        raise ValueError("Config: Invalid powerReadingTarget")

    j_power_reading_smoothing:str = jf.get("powerReadingSmoothing")
    e_power_reading_smoothing: PowerReadingSmoothingType = PowerReadingSmoothingType.NONE

    if(j_power_reading_smoothing == "avg"):
        e_power_reading_smoothing = PowerReadingSmoothingType.AVG

    j_power_reading_smoothing_sample_size: int = jf.get("powerReadingSmoothingSampleSize")
    if j_power_reading_smoothing_sample_size is None or type(j_power_reading_smoothing_sample_size) is not int or j_power_reading_smoothing_sample_size < 0: 
        j_power_reading_smoothing_sample_size = 0

    j_port: int | None = None
    j_keepalive: int | None = None
    j_protocol: int | None = None
    j_retain: bool | None = None
    j_client_id: str | None = None
    j_clean_session: bool | None = None

    t = jf.get("port")
    if type(t) is int and t > 0:
        j_port = t

    t = jf.get("keepalive")
    if type(t) is int and t > 0:
        j_keepalive = t

    t = jf.get("protocol")
    if type(t) is int:
        j_protocol = t

    t = jf.get("retain")
    if type(t) is bool:
        j_retain = t

    t = jf.get("clientId")
    if type(t) is str:
        j_client_id = t

    t = jf.get("cleanSession")
    if type(t) is bool:
        j_clean_session = t

    j_last_will = jf.get("lastWill")
    j_last_will_topic: str | None = None
    j_last_will_payload: str | None = None
    j_last_will_retain: bool | None = None

    if type(j_last_will) is dict:
        t = j_last_will.get("topic")
        if type(t) is str:
            j_last_will_topic = t

        t = j_last_will.get("payload")
        if type(t) is str:
            j_last_will_payload = t

        t = j_last_will.get("retain")
        if type(t) is bool:
            j_last_will_retain = t

    j_auth = jf.get("auth")
    j_auth_user: str | None = None
    j_auth_pw: str | None = None

    if type(j_auth) is dict:
        t = j_auth.get("username")
        if type(t) is str:
            j_auth_user = t

        t = j_auth.get("password")
        if type(t) is str:
            j_auth_pw = t

    conf = AppConfig(
        host=j_host,
        topic_read_power=j_topic_read_power,
        topic_write_limit=j_topic_write_limit,
        inverter_command_throttle=j_inverter_command_throttle,
        inverter_command_type=e_inverter_command_type,
        inverter_command_min_diff=j_inverter_min_diff,
        inverter_max_power=j_inverter_max_power,
        power_reading_target=j_power_reading_target,
        power_reading_smoothing=e_power_reading_smoothing,
        power_reading_smoothing_sample_size=j_power_reading_smoothing_sample_size,
        last_will_topic=j_last_will_topic,
        last_will_payload=j_last_will_payload,
        last_will_retain=j_last_will_retain,
        cred_username=j_auth_user,
        cred_password=j_auth_pw,
        port=j_port,
        keepalive=j_keepalive,
        protocol=j_protocol,
        retain=j_retain,
        client_id=j_client_id,
        clean_session=j_clean_session
    )

    return conf
