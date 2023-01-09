# Config

Found in `/src/config/config.json`. Properties not required can be `null`

## MQTT

```json
...
    "mqtt": {
        "host": "192.168.1.2",
        "port": 1883,
        "keepalive": 60,
        "protocol": 5,
        "retain": false,
        "clientId": "sec_1673108642",
        "cleanSession": true,
        "topics": {
            "readPower": "power/xxx-xxx-xxx/tele/SENSOR",
            "writeCommand": "solar/xxx/cmd/limit_nonpersistent_relative",
            "inverterStatus": "solar/xxx/status/producing"
        },
        "auth": {
            "username": "my-user",
            "password": "my-password"
        }
    },
...
```

### MQTT Properties

Setup basic mqtt properties

|Req                | Property               | Type              | Default       | Description
|---                | ---                    | ---               |---            |---
| :red_circle:      | `mqtt.host`            | string            |               | hostname or IP address of the remote broker
|                   | `mqtt.port`            | int               | 1883          | network port of the server host to connect to
|                   | `mqtt.keepalive`       | int               | 60            | maximum period in seconds allowed between communications with the broker
|                   | `mqtt.protocol`        | int               | 4             | version of the mqtt protocol to use. `MQTTv31 = 3`, `MQTTv311 = 4`, `MQTTv5 = 5`
|                   | `mqtt.retain`          | bool              | false         | set the limit command message to be retained (true) or not (false)
|:yellow_circle:    | `mqtt.clientId`        | string            | solar-export-control | mqtt client id to use, required if `cleanSession=false` or if multiple instances of this program are running
|                   | `mqtt.cleanSession`    | bool              | true          | client type. See [clean_session](https://pypi.org/project/paho-mqtt/#constructor-reinitialise)
| :red_circle:      | `mqtt.topics`          | object            |               | controls mqtt topics
|                   | `mqtt.auth`            | object            | null          | controls mqtt auth

### MQTT.TOPICS Properties

Setup mqtt topics

|Req                | Property               | Type             | Default       | Description
|---                | ---                    | ---              |---            |---
| :red_circle:      | `topics.readPower`     | string           |               | MQTT-Topic to read current power draw
|                   | `topics.writeCommand`  | string           |               | MQTT-Topic to write power limit command to
|                   | `topics.inverterStatus`| string           |               | MQTT-Topic to listens for inverter status updates

### MQTT.AUTH Properties

Setup mqtt broker authentication. **Will only be used If `username` is not empty**

|Req                | Property               | Type             | Default       | Description
|---                | ---                    | ---              |---            |---
| :red_circle:      | `auth.username`        | string           |               | set a username for broker authentication
|                   | `auth.password`        | string           | null          | set a password for broker authentication

<br />

---

<br />

## COMMAND

```json
...
    "command": {
        "target": -100,
        "minPower": 24,
        "maxPower": 1200,
        "type": "relative",
        "throttle": 6,
        "hysteresis": 24.0,
        "retransmit": 0
    },
...
```

### COMMAND Properties

Setup how commands will be issued

|Req                | Property               | Type             | Unit          | Description
|---                | ---                    | ---              |---            |---
| :red_circle:      | `command.target`       | int              | Watt (W)      | power consumption this app will use as target. Typical values are `0` (Zero Export) or `-600` (in Germany "Balkonkraftwerk")
| :red_circle:      | `command.minPower`     | int              | Watt (W)      | the lower power limit the inverter can be set to
| :red_circle:      | `command.maxPower`     | int              | Watt (W)      | the upper power limit the inverter can be set to
| :red_circle:      | `command.type`         | string: "absolute" or "relative"|| controls wether the limit command is absolute in watts (W) or in relative percent of `command.maxPower`
| :red_circle:      | `command.throttle`     | int              | Seconds (s)   | time that must pass between limit commands. Use `0` to disable
| :red_circle:      | `command.hysteresis`   | number           | Watt (W)      | minimum difference between two limit commands. Use `0.00` to disable
| :red_circle:      | `command.retransmit`   | int              | Seconds       | time after which `command.hysteresis` is ignored to retransmit the limit command. Useful if commands can get 'lost' on the way to the inverter. Use `0` to disable

<br />

---

<br />

## READING

```json
...
    "reading": {
        "offset": 0,
        "smoothing": "avg",
        "smoothingSampleSize": 8
    },
...
```

### READING Properties

Setup how power reading will be handled

|Req                | Property               | Type             | Default       | Description
|---                | ---                    | ---              |---            |---
|                   | `reading.offset`       | int              | 0             | specifiy an offset in watts (W) to add or subtract
|                   | `reading.smoothing`    | string: "avg" or null| null      | - null: original power reading will be used<br/>- `avg`: average of `reading.smoothingSampleSize` is used<br />Use `avg` to filter short power spikes
|                   | `reading.smoothingSampleSize`| int        | 0             | amount of samples to use for `reading.smoothing` when not `none`

<br />

---

<br />

## META

````json
...
    "meta": {
        "prefix": "solarexportcontrol",
        "resetInverterLimitOnInactive": true,
        "telemetry": {
            "power": true,
            "sample": true,
            "overshoot": true,
            "limit": true,
            "command": true
        },
        "homeAssistantDiscovery": {
            "enabled": true,
            "discoveryPrefix": "homeassistant",
            "id": 1,
            "name": "SEC"
        }
    },
...
````

### META Properties

Setup how this application can be controlled and how it publishes telemetry

|Req                | Property                            | Type          | Description
|---                | ---                                 | ---           |---
| :red_circle:      | `meta.prefix`                       | string        | Prefix used for every mqtt topic managed by this application
| :red_circle:      | `meta.resetInverterLimitOnInactive` | bool          | Should the inverter limit be reset to max when application is disabled?
| :red_circle:      | `meta.telemtry`                     | object        | Manages the information which are published as mqtt topics
| :red_circle:      | `meta.homeAssistantDiscovery`       | object        | Manages the home assistant auto discovery

### META.TELEMETRY Properties

Setup which values are published as telemetry

|Req                | Property                            | Type | Unit     | Description
|---                | ---                                 | ---  |---       |---
| :red_circle:      | `telemetry.power`                   | bool | Watt (W) | Outputs the raw power value as parsed from `mqtt.topics.readPower`
| :red_circle:      | `telemetry.sample`                  | bool | Watt (W) | Outputs the power value after applying `reading.offset` and `reading.smoothing`
| :red_circle:      | `telemetry.overshoot`               | bool | Watt (W) | Outputs the difference between the last sample and `command.target`
| :red_circle:      | `telemetry.limit`                   | bool | Watt (W) | Outputs the calculated inverter limit
| :red_circle:      | `telemetry.command`                 | bool | Watt (W) or Percent (%) | Outputs the last issued inverter limit command as published in `mqtt.topics.writeCommand`. Watt if `command.type` is absolute, percent if relative

### META.HOMEASSISTANTDISCOVERY

Setup the home assistant integration (auto discovery of telemetry)

|Req                | Property                                 | Type   | Description
|---                | ---                                      | ---    |---
| :red_circle:      | `homeAssistantDiscovery.enabled`         | bool   | Enables or disables the integration
| :red_circle:      | `homeAssistantDiscovery.discoveryPrefix` | string | Sets home assistant auto discovery topic prefix. Use `homeassistant` unless you have changed this in home assistant
| :red_circle:      | `homeAssistantDiscovery.id`              | int    | Used for creating the unique id in home assistant. Only change this if you run multiple instances of this program
|  :red_circle:     | `homeAssistantDiscovery.name`            | string | The name of the device and entites in home assistant

## CUSTOMIZE

```json
...
"customize": {
    "status": {},
    "calibration": {},
    "command": {}
}
...
```

### CUSTOMIZE Properties

Specify arbitrary data to pass to `customize.py` functions

|Req                | Property               | Type             | Default       | Description
|---                | ---                    | ---              |---            |---
|                   | `customize.status`     | object           | (empty) object| data passed to `get_status_init` in `customize.py`
|                   | `customize.calibration`| object           | (empty) object| data passed to `calibrate` in `customize.py`
|                   | `customize.command`    | object           | (empty) object| data passed to `command_to_generic` in `customize.py`
