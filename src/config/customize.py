import json

# Example payload: {"Time": "2022-10-20T20:58:13", "em": {"power_total": 230.04 }}
# Read 'power_total' if it exists
def parse_power_payload(payload: bytes, inverterMax:int) -> float | None:
    jobj = json.loads(payload)
    if "em" in jobj:
        em_jobj = jobj["em"]
        if "power_total" in em_jobj:
            value = em_jobj["power_total"]
            if isinstance(value, float):
                return value

    return None

#Convert calculated new limit to mqtt payload
def command_to_payload(command: float, inverterMax:int) -> str | None:
    return f"{round(command,2):.2f}"