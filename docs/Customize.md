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
def command_to_payload(command: float, command_min: float, command_max: float) -> str | None:
```

This function must be edited to return the mqtt payload as `string`. Return `None` to discard the limit.

<details><summary>Example</summary>

Just round the limit to 2 decimals

```python
def command_to_payload(command: float, command_min: float, command_max: float) -> str | None:
    return f"{round(command,2):.2f}"
```

</details>

---

## Optional: `get_status_init`

```python
# Get initial inverter status (True = Active / False = Inactive)
def get_status_init(config: dict) -> bool:
```

Only required if `config.mqtt.topics.status` is not empty

This function can be be edited to return the inital active status state (True=Active / False=Inactive). The whole `config.customize.status` object is passed as parameter.

Get´s called during start and reconnection

<details><summary>Example 1</summary>

Always start with `active`

```python
def get_status_init(config: dict) -> bool:
    return True
```

</details>

<details><summary>Example 2</summary>

Retrieve status with http request

config.json

```json
...
"customize":{
    "status": {   
        "url": "http://opendtu.local/api/livedata/status"
    },
}
...
```

```python
# Get initial inverter status (True = Active / False = Inactive)
def get_status_init(config: dict) -> bool:
    url: str = config["url"]                             # Get url from config
    resp = requests.get(url).json()                      # Get status page and parse json
    return resp["inverters"][0]["reachable"] == True     # Test if inverter is reachable
```

</details>

<br />

## Optional: `parse_status_payload`

```python
# Convert ongoing status update payload to bool (True = Active /False = Inactive)
def parse_status_payload(payload: bytes, current_status: bool) -> bool | None:
```

Only required if `config.mqtt.topics.status` is not empty

This function can be be edited to return the status from the payload of `config.mqtt.topics.status` as `bool` (True=Active / False=Inactive). Return `None`to discard message

<details><summary>Example</summary>

Test if playload is 'truthy'

```python
def parse_status_payload(payload: bytes, current_status: bool) -> bool | None:
    s = payload.decode().lower()
    return s == "1" or s == "true"
```

</details>

## Optional: `def calibrate`

```python
# Get a value thats as near as possible to current inverter power production
def calibrate(config: dict) -> float | None:
```

This application does not know how much power your inverter produces currently. This leads to an inital 'attunement' phase in which the application changes the limit without impacting the current power production of the inverter.

E.g.:

- Your inverter max limit is 1200 W
- Your inverter currently produces 400 W
- Your current consumption is -200 W
- Your target is 0 W

1. Limit will start with max limit 1200 W
2. Adjusted by the current overshot, new limit is 1000 W. Inverter production is not impacted
3. Adjusted by the current overshot, new limit is 800 W. Inverter production is not impacted
4. Adjusted by the current overshot, new limit is 600 W. Inverter production is not impacted
5. Adjusted by the current overshot, new limit is 400 W. Inverter production is not impacted
6. Adjusted by the current overshot, new limit is 200 W. Inverter production **is impacted**

if your power reading interval is not that fast, this 6 Steps can be quite long.

This function allows the application to shortcut to bullet point 5.

Return the current power production of the inverter or `None` for the default value of `config.command.maxPower`
The whole `config.customize.calibrate` object is passed as parameter.
Get´s called during start and reconnection

<details><summary>Example</summary>

Retrieve current production via http

config.json

```json
...
"calibration": {
    "url": "http://opendtu.local/api/livedata/status"
}
...
```

```python
# Get a value thats as near as possible to current inverter power production
def calibrate(config: dict) -> float | None:
    url: str = config["url"]
    resp = requests.get(url).json()
    val = resp["total"]["Power"]["v"]

    if type(val) is float:
        return val

    return None
```

</details>

## Optional: `command_to_generic`

```python
# Send your command to anywhere
def command_to_generic(command: float, command_min: float, command_max: float, config:dict) -> None:
```

This function will get called whenever a command would be published on `config.mqtt.topics.writeLimit`.
The whole `config.customize.command` object is passed as parameter.
Send the limit over http, sql or whatever, go wild.
