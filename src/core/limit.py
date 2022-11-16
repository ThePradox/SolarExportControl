import logging
import statistics
import core.appconfig as appconfig
import config.customize as customize
from typing import Deque, Callable
from collections import deque
from datetime import datetime


# target: configured power target (config.command.target)
# reading: parsed value from mqtt read power topic
# sample: reading with applied smoothing if turned on
# overshoot: absolute difference between target and sample
# limit: overshoot + previous limit, capped to command_min and command_max
# command: value of limit in watts or percent, decided by config.command.type

class LimitCalculatorResult:
    def __init__(self, reading: float, sample: float) -> None:
        self.reading: float = reading
        self.sample: float = sample
        self.overshoot: float | None = None
        self.limit: float | None = None
        self.command: float | None = None
        self.is_calibration: bool = False
        self.is_throttled: bool = False
        self.is_not_over_min_diff: bool = False
        self.is_retransmit: bool = False


class LimitCalculator:
    def __init__(self, config: appconfig.AppConfig) -> None:
        self.config: appconfig.AppConfig = config
        self.last_limit_time: datetime = datetime.min
        self.last_limit_value: float = config.command.min_power
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

    def add_reading(self, reading: float) -> LimitCalculatorResult:
        r = self.__add_reading(reading)
        self.__log_result(r)
        return r

    def __add_reading(self, reading: float) -> LimitCalculatorResult:
        sample = self.__sampleReading(reading)
        result = LimitCalculatorResult(reading, sample)

        if not self.last_command_has:
            logging.debug(f"First reading. Calibrate...")
            self.last_limit_value = self.__get_calibration()
            self.last_command_has = True
            result.is_calibration = True
            logging.info(f"Calibration value is: {self.last_limit_value}")

            if self.config.command.type == appconfig.InverterCommandType.RELATIVE:
                result.limit = self.__convert_to_relative_command(self.last_limit_value)
            else:
                result.limit = self.last_limit_value
            return result

        elapsed = round((datetime.now() - self.last_limit_time).total_seconds(), 2)
        logging.debug(f"Elapsed since last command: {elapsed}")

        if elapsed < self.config.command.throttle:
            logging.debug("Throttle kicked in")
            result.is_throttled = True
            return result

        overshoot = self.__convert_reading_to_relative_overshoot(sample)
        result.overshoot = overshoot
        limit = self.__convert_overshot_to_limit(overshoot)

        if limit is None:
            return result

        if self.config.command.retransmit > 0 and elapsed >= self.config.command.retransmit:
            logging.debug("Forced retransmit kicked in. Ignoring mindiff")
            result.is_retransmit = True
        else:
            if not self.__limit_is_min_diff(limit):
                logging.debug("Limit is not over min diff")
                result.is_not_over_min_diff = True
                return result
    
        result.limit = limit
        command: float

        if self.config.command.type == appconfig.InverterCommandType.RELATIVE:
            command = self.__convert_to_relative_command(limit)
        else:
            command = limit

        result.command = command
        self.last_limit_time = datetime.now()
        self.last_limit_value = limit

        return result

    def get_command_min(self):
        if self.config.command.type == appconfig.InverterCommandType.RELATIVE:
            return self.__convert_to_relative_command(self.command_min)
        else:
            return self.command_min

    def get_command_max(self):
        if self.config.command.type == appconfig.InverterCommandType.RELATIVE:
            return self.__convert_to_relative_command(self.command_max)
        else:
            return self.command_max

    def reset(self) -> None:
        self.__samples.clear()
        self.last_limit_time: datetime = datetime.min
        self.last_limit_value: float = float(0)
        self.last_command_has: bool = False
        logging.debug("Limit context was reseted")

    def __get_calibration(self) -> float:
        try:
            val = customize.calibrate(self.config.customize.calibration)
            if val is not None:
                return self.__cap_limit(val)
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
            return self.__cap_limit(self.last_limit_value + overshoot)

    def __limit_is_min_diff(self, limit: float) -> bool:
        if self.config.command.min_diff == 0:
            return True
        return abs(self.last_limit_value - limit) >= self.config.command.min_diff

    def __convert_to_relative_command(self, limit: float) -> float:
        return (limit / self.command_max) * 100

    def __cap_limit(self, limit: float) -> float:
        return max(self.command_min, min(self.command_max, limit))

    @staticmethod
    def __log_result(result: LimitCalculatorResult):
        if logging.root.level is not logging.DEBUG:
            return

        seg = []
        seg.append(f"Reading: {result.reading:>8.2f}")
        seg.append(f"Sample: {result.sample:>6.2f}")

        if result.overshoot is not None:
            seg.append(f"Overshoot: {result.overshoot:>6.2f}")

        if result.limit is not None:
            seg.append(f"Limit: {result.limit:>7.2f}")

        if result.command is not None:
            seg.append(f"Limit: {result.command:>7.2f}")

        seg.append(f"Cal: {int(result.is_calibration)}")
        seg.append(f"Thr: {int(result.is_throttled)}")
        seg.append(f"Min: {int(result.is_not_over_min_diff)}")
        seg.append(f"Ret: {int(result.is_retransmit)}")
       
        logging.debug(" | ".join(seg))
