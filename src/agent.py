import logging
import config as conf
import customize as cust
import paho.mqtt.client as mqtt

from limit import LimitCalculator


class ExportControlAgent:
    def __init__(self, config: conf.AppConfig) -> None:
        self.config: conf.AppConfig = config
        self.limitcalc: LimitCalculator = LimitCalculator(config)

    def run(self) -> None:
        def on_connect(client: mqtt.Client, userdata, flags, rc):
            logging.debug(f"Connected with result code: {str(rc)}")
            self.limitcalc.reset()
            client.subscribe(self.config.topic_read_power)

        def on_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
            logging.debug(f"Received message: '{msg.payload}' on topic: '{msg.topic}' with QoS '{msg.qos}'")
            value = cust.parse_power_payload(msg.payload)
            logging.debug(f"Parsed value: {value}")

            cmdval: float|None = None
            if(value is not None):
                cmdval = self.limitcalc.addReading(value)

            if cmdval is not None:
                cmdpayload = cust.command_to_payload(cmdval)

                if cmdpayload is not None:
                    r = client.publish(self.config.topic_write_limit, cmdpayload, 0, self.config.retain)
                    logging.debug(f"Command send: {r}")

        client = mqtt.Client(
            client_id=self.config.client_id,
            clean_session=self.config.clean_session,
            protocol=self.config.protocol,
        )

        client.on_connect = on_connect
        client.on_message = on_message

        #Use auth
        if bool(self.config.cred_username):
            client.username_pw_set(self.config.cred_username, self.config.cred_password)  

        #Use lwt
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
        client.loop_forever()
