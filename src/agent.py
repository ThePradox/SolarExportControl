import config as conf
import customize as cust
import paho.mqtt.client as mqtt


class ExportControlAgent:
    def __init__(self, config: conf.AppConfig) -> None:
        self.config: conf.AppConfig = config

    def run(self) -> None:
        def on_connect(client: mqtt.Client, userdata, flags, rc):
            print("Connected with result code " + str(rc))
            client.subscribe(self.config.topic_read_power)

        def on_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
            print("Received message: '{0}' on topic: '{1}' with QoS '{2}'".format(msg.payload, msg.topic, msg.qos))
            value = cust.parse_power_payload(msg.payload)
            print("Parsed value: {0}".format(value))

        client = mqtt.Client(
            client_id=self.config.client_id,
            clean_session=self.config.clean_session,
            protocol=self.config.protocol,
        )

        client.on_connect = on_connect
        client.on_message = on_message

        if self.config.use_credentials():
            client.username_pw_set(
                self.config.cred_username, self.config.cred_password)

        if self.config.use_last_will():
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
