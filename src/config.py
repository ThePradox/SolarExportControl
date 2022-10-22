from typing import Callable
import paho.mqtt.client as mqtt


class MqttConfig:
    def __init__(self, host: str, topic_read_power: str, topic_write_limit: str,
                 last_will_topic: str | None = None, last_will_payload: str | None = None, last_will_retain: bool = False,
                 cred_username: str | None = None,
                 cred_password: str | None = None,
                 port: int = 1883, keepalive: int = 60, protocol: int = mqtt.MQTTv311,
                 retain: bool = False, client_id: str = "",
                 clean_session: bool = True, transport: str = "tcp") -> None:

        self.host: str = host
        self.topic_read_power: str = topic_read_power
        self.topic_write_limit: str = topic_write_limit
        self.last_will_topic: str | None = last_will_topic
        self.last_will_payload: str | None = last_will_payload
        self.last_will_retain: bool = last_will_retain
        self.cred_username: str | None = cred_username
        self.cred_password: str | None = cred_password
        self.port: int = port
        self.keepalive: int = keepalive
        self.protocol: int = protocol
        self.retain: bool = retain
        self.client_id: str = client_id
        self.clean_session = clean_session
        self.transport = transport

    def use_credentials(self) -> bool:
        return bool(self.cred_username)

    def use_last_will(self) -> bool:
        return bool(self.last_will_topic)


class AppConfig:
    def __init__(self, parse_power_payload: Callable[[bytes], float|None]) -> None:
        self.parse_power_payload: Callable[[bytes], float|None] = parse_power_payload
