from config import MqttConfig, AppConfig
import paho.mqtt.client as mqtt


class ZeroExportAgent:
    def __init__(self, mqtt_config: MqttConfig, app_config: AppConfig) -> None:
        self.mqtt_config: MqttConfig = mqtt_config
        self.app_config: AppConfig = app_config

    def run(self) -> None:
        def on_connect(client: mqtt.Client, userdata, flags, rc):
            print("Connected with result code "+str(rc))
            client.subscribe(self.mqtt_config.topic_read_power)

        def on_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
            print("Received message '" + str(msg.payload) +
                  "' on topic '" + msg.topic + "' with QoS " + str(msg.qos))
            value = self.app_config.parse_power_payload(msg.payload)
            print("Parsed value: "+str(value))

        client = mqtt.Client(
            client_id=self.mqtt_config.client_id,
            clean_session=self.mqtt_config.clean_session,
            protocol=self.mqtt_config.protocol,
            transport=self.mqtt_config.transport)

        client.on_connect = on_connect
        client.on_message = on_message

        if self.mqtt_config.use_credentials():
            client.username_pw_set(
                self.mqtt_config.cred_username, self.mqtt_config.cred_password)

        if self.mqtt_config.use_last_will():
            client.will_set(self.mqtt_config.last_will_topic,
                            self.mqtt_config.last_will_payload, retain=self.mqtt_config.last_will_retain)

        client.connect(host=self.mqtt_config.host,
                       port=self.mqtt_config.port,
                       keepalive=self.mqtt_config.keepalive)
        client.loop_forever()
