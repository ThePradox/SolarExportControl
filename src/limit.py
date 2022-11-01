import logging
from typing import Deque
import config as conf
from collections import deque
import statistics
from datetime import datetime


class LimitCalculator:
    def __init__(self, config: conf.AppConfig) -> None:
        self.config: conf.AppConfig = config
        self.last_command_time: datetime = datetime.min
        self.last_command_value: float = float(0)
        self.last_command_has: bool = False
        self.command_max: float = float(config.inverter_max_power)
        self.command_min: float = 0.0

        deqSize: int = self.config.power_reading_smoothing_sample_size if self.config.power_reading_smoothing_sample_size > 0 else 1      

        if self.config.power_reading_smoothing == conf.PowerReadingSmoothingType.AVG:
            self.__sampleReading = self.__getSmoothingAvg
        else:
            self.__sampleReading = self.__getSmoothingNone
            deqSize = 1

        self.__samples: Deque[float] = deque([], maxlen=deqSize)

    def addReading(self, reading: float) -> float | None:
        logging.debug(f"New reading: {reading}")

        sample = self.__sampleReading(reading)       
        logging.debug(f"Sample is: {sample}")

        if self.last_command_has is not True:         
            self.last_command_value = float(self.command_max)
            self.last_command_has = True
            logging.debug(f"First reading. Using calibration value.")

            if self.config.inverter_command_type == conf.InverterCommandType.RELATIVE:
                return self.__convertToRelativeCommand(self.last_command_value)
            else:
                return self.last_command_value

        elapsed = (datetime.now() - self.last_command_time).total_seconds()
        logging.debug(f"Elapsed since last command: {elapsed}")

        if elapsed < self.config.inverter_command_throttle:
            logging.debug("Throttle kicked in")
            return None

        overshoot = self.__convertReadingToRelativeOvershoot(sample)
        logging.debug(f"Overshoot is: {overshoot}")

        limit = self.__convertOvershotToLimit(overshoot)
        logging.debug(f"Limit is: {limit}")

        if limit is None:
            return None

        if self.config.inverter_command_retransmit > 0 and elapsed >= self.config.inverter_command_retransmit:
            logging.debug("Forced retransmit kicked in. Ignoring mindiff")
        else:
            if self.__limitIsMinDiff(limit) is not True:
                logging.debug("Limit is not over min diff")
                return None

        command:float
        if self.config.inverter_command_type == conf.InverterCommandType.RELATIVE:
            command = self.__convertToRelativeCommand(limit)
        else:
            command = limit


        logging.debug(f"Command is: {command}")
        self.last_command_time = datetime.now()
        self.last_command_value = limit

        return command

    def reset(self) -> None:
        logging.debug("Reset has been called")
        self.__samples.clear()
        self.last_command_time: datetime = datetime.min
        self.last_command_value: float = float(0)
        self.last_command_has: bool = False

    def __getSmoothingAvg(self, reading: float) -> float:
        self.__samples.append(reading)
        return statistics.mean(self.__samples)

    def __getSmoothingNone(self, reading:float) -> float:
        self.__samples.append(reading)
        return self.__samples[0]

    def __convertReadingToRelativeOvershoot(self, reading: float) -> float:
        return (self.config.power_reading_target - reading) * -1

    def __convertOvershotToLimit(self, overshoot: float) -> float | None:
        if overshoot == 0:
            return None
        else:
            return max(0, min(self.command_max, (self.last_command_value + overshoot)))

    def __limitIsMinDiff(self, limit: float) -> bool:
        if self.config.inverter_command_min_diff == 0:
            return True
        return abs(self.last_command_value - limit) >= self.config.inverter_command_min_diff

    def __convertToRelativeCommand(self, limit: float) -> float:
        if limit == 0:
            return 0
        return (limit / self.command_max) * 100
