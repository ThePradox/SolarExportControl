# Customize.py

Found in `/src/config/customize.py`

## **Required**: `parse_power_payload`

```python
# Convert ongoing power reading payload to float (negative = export)
def parse_power_payload(payload: bytes, command_min: float, command_max: float) -> float | None:
```

This function must be edited to return the power reading as `float`. Return `None` to discard the reading

<details><summary>Example 1</summary>

Payload comes from tasmota while the device name is set to "em":

Payload:

```json
{"Time": "2022-10-20T20:58:13", "em": {"power_total": 230.04 }}
```

Function

```python
def parse_power_payload(payload: bytes, command_min: float, command_max: float) -> float | None:
    jobj = json.loads(payload)
    if "em" in jobj:
        em_jobj = jobj["em"]
        if "power_total" in em_jobj:
            value = em_jobj["power_total"]
            if isinstance(value, float):
                return value

    return None
```

</details>

<details><summary>Example 2</summary>

Payload is just the number

Payload:

```txt
230.04
```

Function

```python
def parse_power_payload(payload: bytes, command_min: float, command_max: float) -> float | None:
    return float(payload.decode())
```

</details>

<br />

## **Required**: `command_to_payload`

```python
# Convert calculated new limit to mqtt payload
def command_to_payload(command: float, command_type: int, command_min: float, command_max: float) -> str | None:
```

This function must be edited to return the mqtt payload as `string`. Return `None` to discard the limit.

<details><summary>Example</summary>

Just round the limit to 2 decimals

```python
def command_to_payload(command: float, command_type: int, command_min: float, command_max: float) -> str | None:
    return f"{round(command,2):.2f}"
```

</details>

<br />

## Optional: `parse_status_payload`

```python
# Convert ongoing status update payload to bool (True = Active /False = Inactive)
def parse_status_payload(payload: bytes, current_status: bool) -> bool | None:
```

Only required if `config.mqtt.topics.status` is not empty

This function can be be edited to return the status from the payload of `config.mqtt.topics.status` as `bool` (True=Active / False=Inactive). Return `None` to discard message

<details><summary>Example</summary>

Test if playload is 'truthy'

```python
def parse_status_payload(payload: bytes, current_status: bool) -> bool | None:
    s = payload.decode().lower()
    return s == "1" or s == "true"
```

</details>

<br />

## Optional: `command_to_generic`

```python
# Send your command to anywhere
def command_to_generic(command: float, command_type: int, command_min: float, command_max: float, config:dict) -> None:
```

This function will get called whenever a command would be published on `config.mqtt.topics.writeCommand`.
The whole `config.customize.command` object is passed as parameter.
Send the limit over http, sql or whatever, go wild.
