# Config

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
| :red_circle: | `topicWriteLimit` | MQTT-Topic to write power limit to | string
|| `auth.username` | set a username for broker authentication | string
|| `auth.password` | set optionally a password for broker authentication | string
|| `lastWill.topic` | TQTT-Topic that the will message should be published on | string
|| `lastWill.payload` | the message to send as a will. If not given a zero length message will be used as the will | string
|| `lastWill.retain` | set the will to be retained (true) or not (false) | bool | false
| :red_circle: | `inverterCommandThrottle` | time in seconds that must pass between new limit commands. Use to prevent multiple commands in a row during a longer power curve. Use `0` to disable | int |
| :red_circle: | `inverterCommandType` | - `absolute`: publish limit in watts <br/>- `relative`: publish limit in percent of `inverterMaxPower` | string:  "absolute" or "relative"
| :red_circle: | `inverterCommandMinDiff` | only publish new limit if the amount of watts difference between last limit command is greather than this value. Use `0.0` to disable | number |
| :red_circle: | `inverterCommandRetransmit` | time in seconds after which `inverterCommandMinDiff` is ignored to retransmit the command. Useful if commands can get 'lost' on the way to the inverter. Use `0` to disable |  int |
| :red_circle: | `inverterMaxPower` | max power of solar inverter | int |
| :red_circle: | `powerReadingTarget` | the power consumption this app will use as target. Typical values are `0` (Zero Export) or `-600` (in Germany "Balkonkraftwerk") | int
| :red_circle: | `powerReadingSmoothing` | - `none`: The original power reading will be used<br/>- `avg`: The average over `powerReadingSmoothingSampleSize` is used<br />Use `avg` to filter very short power spikes
| :red_circle: | `powerReadingSmoothingSampleSize` | amount of samples to use for `powerReadingSmoothing` when not `none`.<br/> `1` is the same as `powerReadingSmoothing=none`
|| `status.topic` | MQTT-Topic to read status from. Setting a topic enables the status function | string | null
|| `calibration` | Config oject which is passed to `customize.calibrate` | object |
