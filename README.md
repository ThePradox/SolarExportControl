# SolarExportControl

## Disclaimer: Looking for testers and feedback

This application was tested multiple days on my setup. Further tests on other setups are necessary!

## Description

This application takes your current electric power consumption (from a digital electric meter for example) and compares it to a defined target value.

If your consumption is greater than your target: Lower the limit of your solar inverter

If your consumption is lower than your target: Increase the limit on your solar inverter

## Original setup

- Power reading via esp32 with tasmota and a 'hichi' IR sensor into mqtt broker
- Limiting power of inverter with an esp32 running [OpenDTU](https://github.com/tbnobody/OpenDTU) and receiving the limit over mqtt

## Implemented Features

- Most MQTT settings exposed
- Configurable command behaviour:
  - Min limit
  - Relative (%) or absolute (W)
  - Throttle amount of commands
  - Minimum difference to last command
- Configurable power reading:
  - Offset
  - Smoothing: Average over X samples
- Configurable sleep mode. Turn off during night!
- Scriptable calibration
- Scriptable generic limit callback: Send your inverter limit anywhere!

## Demo

An ongoing graph/config screenshot collection can be found [here](docs/Demo.md)

## Requirements

- MQTT Broker
- A power reading sensor:
  - Publishes to MQTT Broker
  - The published value **must** include the inverter power
  - The published value **must** be negative if power is exported (inverter production greater than consumption)
  - Should publish at least every 10 seconds

- An inverter which can regulate its power production
  - Receive its power limit from the MQTT Broker
  - Power limit can be watts or percentage

- Python3 (min. 3.10)

## How to install

1. Fullfill [Requirements](#requirements)
2. Clone or download Repo
3. Install requirements `$ pip install -r requirements.txt`
4. Modify [config](/src/config/config.json) to your liking
5. Modify [customize](/src/config/customize.py) to match your devices
6. [Run](#how-to-run)

## Config

You **must** edit the `.\src\config\config.json` to match your environment:

See [Docs](/docs/Config.md)

## Customize

You **must** edit the `.\src\config\customize.py` to match your devices:

See [Docs](/docs/Customize.md)

## How to run

- Run normal: `python .\src\main.py .\src\config\config.json`
- Run with VSCode ("launch.json" should be included)

### Arguments

- Entrypoint: `/src/main.py`
- Required (positional) argument:
  - `(path to config.json)`: can be relative or absolute
- Optional arguments:
  - `--verbose` : detailed logging
  - `--mqttdiag`: additional mqtt diagnostics

## Docker support

See [Docs](/docs/Docker.md)

## Config suggestions

For `config.command.minDiff` I would suggest about 1-3% of your `command.maxPower`

If your power reading interval is less than or around 5 seconds:

- `config.command.throttle: 5`
- `config.reading.smoothing: "avg"`
- `config.reading.smoothingSampleSize:5`

If your power reading interval is slower you are free to turn especially `config.command.throttle` to `0`.

If your power reading interval is very slow (1 minute or greater) you should also turn `config.reading.smoothing` to `none`

However this basically will change the inverter power limit every interval since every power reading is different.
