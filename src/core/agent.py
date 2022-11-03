import logging
import config.customize as customize
import core.setup as setup
from core.limit import LimitCalculator
from paho.mqtt import client as mqtt


class ExportControlAgent:
    def __init__(self, config: setup.AppConfig) -> None:
        self.config: setup.AppConfig = config
        self.limitcalc: LimitCalculator = LimitCalculator(config)       

    def run(self) -> None:
        def on_connect(client: mqtt.Client, userdata, flags, rc):
            logging.info(f"Connected with result code: {str(rc)}")
            self.limitcalc.reset()
            client.subscribe(self.config.topic_read_power)
            logging.debug(f"Subscribed to '{self.config.topic_read_power}'")

        def on_disconnect(client: mqtt.Client, userdata, rc):
            logging.warning(f"Disconnected with result code: {str(rc)}")

        def on_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
            logging.debug(f"Received message: '{msg.payload}' on topic: '{msg.topic}' with QoS '{msg.qos}'")
            value = customize.parse_power_payload(msg.payload, self.config.inverter_max_power)
            logging.debug(f"Parsed value: {value}")

            cmdval: float | None = None
            if (value is not None):
                cmdval = self.limitcalc.addReading(value)

            if cmdval is not None:
                cmdpayload = customize.command_to_payload(cmdval, self.config.inverter_max_power)

                if cmdpayload is not None:
                    r = client.publish(self.config.topic_write_limit, cmdpayload, 0, self.config.retain)
                    logging.info(f"New limit send: '{cmdpayload}', Result: '{r}'")

        client = mqtt.Client(
            client_id=self.config.client_id,
            clean_session=self.config.clean_session,
            protocol=self.config.protocol,
        )

        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message

        # Use auth
        if bool(self.config.cred_username):
            client.username_pw_set(
                self.config.cred_username, self.config.cred_password)

        # Use lwt
        if bool(self.config.last_will_topic):
            client.will_set(
                self.config.last_will_topic,
                self.config.last_will_payload,
                retain=self.config.last_will_retain,
            )

        client.connect(
            host=self.config.host,
            port=self.config.port,
            keepalive=self.config.keepalive,
        )
        logging.info("Connecting...")
        client.loop_forever()