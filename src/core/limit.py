import logging
import statistics
import core.appconfig as appconfig
import config.customize as customize
from typing import Deque, Callable
from collections import deque
from datetime import datetime


class LimitCalculator:
    def __init__(self, config: appconfig.AppConfig) -> None:
        self.config: appconfig.AppConfig = config
        self.last_command_time: datetime = datetime.min
        self.last_command_value: float = config.command.min_power
        self.last_command_has: bool = False
        self.command_max: float = config.command.max_power
        self.command_min: float = config.command.min_power

        deqSize: int = self.config.reading.smoothingSampleSize if self.config.reading.smoothingSampleSize > 0 else 1

        sampleFunc: Callable[[float], float]
        if self.config.reading.smoothing == appconfig.PowerReadingSmoothingType.AVG:
            sampleFunc = self.__get_smoothing_avg
        else:
            sampleFunc = self.__get_smoothing_none
            deqSize = 1

        if self.config.reading.offset != 0:
            self.__sampleReading = lambda x: sampleFunc(self.config.reading.offset + x)
        else:
            self.__sampleReading = sampleFunc

        self.__samples: Deque[float] = deque([], maxlen=deqSize)

    def add_reading(self, reading: float) -> float | None:
        sample = self.__sampleReading(reading)
        self.__log_reading(reading, sample)

        if not self.last_command_has:
            logging.debug(f"First reading. Calibrate...")
            self.last_command_value = self.__get_calibration()
            self.last_command_has = True
            logging.info(f"Calibration value is: {self.last_command_value}")

            if self.config.command.type == appconfig.InverterCommandType.RELATIVE:
                return self.__convert_to_relative_command(self.last_command_value)
            else:
                return self.last_command_value

        elapsed = round((datetime.now() - self.last_command_time).total_seconds(), 2)
        logging.debug(f"Elapsed since last command: {elapsed}")

        if elapsed < self.config.command.throttle:
            logging.debug("Throttle kicked in")
            return None

        overshoot = self.__convert_reading_to_relative_overshoot(sample)
        limit = self.__convert_overshot_to_limit(overshoot)
        self.__log_overshoot(overshoot, limit)

        if limit is None:
            return None

        if self.config.command.retransmit > 0 and elapsed >= self.config.command.retransmit:
            logging.debug("Forced retransmit kicked in. Ignoring mindiff")
        else:
            if not self.__limit_is_min_diff(limit):
                logging.debug("Limit is not over min diff")
                return None

        command: float
        if self.config.command.type == appconfig.InverterCommandType.RELATIVE:
            command = self.__convert_to_relative_command(limit)
        else:
            command = limit

        logging.debug(f"Command is: {command}")
        self.last_command_time = datetime.now()
        self.last_command_value = limit

        return command

    def get_limit_command_min(self):
        if self.config.command.type == appconfig.InverterCommandType.RELATIVE:
            return self.__convert_to_relative_command(self.command_min)
        else:
            return self.command_min

    def get_limit_command_max(self):
        if self.config.command.type == appconfig.InverterCommandType.RELATIVE:
            return self.__convert_to_relative_command(self.command_max)
        else:
            return self.command_max

    def reset(self) -> None:     
        self.__samples.clear()
        self.last_command_time: datetime = datetime.min
        self.last_command_value: float = float(0)
        self.last_command_has: bool = False
        logging.debug("Limit context was reseted")

    def __get_calibration(self) -> float:
        try:
            val = customize.calibrate(self.config.customize.calibration)
            if val is not None:
                if val >= self.command_min and val <= self.command_max:
                    return val
                else:
                    logging.warning(f"customize.calibrate returned invalid value: {val}")
        except Exception as ex:
            logging.warning(f"customize.calibrate threw exception: {ex}")

        return float(self.command_max)

    def __get_smoothing_avg(self, reading: float) -> float:
        self.__samples.append(reading)
        return statistics.mean(self.__samples)

    def __get_smoothing_none(self, reading: float) -> float:
        self.__samples.append(reading)
        return self.__samples[0]

    def __convert_reading_to_relative_overshoot(self, reading: float) -> float:
        return (self.config.command.target - reading) * -1

    def __convert_overshot_to_limit(self, overshoot: float) -> float | None:
        if overshoot == 0:
            return None
        else:
            return self.__cap_command(self.last_command_value + overshoot)

    def __limit_is_min_diff(self, limit: float) -> bool:
        if self.config.command.min_diff == 0:
            return True
        return abs(self.last_command_value - limit) >= self.config.command.min_diff

    def __convert_to_relative_command(self, limit: float) -> float:
        return (limit / self.command_max) * 100

    def __cap_command(self, limit: float) -> float:
        return max(self.command_min, min(self.command_max, limit))

    @staticmethod
    def __log_reading(reading: float, sample: float):
        logging.debug(f"Reading: {reading:>8.2f} | Sample: {sample:>6.2f}")

    @staticmethod
    def __log_overshoot(overshoot: float, limit: float | None):
        logging.debug(f"Overshoot: {overshoot:>6.2f} | Limit: {limit:>7.2f}")
