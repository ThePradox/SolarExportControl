import json
import requests

# Example payload: {"Time": "2022-10-20T20:58:13", "em": {"power_total": 230.04 }}
# Convert ongoing power reading payload to float (Negative = Export)
def parse_power_payload(payload: bytes, inverter_max: int) -> float | None:
    jobj = json.loads(payload)
    if "em" in jobj:
        em_jobj = jobj["em"]
        if "power_total" in em_jobj:
            value = em_jobj["power_total"]
            if isinstance(value, float):
                return value

    return None

# Convert calculated new limit to mqtt payload
def command_to_payload(command: float, inverter_max: int) -> str | None:
    return f"{round(command,2):.2f}"

# Get initial inverter status (True = Active / False = Inactive)
def get_status_init(config: dict) -> bool:
    return True

# Convert ongoing status update payload to bool (True = Active /False = Inactive)
def parse_status_payload(payload: bytes, current_status: bool) -> bool | None:
    s = payload.decode().lower()
    return s == "1" or s == "true"

# Get a value thats as near as possible to current inverter power production
def calibrate(config: dict) -> float | None:
    return None