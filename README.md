# SolarExportControl

## Background
Take mqtt data about your electric power consumption (from a digital electric meter for example) compare it to a target max power export and if necessary set max power of an solar inverter via mqtt.

## Original setup:
- Power reading via esp32 with tasmota and a 'hichi' IR sensor into mqtt broker
- Limiting power of inverter with an esp32 running opendtu and receiving the limit over mqtt

## Goal
- Use as little input as possible: Only a read current power topic and a command limit inverter power topic is needed
- Compatible with [OpenDTU](https://github.com/tbnobody/OpenDTU) 
- Compatible with anything that can recieve its power limit over mqtt
- Make limit calculation configurable
- Make reading mqtt power payload and writing power limit payload customizable
- Docker the whole thing?

## Implemented Features

- Most MQTT Settings exposed
- Adjustable command throttling
- Command calculation as absolute and relative
- Adjustable minimum difference between limits
- Adjustable power target
- Adjustable power reading smoothing (Average over a X samples)

## Requirements
- MQTT Broker
- A power reading sensor:
    - Publishes to MQTT Broker
    - The published value must include the inverter power
    - The published value must be negative if power is exported (inverter production greater than consumption)
    - Should publish at least every 10 seconds

- A device which can regulate its power production
    - Receive its power limit from the MQTT Broker
    - Power limit can be watts or percentage

- Python3

## How to install
1. Fullfill [Requirements](#requirements)
2. Clone or download Repo
3. Install requirements `$ pip install -r requirements.txt`
4. Modify [config](#config) to your liking
5. Modify [customize](#customize) to match your devices
6. [Run](#how-to-run)

## Customize

You must edit the `.\src\customize.py` to match your devices:

### parse_power_payload
```python
def parse_power_payload(payload: bytes) -> float | None:
```
This function must be edited to return the power reading as `float`. Return `None` to discard the reading

<details><summary>Example</summary>

My payload comes from tasmota while the device name is set to "em":
```json
{"Time": "2022-10-20T20:58:13", "em": {"power_total": 230.04 }}
```

So my function looks like this:

```python
def parse_power_payload(payload: bytes) -> float | None:
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

### command_to_payload
```python
def command_to_payload(command: float) -> str | None:
```
This function must be edited to return the mqtt payload as `string`. Return `None` to discard the limit.

<details><summary>Example</summary>

Just round the limit to 2 decimals

```python
return f"{round(command,2):.2f}"
```
</details>

## How to run
- Run with `python .\src\main.py .\config.json --verbose`
- Run with VSCode ("launch.json" should be included)

## Config

Settings in `config.json`. Properties not required can be `null`


Required | Property | Description | Type | Default
|---|---|---|---|---|
| :red_circle: | `host` | hostname or IP address of the remote broker | string ||
| | `port` | network port of the server host to connect to | int |  1883
|| `keepalive` | maximum period in seconds allowed between communications with the broker | int | 60
|| `protocol` | choose the version of the mqtt protocol to use. Use either `MQTTv31 = 3`, `MQTTv311 = 4`, `MQTTv5 = 5` | int | 4
|| `retain` | set the limit command message to be retained (true) or not (false) | bool | false
|:yellow_circle: | `clientId` | mqtt client id to use, required if `cleanSession=false` | string |  solar-export-control
|| `cleanSession` | client type. See [clean_session](https://pypi.org/project/paho-mqtt/#constructor-reinitialise) | bool | true
| :red_circle: | `topicReadPower` | MQTT-Topic to read current power draw | string | 
| :red_circle: | `topicWriteLimit` | MQTT-Topi to write power limit to | string
|| `auth.username` | set a username for broker authentication | string
|| `auth.password` | set optionally a password for broker authentication | string
|| `lastWill.topic` | topic that the will message should be published on | string
|| `lastWill.payload` | the message to send as a will. If not given a zero length message will be used as the will | string
|| `lastWill.retain` | set the will to be retained (true) or not (false) | bool | false
| :red_circle: | `inverterCommandThrottle` | time in seconds that must pass between new limit commands. Use to prevent multiple commands in a row during a longer power curve. Use `0` to disable | int |
| :red_circle: | `inverterCommandType` | - `absolute`: publish limit in watts <br/>- `relative`: publish limit in percent of `inverterMaxPower` | string:  "absolute" or "relative"
| :red_circle: | `inverterCommandMinDiff` | only publish new limit if the amount of watts difference between last limit command is greather than this value. Use `0.0` to disable | number | 
| :red_circle: | `inverterMaxPower` | max power of solar inverter | int |
| :red_circle: | `powerReadingTarget` | the power consumption this app will use as target. Typical values are `0` (Zero Export) or `-600` (in Germany "Balkonkraftwerk") | int
| :red_circle: | `powerReadingSmoothing` | - `none`: The original power reading will be used<br/>- `avg`: The average over `powerReadingSmoothingSampleSize` is used<br />Use `avg` to filter very short power spikes
| :red_circle: | `powerReadingSmoothingSampleSize` | amount of samples to use for `powerReadingSmoothing` when not `none`.<br/> `1` is the same as `powerReadingSmoothing=none`

## Precision

If you want absolute precision use:
- `inverterCommandThrottle = 0`
- `inverterCommandMinDiff = 0`
- `powerReadingSmoothing = 'none'`

However this basically will change the inverter power limit every interval since every power reading is different unless every device in your household consumes a absolute fixed amount of power.

## Suggestion to Precision

### inverterCommandThrottle
Only set this if your power reading interval is very fast (1-5 seconds), then i would suggest a value of `5`

### inverterCommandMinDiff
I would suggest about 1-3% of your `inverterMaxPower`

### powerReadingSmoothing and powerReadingSmoothingSampleSize
Use `avg` if your power reading interval is very fast (1-5 seconds).<br/>
Im still experimenting but a good rule of thumb for `powerReadingSmoothingSampleSize` seems to be:
> `(your amount of power reading per minute)` / 60 * 8


