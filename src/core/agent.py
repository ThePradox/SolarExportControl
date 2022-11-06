import logging
import config.customize as customize
import core.setup as setup
from core.limit import LimitCalculator
from paho.mqtt import client as mqtt


class ExportControlAgent:
    def __init__(self, config: setup.AppConfig) -> None:
        self.config: setup.AppConfig = config
        self.limitcalc: LimitCalculator = LimitCalculator(config)
        self.status_current = True

    def run(self) -> None:
        def on_connect(client: mqtt.Client, userdata, flags, rc):
            logging.info(f"Connected with result code: {str(rc)}")
            self.limitcalc.reset()
            self.status_current = True

            if self.config.mqtt.topics.status:
                self.__subscribe(client, self.config.mqtt.topics.status)

                try:
                    self.status_current = customize.get_status_init(self.config.customize.status)
                    logging.info(f"Init status: {'Active' if self.status_current else 'Inactive'}")
                except Exception as ex:
                    logging.warning(f"Failed to get init status: {ex}")

            if self.status_current:
                self.__subscribe(client, self.config.mqtt.topics.read_power)

        def on_disconnect(client: mqtt.Client, userdata, rc):
            logging.warning(f"Disconnected with result code: {str(rc)}")

        def on_status_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
            value = customize.parse_status_payload(msg.payload, self.status_current)
            self.__received_message(msg, "status", value)
          
            if value == None:
                return

            if self.status_current != value:
                if value:
                    logging.info("New status: Active")
                    self.limitcalc.reset()
                    self.__subscribe(client, self.config.mqtt.topics.read_power)
                else:
                    logging.info("New status: Inactive")
                    self.__unsubscribe(client, self.config.mqtt.topics.read_power)

            self.status_current = value

        def on_reading_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):           
            value = customize.parse_power_payload(msg.payload, self.config.command.min_power, self.config.command.max_power)
            self.__received_message(msg, "reading", value)
          
            cmdval: float | None = None
            if (value is not None):
                cmdval = self.limitcalc.add_reading(value)

            if cmdval is not None:
                cmdpayload = customize.command_to_payload(cmdval, self.config.command.min_power, self.config.command.max_power)

                if cmdpayload is not None:
                    if self.config.mqtt.topics.write_limit:
                        r = client.publish(self.config.mqtt.topics.write_limit, cmdpayload, 0, self.config.mqtt.retain)
                        logging.info(f"Published limit: '{cmdpayload}', Result: '{r}'")

                try:
                    customize.command_to_generic(cmdval,self.config.command.min_power, self.config.command.max_power, self.config.customize.command)
                except Exception as ex:
                    logging.warning(f"customize.command_to_generic failed: {ex}")

        client = mqtt.Client(
            client_id=self.config.mqtt.client_id,
            clean_session=self.config.mqtt.clean_session,
            protocol=self.config.mqtt.protocol,
        )

        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.message_callback_add(self.config.mqtt.topics.read_power, on_reading_message)

        if self.config.mqtt.topics.status:
            client.message_callback_add(self.config.mqtt.topics.status, on_status_message)

        # Use auth
        if self.config.mqtt.auth:
            client.username_pw_set(self.config.mqtt.auth.username, self.config.mqtt.auth.password)

        # Use lwt
        if self.config.mqtt.topics.last_will and self.config.mqtt.last_will:
            client.will_set(
                topic=self.config.mqtt.topics.last_will,
                payload=self.config.mqtt.last_will.payload,
                retain=self.config.mqtt.last_will.retain)

        client.connect(
            host=self.config.mqtt.host,
            port=self.config.mqtt.port,
            keepalive=self.config.mqtt.keepalive)

        logging.info("Connecting...")
        client.loop_forever()

    @staticmethod
    def __subscribe(client: mqtt.Client, topic: str):
        client.subscribe(topic)
        logging.debug(f"Subscribed to '{topic}'")

    @staticmethod
    def __unsubscribe(client: mqtt.Client, topic: str):
        client.unsubscribe(topic)
        logging.debug(f"Unsubscribed from '{topic}'")

    @staticmethod
    def __received_message(msg: mqtt.MQTTMessage, type: str, parsed):
        logging.debug(f"Received {type} message: '{msg.payload}' on topic: '{msg.topic}' with QoS '{msg.qos}' -> {parsed}")
