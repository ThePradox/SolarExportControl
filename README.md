# SolarExportControl

## Disclaimer: Looking for testers and feedback

This application was tested multiple days on my setup. Further tests on other setups are necessary!

## Demo

An ongoing graph/config screenshot collection can be found [here](docs/Demo.md)

## Background

Take mqtt data about your electric power consumption (from a digital electric meter for example) compare it to a target max power export and if necessary set max power of an solar inverter via mqtt.

## Original setup

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

## How does it work?

To put it simply:

If your power consumption is greater than `powerReadingTarget`, decrease the limit on your inverter.

If your power consumption is smaller than `powerReadingTarget`, increase the limit on your inverter.

## Requirements

- MQTT Broker
- A power reading sensor:
  - Publishes to MQTT Broker
  - The published value must include the inverter power
  - The published value must be negative if power is exported (inverter production greater than consumption)
  - Should publish at least every 10 seconds

- An inverter which can regulate its power production
  - Receive its power limit from the MQTT Broker
  - Power limit can be watts or percentage

- Python3

## How to install

1. Fullfill [Requirements](#requirements)
2. Clone or download Repo
3. Install requirements `$ pip install -r requirements.txt`
4. Modify [config](/src/config/config.json) to your liking
5. Modify [customize](/src/config/customize.py) to match your devices
6. [Run](#how-to-run)

## Config

See [Docs](/docs/Config.md)

## Customize

You **must** edit the `.\src\config\customize.py` to match your devices:

See [Docs](/docs/Customize.md)

## How to run

- Run with `python .\src\main.py .\src\config\config.json --verbose`
- Run with VSCode ("launch.json" should be included)

## Suggestions

For `inverterCommandMinDiff` I would suggest about 1-3% of your `inverterMaxPower`

If your power reading interval is less than or around 5 seconds:

- `inverterCommandThrottle: 5`
- `powerReadingSmoothing: "avg"`
- `powerReadingSmoothingSampleSize:5`

If your power reading interval is slower you are free to turn especially `inverterCommandThrottle` to `0`.

If your power reading interval is very slow (1 minute or greater) you should also turn `powerReadingSmoothing` to `none`

However this basically will change the inverter power limit every interval since every power reading is different unless every device in your household consumes a absolute fixed amount of power.

## TODO

- [ ] Test extensively
- [x] Refactoring necessary for better docker support
- [x] Create dockerfile
- [ ] Feature idea: Stop processing during night
