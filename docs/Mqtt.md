# MQTT TOPICS

> [prefix] is configured in [config](./Config.md#meta-properties)

## Telemetry Topics

| Path                     | Unit                            | Description
|---                       | ---                             | ---
| [prefix]/tele/power      | Watt (W)                        | raw power value as parsed from `config.mqtt.topics.readPower`
| [prefix]/tele/sample     | Watt (W)                        | power value after applying `config.reading.offset` and `config.reading.smoothing`
| [prefix]/tele/overshoot  | Watt (W)                        | difference between the last sample and `config.command.target`
| [prefix]/tele/limit      | Watt (W)                        | calculated inverter limit
| [prefix]/tele/command    | Watt (W) or Percent (%)         | last issued inverter limit command as published in `config.mqtt.topics.writeCommand`. Watt if `config.command.type` is `absolute`, percent if `relative`

## Status Topics

| Path                     | Unit             | Description
|---                       | ---              | ---
| [prefix]/status/inverter | bool (0 or 1)    | inverter status if configured with `config.mqtt.topics.inverterStatus`
| [prefix]/status/enabled  | bool (0 or 1)    | application enabled status
| [prefix]/status/active   | bool (0 or 1)    | application working status
| [prefix]/status/online   | bool (0 or 1)    | application connection status

## Command Topics

| Path                     | Unit             | Description
|---                       | ---              | ---
| [prefix]/cmd/enabled     | bool (0 or 1)    | start and stop the application
