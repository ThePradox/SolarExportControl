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

            if self.config.status_topic:
                client.subscribe(self.config.status_topic)
                logging.debug(f"Subscribed to '{self.config.status_topic}'")
                
                try:
                    self.status_current = customize.get_status_init(self.config.status_config)
                    logging.info(f"Init status: {'Active' if self.status_current else 'Inactive'}")
                except Exception as ex:
                    logging.warning(f"Failed to get init status: {ex}") 
                    
            if self.status_current:          
                client.subscribe(self.config.topic_read_power)
                logging.debug(f"Subscribed to '{self.config.topic_read_power}'")

        def on_disconnect(client: mqtt.Client, userdata, rc):
            logging.warning(f"Disconnected with result code: {str(rc)}")

        def on_status_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
            logging.debug(f"Received status message: '{msg.payload}' on topic: '{msg.topic}' with QoS '{msg.qos}'")
            value = customize.parse_status_payload(msg.payload, self.status_current)
            logging.debug(f"Parsed value: {value}")

            if value == None:
                return

            if self.status_current != value:
                if value:
                    logging.info("New status: Active")
                    self.limitcalc.reset()
                    client.subscribe(self.config.topic_read_power)
                    logging.debug(f"Subscribed to '{self.config.topic_read_power}'")
                else:
                    logging.info("New status: Inactive")
                    client.unsubscribe(self.config.topic_read_power)
                    logging.debug(f"Unsubscribed to '{self.config.topic_read_power}'")

            self.status_current = value


        def on_reading_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
            logging.debug(f"Received reading message: '{msg.payload}' on topic: '{msg.topic}' with QoS '{msg.qos}'")
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
        client.message_callback_add(self.config.topic_read_power, on_reading_message)

        if self.config.status_topic:
            client.message_callback_add(self.config.status_topic, on_status_message)

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