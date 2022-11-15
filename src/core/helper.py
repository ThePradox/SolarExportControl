import logging
import datetime
import core.appconfig as appconfig
from core.limit import LimitCalculator
from paho.mqtt import client as mqtt
from typing import Callable, Any, List


MQTT_TOPIC_META_CMD_ACTIVE = "/cmd/active"

MQTT_TOPIC_META_TELE_LAST_LIMIT = "/limit"
MQTT_TOPIC_META_TELE_OVERSHOOT = "/overshoot"
MQTT_TOPIC_META_TELE_INVERTER_STATUS = "/inverter_status"
MQTT_TOPIC_META_TELE_ACTIVE = "/active"
MQTT_TOPIC_META_TELE_ONLINE = "/status"

MQTT_PL_META_TELE_ACTIVE_TRUE = "on"
MQTT_PL_META_TELE_ACTIVE_FALSE = "off"
MQTT_PL_META_TELE_ONLINE_TRUE = "online"
MQTT_PL_META_TELE_ONLINE_FALSE = "offline"
MQTT_PL_META_TELE_INVERTER_STATUS_TRUE = "on"
MQTT_PL_META_TELE_INVERTER_STATUS_FALSE = "off"


#OnMessageCallbackType = set[Callable[[mqtt.Client, Any, mqtt.MQTTMessage, Any], None]]
#OnCmdMetaActive = set[Callable[[mqtt.Client, bool], None]]


class MqttHelper:
    def __init__(self, config: appconfig.AppConfig, loglvl=logging.root.level, mqttLogging: bool = False) -> None:
        self.config = config
        self.debug = loglvl == logging.DEBUG
        self.scheduler = ActionScheduler()
        self.subs: List[str] = []

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

    def schedule(self, seconds: int, action: Callable):
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
        r = self.client.unsubscribe(topics)
        for topic in topics:
            logging.debug(f"Unsubscribed from '{topic}' -> M-ID: {r[1]}, Code: {r[0]} - \"{mqtt.error_string(r[0])}\"")
            self.subs.remove(topic)
            
    def unsubscribe_all(self) -> None:
        if not len(self.subs):
            return
        self.unsubscribe_many([x for x in self.subs])

    def publish(self, topic: str, payload: str | None, qos: int = 0, retain: bool = False, props=None):
        self.client.publish(topic, payload, qos, retain, props)

    @staticmethod
    def received_message(msg: mqtt.MQTTMessage, type: str, parsed) -> None:
        # Skip str formating overhead on not debug (payload can be big)
        if logging.root.level == logging.DEBUG:
            logging.debug(f"Received '{type}' message: '{msg.payload}' on topic: '{msg.topic}' with QoS '{msg.qos}' was retained '{msg.retain}' -> {parsed}")

    @staticmethod
    def combine_topic_path(prefix: str, topic: str) -> str:
        return f'{prefix.removesuffix("/")}/{topic.removeprefix("/")}'

    def connect(self) -> None:
        vers_clean_start = mqtt.MQTT_CLEAN_START_FIRST_ONLY

        if self.config.mqtt.protocol == mqtt.MQTTv5:
            vers_clean_start = self.config.mqtt.clean_session

        self.client.connect(host=self.config.mqtt.host,
                            port=self.config.mqtt.port,
                            keepalive=self.config.mqtt.keepalive,
                            clean_start=vers_clean_start)

        logging.info("Connecting client ...")

    def on_connect(self, callback_success: Callable[[], None] | None, callback_error: Callable[[int], None] | None):
        self.__on_connect_success = callback_success
        self.__on_connect_error = callback_error

    def __proxy_on_connect(self, client: mqtt.Client, ud, flags, rc, props=None):
        logging.info(f"Connection response -> {rc} - \"{mqtt.connack_string(rc)}\", flags: {flags}")
        self.scheduler.clear()

        if rc == mqtt.CONNACK_ACCEPTED:
            if self.__on_connect_success is not None:
                self.__on_connect_success()
        else:
            if self.__on_connect_error is not None:
                self.__on_connect_error(rc)

    def on_disconnect(self, callback: Callable[[int], None] | None):
        self.__on_disconnect = callback

    def __proxy_on_disconnect(self, client: mqtt.Client, userdata, rc, props=None):
        logging.warning(f"Disconnected: {rc} - \"{mqtt.error_string(rc)}\"")
        self.scheduler.clear()
        if self.__on_disconnect is not None:
            self.__on_disconnect(rc)

    def __proxy_on_subscribe(self, client, userdata, mid, granted_qos_or_rcs, props=None):
        logging.debug(f"Subscribe acknowledged -> M-ID: {mid}")

    def __proxy_on_unsubscribe(self, client, userdata, mid, props=None, rc=None):
        logging.debug(f"Unsubscribe acknowledged -> M-ID: {mid}")

    def loop_forever(self):
        while True:
            self.client.loop(timeout=1.0)        
            due_actions = self.scheduler.get_due()
            if due_actions is not None:
                for action in due_actions:
                    try:
                        action()
                    except Exception as ex:
                        logging.warning(f"Failed to execute scheduled action: {ex}")


class MetaControlHelper(MqttHelper):
    def __init__(self, config: appconfig.AppConfig, loglvl=logging.root.level, mqttLogging: bool = False) -> None:
        super().__init__(config, loglvl, mqttLogging)
        self.topic_cmd_active = MqttHelper.combine_topic_path(config.meta.prefix, MQTT_TOPIC_META_CMD_ACTIVE)
        self.topic_tele_active = MqttHelper.combine_topic_path(config.meta.prefix, MQTT_TOPIC_META_TELE_ACTIVE)
        self.topic_tele_online = MqttHelper.combine_topic_path(config.meta.prefix, MQTT_TOPIC_META_TELE_ONLINE)
        self.topic_tele_last_limit = MqttHelper.combine_topic_path(config.meta.prefix, MQTT_TOPIC_META_TELE_LAST_LIMIT)
        self.topic_tele_overshoot = MqttHelper.combine_topic_path(config.meta.prefix, MQTT_TOPIC_META_TELE_OVERSHOOT)
        self.topic_tele_inverter_status = MqttHelper.combine_topic_path(config.meta.prefix, MQTT_TOPIC_META_TELE_INVERTER_STATUS)
        self.__on_cmd_active: Callable[[bool], None] | None = None

    def setup_will(self):
        self.client.will_set(self.topic_tele_online, MQTT_PL_META_TELE_ONLINE_FALSE, 0, True)

    def publish_meta_active(self, active: bool) -> None:
        payload = MQTT_PL_META_TELE_ACTIVE_TRUE if active else MQTT_PL_META_TELE_ACTIVE_FALSE
        self.publish(self.topic_tele_active, payload, 0, True)

    def publish_meta_online(self, online: bool) -> None:
        payload = MQTT_PL_META_TELE_ONLINE_TRUE if online else MQTT_PL_META_TELE_ONLINE_FALSE
        self.publish(self.topic_tele_online, payload, 0, True)

    def publish_meta_lastlimit(self, limit: str) -> None:
        self.publish(self.topic_tele_last_limit, limit, 0, True)

    def publish_meta_overshoot(self, overshoot: str) -> None:
        self.publish(self.topic_tele_overshoot, overshoot, 0, True)

    def publish_meta_inverter_status(self, status:bool) -> None:
        payload = MQTT_PL_META_TELE_INVERTER_STATUS_TRUE if status else MQTT_PL_META_TELE_INVERTER_STATUS_FALSE
        self.publish(self.topic_tele_inverter_status, payload, 0, True)

    def subscribe_cmd_active(self):
        self.subscribe(self.topic_cmd_active)

    def on_cmd_active(self, callback: Callable[[bool], None] | None):
        self.__on_cmd_active = callback
        if callback is None:
            self.client.message_callback_remove(self.topic_cmd_active)
        else:
            self.client.message_callback_add(self.topic_cmd_active, self.__proxy_on_cmd_active)

    def __proxy_on_cmd_active(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage, props=None):
        if self.__on_cmd_active is None:
            return

        pl = msg.payload.decode().lower()
        parsed: bool | None = None

        if pl == MQTT_PL_META_TELE_ACTIVE_TRUE:
            parsed = True
        elif pl == MQTT_PL_META_TELE_ACTIVE_FALSE:
            parsed = False

        MqttHelper.received_message(msg, "meta-active", parsed)

        if parsed is not None:
            self.__on_cmd_active(parsed)

    def unsubscribe_all_but_cmd_active(self) -> None:
        osubs = [sub for sub in self.subs if sub != self.topic_cmd_active]
        self.unsubscribe_many(osubs)
        

        



class AppMqttHelper(MetaControlHelper):
    def __init__(self, config: appconfig.AppConfig, loglvl=logging.root.level, mqttLogging: bool = False) -> None:
        super().__init__(config, loglvl, mqttLogging)
        self.__on_power_reading: Callable[[float], None] | None = None
        self.__on_inverter_status: Callable[[bool], None] | None = None

    def on_power_reading(self, callback: Callable[[float], None] | None, parser: Callable[[bytes], float | None]):
        self.__on_power_reading = callback
        self.__parser_power_reading = parser

        if callback is None:
            self.client.message_callback_remove(self.config.mqtt.topics.read_power)
        else:
            self.client.message_callback_add(self.config.mqtt.topics.read_power, self.__proxy_on_power_reading)

    def __proxy_on_power_reading(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage, props=None):
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

    def on_inverter_status(self, callback: Callable[[bool], None] | None, parser: Callable[[bytes], bool | None]):
        if not self.config.mqtt.topics.status:
            return

        self.__on_inverter_status = callback
        self.__parser_inverter_status = parser

        if callback is None:
            self.client.message_callback_remove(self.config.mqtt.topics.status)
        else:
            self.client.message_callback_add(self.config.mqtt.topics.status, self.__proxy_on_inverter_status)

    def __proxy_on_inverter_status(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage, props=None):
        if self.__on_inverter_status is None or not self.config.mqtt.topics.status:
            return

        try:
            value = self.__parser_inverter_status(msg.payload)
        except Exception as ex:
            logging.warning(f"Failed to parse inverter status: {ex}")
            return

        self.received_message(msg, "inverter-status", value)

        if value is not None:
            self.__on_inverter_status(value)

    def publish_limit(self, limit: str) -> None:
        if self.config.mqtt.topics.write_limit:
            r = self.publish(self.config.mqtt.topics.write_limit, limit, 0, self.config.mqtt.retain)
            logging.info(f"Published limit: '{limit}', Result: '{r}'")

    def subscribe_power_reading(self) -> None:
        self.subscribe(self.config.mqtt.topics.read_power, 0)

    def unsubscribe_power_reading(self) -> None:
        self.unsubscribe(self.config.mqtt.topics.read_power)

    def subscribe_inverter_status(self) -> None:
        if self.config.mqtt.topics.status:
            self.subscribe(self.config.mqtt.topics.status, 0)

    def unsubscribes_inverter_status(self) -> None:
        if self.config.mqtt.topics.status:
            self.unsubscribe(self.config.mqtt.topics.status)

class ActionScheduler:
    def __init__(self) -> None:
        self.items = []
        self.nextTime = datetime.datetime.max

    def schedule(self, seconds: int, action: Callable):
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

    def clear(self):
        self.items.clear()
        self.nextTime = datetime.datetime.max