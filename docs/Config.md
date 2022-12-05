# Config

Found in `/src/config/config.json`. Properties not required can be `null`

## MQTT

```json
...
"mqtt": {
    "host": "",
    "port": null,
    "keepalive": null,
    "protocol": null,
    "retain": null,
    "clientId": null,
    "cleanSession": true,

    "topics": {
        "readPower": "",
        "writeLimit": null,
        "status": null
    },

    "auth": {
        "username": "",
        "password": null
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
|:yellow_circle:    | `mqtt.clientId`        | string            | solar-export-control | mqtt client id to use, required if `cleanSession=false`
|                   | `mqtt.cleanSession`    | bool              | true          | client type. See [clean_session](https://pypi.org/project/paho-mqtt/#constructor-reinitialise)
| :red_circle:      | `mqtt.topics`          | object            |               | controls mqtt topics
|                   | `mqtt.auth`            | object            | null          | controls mqtt auth

### MQTT.TOPICS Properties

Setup mqtt topics

|Req                | Property               | Type             | Default       | Description
|---                | ---                    | ---              |---            |---
| :red_circle:      | `topics.readPower`     | string           |               | MQTT-Topic to read current power draw
|                   | `topics.WriteLimit`    | string           |               | MQTT-Topic to write power limit to
|                   | `topics.status`        | string           |               | MQTT-Topic to listens for status updates

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
    "target": 0,
    "minPower": 0,
    "maxPower": 1200,
    "type": "relative",
    "throttle": 5,
    "hysteresis": 10.0,
    "retransmit": 60
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
| :red_circle:      | `command.type`         | string: "absolute" or "realtive"|| controls wether the command is absolute in watts (W) or in relative percent of `command.maxPower`
| :red_circle:      | `command.throttle`     | int              | Seconds (s)   | time that must pass between new limit commands. Use `0` to disable
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
    "smoothingSampleSize": 5
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
