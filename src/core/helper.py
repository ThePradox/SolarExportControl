import logging
import datetime
import time
import core.appconfig as appconfig
from paho.mqtt import client as mqtt
from typing import Callable, Any, List, Tuple


MQTT_TOPIC_META_CMD_ENABLED = "/cmd/enabled"

MQTT_TOPIC_META_TELE_READING = "tele/power"
MQTT_TOPIC_META_TELE_SAMPLE = "tele/sample"
MQTT_TOPIC_META_TELE_OVERSHOOT = "tele/overshoot"
MQTT_TOPIC_META_TELE_LIMIT = "tele/limit"
MQTT_TOPIC_META_TELE_CMD = "tele/command"

MQTT_TOPIC_META_CORE_INVERTER_STATUS = "status/inverter"
MQTT_TOPIC_META_CORE_ENABLED = "status/enabled"
MQTT_TOPIC_META_CORE_ACTIVE = "status/active"
MQTT_TOPIC_META_CORE_ONLINE = "status/online"

MQTT_PL_TRUE = "1"
MQTT_PL_FALSE = "0"


class MqttHelper:
    def __init__(self, config: appconfig.AppConfig, loglvl=logging.root.level, mqttLogging: bool = False) -> None:
        self.config = config
        self.debug = loglvl == logging.DEBUG
        self.scheduler = ActionScheduler()
        self.subs: List[str] = []

        self.__on_connect_success = None
        self.__on_connect_error = None
        self.__on_disconnect = None

        vers_clean_session = config.mqtt.clean_session

        if config.mqtt.protocol == mqtt.MQTTv5:
            vers_clean_session = None

        client = mqtt.Client(
            client_id=config.mqtt.client_id,
            clean_session=vers_clean_session,
            protocol=config.mqtt.protocol
        )

        if config.mqtt.auth:
            client.username_pw_set(config.mqtt.auth.username, config.mqtt.auth.password)

        if mqttLogging:
            client.enable_logger(logging.root)

        client.on_connect = self.__proxy_on_connect
        client.on_disconnect = self.__proxy_on_disconnect
        client.on_subscribe = self.__proxy_on_subscribe
        client.on_unsubscribe = self.__proxy_on_unsubscribe

        self.client = client

    @staticmethod
    def received_message(msg: mqtt.MQTTMessage, type: str, parsed) -> None:
        # Skip str formating overhead on not debug (payload can be big)
        if logging.root.level == logging.DEBUG:
            logging.debug(f"Received '{type}' message: '{msg.payload}' on topic: '{msg.topic}' with QoS '{msg.qos}' was retained '{msg.retain}' -> {parsed}")

    @staticmethod
    def combine_topic_path(*args: str) -> str:
        buff = []
        for arg in args:
            buff.append(arg.strip("/"))
        return "/".join(buff)

    def schedule(self, seconds: int, action: Callable) -> None:
        self.scheduler.schedule(seconds, action)

    def subscribe(self, topic: str, qos: int = 0) -> None:
        if topic in self.subs:
            return

        r = self.client.subscribe(topic)
        self.subs.append(topic)
        logging.debug(f"Subscribed to '{topic}' -> M-ID: {r[1]}, Code: {r[0]} - \"{mqtt.error_string(r[0])}\"")

    def unsubscribe(self, topic: str) -> None:
        if topic not in self.subs:
            return

        r = self.client.unsubscribe(topic)
        self.subs.remove(topic)
        logging.debug(f"Unsubscribed from '{topic}' -> M-ID: {r[1]}, Code: {r[0]} - \"{mqtt.error_string(r[0])}\"")

    def unsubscribe_many(self, topics: List[str]) -> None:
        if len(topics) == 0:
            return

        r = self.client.unsubscribe(topics)
        for topic in topics:
            logging.debug(f"Unsubscribed from '{topic}' -> M-ID: {r[1]}, Code: {r[0]} - \"{mqtt.error_string(r[0])}\"")
            self.subs.remove(topic)

    def unsubscribe_all(self) -> None:
        if not len(self.subs):
            return
        self.unsubscribe_many([x for x in self.subs])

    def publish(self, topic: str, payload: str | None, qos: int = 0, retain: bool = False, props=None) -> mqtt.MQTTMessageInfo:
        return self.client.publish(topic, payload, qos, retain, props)

    def connect(self) -> None:
        vers_clean_start = mqtt.MQTT_CLEAN_START_FIRST_ONLY

        if self.config.mqtt.protocol == mqtt.MQTTv5:
            vers_clean_start = self.config.mqtt.clean_session

        self.client.connect(host=self.config.mqtt.host,
                            port=self.config.mqtt.port,
                            keepalive=self.config.mqtt.keepalive,
                            clean_start=vers_clean_start)

        logging.info("Connecting ...")

    def on_connect(self, callback_success: Callable[[], None] | None, callback_error: Callable[[int], None] | None) -> None:
        self.__on_connect_success = callback_success
        self.__on_connect_error = callback_error

    def on_disconnect(self, callback: Callable[[int], None] | None) -> None:
        self.__on_disconnect = callback

    def reset(self) -> None:
        self.subs.clear()
        self.scheduler.clear()

    def loop_forever(self):
        attempt = 0
        delay_interval = 2
        delay_max = 60

        while True:
            while True:
                rc = self.client.loop(timeout=1.0)

                if rc is not mqtt.MQTT_ERR_SUCCESS:
                    break

                attempt = 0
                due_actions = self.scheduler.get_due()
                if due_actions is not None:
                    for action in due_actions:
                        try:
                            action()
                        except Exception as ex:
                            logging.warning(f"Failed to execute scheduled action: {ex}")

            attempt += 1
            delay = delay_interval * attempt
            delay = delay_max if delay > delay_max else delay
            time.sleep(delay)
            logging.info(f"[{attempt}]:Reconnecting ...")
            self.client.reconnect()


# region Event proxys

    def __proxy_on_connect(self, client: mqtt.Client, ud, flags, rc, props=None) -> None:
        logging.info(f"Connection response -> {rc} - \"{mqtt.connack_string(rc)}\", flags: {flags}")
        self.reset()

        if rc == mqtt.CONNACK_ACCEPTED:
            if self.__on_connect_success is not None:
                self.__on_connect_success()
        else:
            if self.__on_connect_error is not None:
                self.__on_connect_error(rc)

    def __proxy_on_disconnect(self, client: mqtt.Client, userdata, rc, props=None) -> None:
        logging.warning(f"Disconnected: {rc} - \"{mqtt.error_string(rc)}\"")
        self.reset()

        if self.__on_disconnect is not None:
            self.__on_disconnect(rc)

    def __proxy_on_subscribe(self, client, userdata, mid, granted_qos_or_rcs, props=None) -> None:
        logging.debug(f"Subscribe acknowledged -> M-ID: {mid}")

    def __proxy_on_unsubscribe(self, client, userdata, mid, props=None, rc=None) -> None:
        logging.debug(f"Unsubscribe acknowledged -> M-ID: {mid}")

# endregion


class MetaControlHelper(MqttHelper):
    def __init__(self, config: appconfig.AppConfig, loglvl=logging.root.level, mqttLogging: bool = False) -> None:
        super().__init__(config, loglvl, mqttLogging)
        self.topic_meta_cmd_enabled = MqttHelper.combine_topic_path(config.meta.prefix, MQTT_TOPIC_META_CMD_ENABLED)
        self.topic_meta_core_enabled = MqttHelper.combine_topic_path(config.meta.prefix, MQTT_TOPIC_META_CORE_ENABLED)
        self.topic_meta_core_active = MqttHelper.combine_topic_path(config.meta.prefix, MQTT_TOPIC_META_CORE_ACTIVE)
        self.topic_meta_core_online = MqttHelper.combine_topic_path(config.meta.prefix, MQTT_TOPIC_META_CORE_ONLINE)
        self.topic_meta_core_inverter_status = MqttHelper.combine_topic_path(config.meta.prefix, MQTT_TOPIC_META_CORE_INVERTER_STATUS)
        self.topic_meta_tele_limit = MqttHelper.combine_topic_path(config.meta.prefix, MQTT_TOPIC_META_TELE_LIMIT)
        self.topic_meta_tele_cmd = MqttHelper.combine_topic_path(config.meta.prefix, MQTT_TOPIC_META_TELE_CMD)
        self.topic_meta_tele_reading = MqttHelper.combine_topic_path(config.meta.prefix, MQTT_TOPIC_META_TELE_READING)
        self.topic_meta_tele_sample = MqttHelper.combine_topic_path(config.meta.prefix, MQTT_TOPIC_META_TELE_SAMPLE)
        self.topic_meta_tele_overshoot = MqttHelper.combine_topic_path(config.meta.prefix, MQTT_TOPIC_META_TELE_OVERSHOOT)
        self.__on_cmd_enabled: Callable[[bool], None] | None = None
        self.has_discovery = False
        self.has_inverter_status = bool(config.mqtt.topics.inverter_status)

        if config.meta.discovery is not None and config.meta.discovery.enabled:
            self.has_discovery = True
            self.__discovery_reading = self.__create_discovery_reading()

    def setup_will(self) -> None:
        self.client.will_set(self.topic_meta_core_online, MQTT_PL_TRUE, 0, True)

    def publish_meta_status_enabled(self, enabled: bool) -> None:
        payload = MQTT_PL_TRUE if enabled else MQTT_PL_FALSE
        self.publish(self.topic_meta_core_enabled, payload, 0, False)

    def publish_meta_status_active(self, active: bool) -> None:
        payload = MQTT_PL_TRUE if active else MQTT_PL_FALSE
        self.publish(self.topic_meta_core_active, payload, 0, False)

    def publish_meta_status_online(self, online: bool) -> None:
        payload = MQTT_PL_TRUE if online else MQTT_PL_FALSE
        self.publish(self.topic_meta_core_online, payload, 0, True)

    def publish_meta_status_inverter(self, status: bool) -> None:
        payload = MQTT_PL_TRUE if status else MQTT_PL_FALSE
        self.publish(self.topic_meta_core_inverter_status, payload, 0, False)

    def publish_meta_tele_reading(self, reading: float) -> None:
        if self.config.meta.telemetry.power:
            self.publish(self.topic_meta_tele_reading, f"{reading:.2f}", 0, False)

    def publish_meta_tele_sample(self, sample: float) -> None:
        if self.config.meta.telemetry.sample:
            self.publish(self.topic_meta_tele_sample, f"{sample:.2f}", 0, False)

    def publish_meta_tele_overshoot(self, overshoot: float) -> None:
        if self.config.meta.telemetry.overshoot:
            self.publish(self.topic_meta_tele_overshoot, f"{overshoot:.2f}", 0, False)

    def publish_meta_tele_limit(self, limit: float) -> None:
        if self.config.meta.telemetry.limit:
            self.publish(self.topic_meta_tele_limit, f"{limit:.2f}", 0, False)

    def publish_meta_tele_command(self, cmd: float) -> None:
        if self.config.meta.telemetry.command:
            self.publish(self.topic_meta_tele_cmd, f"{cmd:.2f}", 0, False)

    def publish_meta_teles(self, reading: float, sample: float, overshoot: float | None, limit: float | None) -> None:
        self.publish_meta_tele_reading(reading)
        self.publish_meta_tele_sample(sample)

        if overshoot is None:
            return

        self.publish_meta_tele_overshoot(overshoot)

        if limit is None:
            return

        self.publish_meta_tele_limit(limit)

    def publish_meta_ha_discovery(self) -> None:
        if not self.has_discovery:
            return

        if self.config.meta.telemetry:
            self.publish(self.__discovery_reading[0], self.__discovery_reading[1], 0, True)

    def subscribe_meta_cmd_enabled(self) -> None:
        self.subscribe(self.topic_meta_cmd_enabled)

    def on_meta_cmd_enabled(self, callback: Callable[[bool], None] | None) -> None:
        self.__on_cmd_enabled = callback
        if callback is None:
            self.client.message_callback_remove(self.topic_meta_cmd_enabled)
        else:
            self.client.message_callback_add(self.topic_meta_cmd_enabled, self.__proxy_on_meta_cmd_enabled)

    def __proxy_on_meta_cmd_enabled(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage, props=None) -> None:
        if self.__on_cmd_enabled is None:
            return

        pl = msg.payload.decode().lower()
        parsed: bool | None = None

        if pl == MQTT_PL_TRUE:
            parsed = True
        elif pl == MQTT_PL_FALSE:
            parsed = False

        MqttHelper.received_message(msg, "meta-enabled", parsed)

        if parsed is not None:
            self.__on_cmd_enabled(parsed)

    def __create_discovery_reading(self) -> Tuple[str, str]:
        config = self.config.meta.discovery
        if config is None or not config.enabled:
            raise ValueError("Discovery is not activated")

        obj_id = f"reading"
        node_id = f"sec_{config.id}"
        component = "sensor"
        uniq_id = f"sec_{config.id}_tele_reading"
        name = f"{config.name} Power"
        topic = self.combine_topic_path(config.prefix, component, node_id, obj_id, "config")
        payload = self.__create_discovery_payload_tele_sensor(name, self.topic_meta_tele_reading, "W", uniq_id, "power", "measurement", "mdi:power-plug")

        return (topic, payload)

    def __create_discovery_device(self) -> str:
        config = self.config.meta.discovery
        if config is None or not config.enabled:
            raise ValueError("Discovery is not activated")

        return f'{{"name":"{config.name}", "ids":"{config.id}", "mf":"Solar Export Control"}}'

    def __create_discovery_payload_tele_sensor(self, name: str, state_topic: str, unit: str, unique_id: str, dev_class: str, state_class, icon: str) -> str:
        device = self.__create_discovery_device()
        return f'{{"name": "{name}","state_topic": "{state_topic}","unit_of_measurement": "{unit}","unique_id": "{unique_id}","device_class": "{dev_class}","state_class": "{state_class}","icon": "{icon}","device": {device},"availability_mode": "all","availability": [{{"topic": "{self.topic_meta_core_online}","payload_available": "{MQTT_PL_TRUE}","payload_not_available": "{MQTT_PL_FALSE}"}},{{"topic": "{self.topic_meta_core_active}","payload_available": "{MQTT_PL_TRUE}","payload_not_available": "{MQTT_PL_FALSE}"}}]}}'


class AppMqttHelper(MetaControlHelper):
    def __init__(self, config: appconfig.AppConfig, loglvl=logging.root.level, mqttLogging: bool = False) -> None:
        super().__init__(config, loglvl, mqttLogging)
        self.__on_power_reading: Callable[[float], None] | None = None
        self.__on_inverter_status: Callable[[bool], None] | None = None

    def on_power_reading(self, callback: Callable[[float], None] | None, parser: Callable[[bytes], float | None]) -> None:
        self.__on_power_reading = callback
        self.__parser_power_reading = parser

        if callback is None:
            self.client.message_callback_remove(self.config.mqtt.topics.read_power)
        else:
            self.client.message_callback_add(self.config.mqtt.topics.read_power, self.__proxy_on_power_reading)

    def on_inverter_status(self, callback: Callable[[bool], None] | None, parser: Callable[[bytes], bool | None]) -> None:
        if not bool(self.config.mqtt.topics.inverter_status):
            return

        self.__on_inverter_status = callback
        self.__parser_inverter_status = parser

        if callback is None:
            self.client.message_callback_remove(self.config.mqtt.topics.inverter_status)
        else:
            self.client.message_callback_add(self.config.mqtt.topics.inverter_status, self.__proxy_on_inverter_status)

    def __proxy_on_power_reading(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage, props=None) -> None:
        if self.__on_power_reading is None:
            return

        try:
            value = self.__parser_power_reading(msg.payload)
        except Exception as ex:
            logging.warning(f"customize.parse_power_payload failed: {ex}")
            return

        self.received_message(msg, "power-reading", value)

        if value is not None:
            self.__on_power_reading(value)

    def __proxy_on_inverter_status(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage, props=None) -> None:
        if self.__on_inverter_status is None or not self.has_inverter_status:
            return

        try:
            value = self.__parser_inverter_status(msg.payload)
        except Exception as ex:
            logging.warning(f"Failed to parse inverter status: {ex}")
            return

        self.received_message(msg, "inverter-status", value)

        if value is not None:
            self.__on_inverter_status(value)

    def publish_command(self, command: str) -> None:
        if self.config.mqtt.topics.write_limit:
            r = self.publish(self.config.mqtt.topics.write_limit, command, 0, self.config.mqtt.retain)
            logging.info(f"Published limit: '{command}', Result: '{r}'")

    def subscribe_power_reading(self) -> None:
        self.subscribe(self.config.mqtt.topics.read_power, 0)

    def unsubscribe_power_reading(self) -> None:
        self.unsubscribe(self.config.mqtt.topics.read_power)

    def subscribe_inverter_status(self) -> None:
        if self.has_inverter_status and self.config.mqtt.topics.inverter_status:
            self.subscribe(self.config.mqtt.topics.inverter_status, 0)

    def unsubscribes_inverter_status(self) -> None:
        if self.has_inverter_status and self.config.mqtt.topics.inverter_status:
            self.unsubscribe(self.config.mqtt.topics.inverter_status)


class ActionScheduler:
    def __init__(self) -> None:
        self.items = []
        self.nextTime = datetime.datetime.max

    def schedule(self, seconds: int, action: Callable) -> None:
        when = datetime.datetime.utcnow() + datetime.timedelta(seconds=seconds)
        self.items.append((when, action))
        if self.nextTime > when:
            self.nextTime = when

    def get_due(self) -> List[Callable] | None:
        now = datetime.datetime.utcnow()

        if self.nextTime <= now:
            self.nextTime = datetime.datetime.max
            hits = []

            for item in self.items:
                if item[0] <= now:
                    hits.append(item)
                elif self.nextTime > item[0]:
                    self.nextTime = item[0]

            if (len(hits) == 0):
                return None

            results = []
            for hit in hits:
                self.items.remove(hit)
                results.append(hit[1])

            return results
        return None

    def clear(self) -> None:
        self.items.clear()
        self.nextTime = datetime.datetime.max
