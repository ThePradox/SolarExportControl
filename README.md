# SolarExportControl
## Background
The goal is to take mqtt data about your electric power consumption (from a digital electric meter for example) compare it to a target max power export and if necessary set max power of an solar inverter via mqtt.

Original setup:
- Power reading via esp32 with tasmota and a 'hichi' IR sensor into mqtt broker
- Limiting power of inverter via esp32 with opendtu receiving the limit over mqtt
