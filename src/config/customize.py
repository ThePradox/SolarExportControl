import json
import requests

# Example payload: {"Time": "2022-10-20T20:58:13", "em": {"power_total": 230.04 }}
# Convert ongoing power reading payload to float (negative = export)
def parse_power_payload(payload: bytes, command_min: float, command_max: float) -> float | None:
    tasmota_device = "em"
    tasmota_value = "power_total"

    jobj = json.loads(payload)
    if tasmota_device in jobj:
        em_jobj = jobj[tasmota_device]
        if tasmota_value in em_jobj:
            value = em_jobj[tasmota_value]
            if isinstance(value, float):
                return value
            elif isinstance(value, int):
                return float(value)

    return None

# Convert calculated new limit to mqtt payload
def command_to_payload(command: float, command_type: int, command_min: float, command_max: float) -> str | None:
    return f"{round(command,2):.2f}"

# Send your command to anywhere
def command_to_generic(command: float, command_type: int, command_min: float, command_max: float, config:dict) -> None:
    pass

# Convert ongoing inverter status update payload to bool (True = Active /False = Inactive)
def parse_inverter_status_payload(payload: bytes, current_status: bool) -> bool | None:
    s = payload.decode().lower()
    return s == "1" or s == "true"

# Convert ongoing inverter power production payload to float
def parse_inverter_power_payload(payload: bytes)-> float | None:
    s = payload.decode()
    return float(s)
