# Customize.py

## **Required**: `parse_power_payload`

```python
def parse_power_payload(payload: bytes, inverter_max:int) -> float | None:
```

This function must be edited to return the power reading as `float`. Return `None` to discard the reading

<details><summary>Example</summary>

Payload comes from tasmota while the device name is set to "em":

```json
{"Time": "2022-10-20T20:58:13", "em": {"power_total": 230.04 }}
```

So my function looks like this:

```python
def parse_power_payload(payload: bytes, inverter_max:int) -> float | None:
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

<br />

## **Required**: `command_to_payload`

```python
def command_to_payload(command: float, inverter_max:int) -> str | None:
```

This function must be edited to return the mqtt payload as `string`. Return `None` to discard the limit.

<details><summary>Example</summary>

Just round the limit to 2 decimals

```python
def command_to_payload(command: float, inverter_max:int) -> str | None:
    return f"{round(command,2):.2f}"
```

</details>

---

## Optional: `get_status_init`

```python
def get_status_init(config: dict) -> bool:
```

Only required if active status is used.

This function can be be edited to return the inital active status state (True=Active / False=Inactive). The whole `status` dict from `config.json` is passed as parameter.

Get´s called during start and reconnection

<details><summary>Example 1</summary>

Always start with `active`

```python
def get_status_init(config: dict) -> bool:
    return True
```

</details>

<details><summary>Example 2</summary>

Retrieve status wie http

config.json

```json
...
    "status": {
        "topic": "my/status/topic",
        "url": "http://opendtu.local/api/livedata/status"
    },
...
```

```python
# Get initial inverter status (True = Active / False = Inactive)
def get_status_init(config: dict) -> bool:
    url: str = config["url"]                    # Get url from config
    resp = requests.get(url).json()             # Get status page and parse json
    return resp[0].get("reachable") == True     # Test if inverter is reachable
```

</details>

<br />

## Optional: `parse_status_payload`

```python
def parse_status_payload(payload: bytes, current_status: bool) -> bool | None:
```

Only required if active status is used.

This function can be be edited to return to parse the payload of `status.topic` to `bool` (True=Active / False=Inactive). Return `None`to discard message

<details><summary>Example</summary>

Test if playload is 'truthy'

```python
def parse_status_payload(payload: bytes, current_status: bool) -> bool | None:
    s = payload.decode().lower()
    return s == "1" or s == "true"
```

</details>

## Optional: `def calibrate`

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

if your power reading interval is not that fast, this 6 Steps can add up to several minutes.

This function allows the application to shortcut to bullet point 5.

Return the current power production of the inverter or `None` for default of `inverterMaxPower`

Get´s called during start and reconnection

```python
def calibrate(config: dict) -> float | None:
```

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
    val = resp[0]["0"]["Power"]["v"]

    if type(val) is float:
        return val

    return None
```

</details>
