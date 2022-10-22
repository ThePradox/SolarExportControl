from agent import ZeroExportAgent
from config import MqttConfig, AppConfig
import json


# My current payload: {"Time": "2022-10-20T20:58:13", "em": {"power_total": 230.04 }}
# Read 'power_total' if it exists
def parse_payload(payload: bytes) -> float | None:
    jobj = json.loads(payload)
    if "em" in jobj:
        em_jobj = jobj["em"]
        if "power_total" in em_jobj:
            value = em_jobj["power_total"]
            if isinstance(value, float):
                return value

    return None


mqtt_config = MqttConfig(
    host="", #IP of broker
    topic_read_power="", #Topic to listen for your current power usage
    topic_write_limit="", #Topic to write the calculated limit to
    cred_username="", #Username for auth, None if no auth
    cred_password="" #Password for auth, None of no auth
)

app_config = AppConfig(
    parse_power_payload=parse_payload #Function to call for parsing the 'topic_read_power' payload to float
)

agent = ZeroExportAgent(mqtt_config, app_config)
agent.run();
