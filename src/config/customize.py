import json
import requests

# Example payload: {"Time": "2022-10-20T20:58:13", "em": {"power_total": 230.04 }}
# Convert ongoing power reading payload to float (negative = export)
def parse_power_payload(payload: bytes, command_min: float, command_max: float) -> float | None:
    jobj = json.loads(payload)
    if "em" in jobj:
        em_jobj = jobj["em"]
        if "power_total" in em_jobj:
            value = em_jobj["power_total"]
            if isinstance(value, float):
                return value

    return None

# Convert calculated new limit to mqtt payload
def command_to_payload(command: float, command_type: int, command_min: float, command_max: float) -> str | None:
    return f"{round(command,2):.2f}"

# Send your command to anywhere
def command_to_generic(command: float, command_type: int, command_min: float, command_max: float, config:dict) -> None:
    pass

# Convert ongoing status update payload to bool (True = Active /False = Inactive)
def parse_inverter_status_payload(payload: bytes, current_status: bool) -> bool | None:
    s = payload.decode().lower()
    return s == "1" or s == "true"
