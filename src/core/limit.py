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
    def __init__(self, reading: float, sample: float, overshoot: float, limit: float, command: float | None,
                 is_calibration: bool, is_throttled: bool, is_not_over_min_diff: bool, is_retransmit: bool, elapsed: float) -> None:
        self.reading: float = reading
        self.sample: float = sample
        self.overshoot: float = overshoot
        self.limit: float = limit
        self.command: float | None = command
        self.is_calibration: bool = is_calibration
        self.is_throttled: bool = is_throttled
        self.is_not_over_min_diff: bool = is_not_over_min_diff
        self.is_retransmit: bool = is_retransmit
        self.elapsed: float = elapsed


class LimitCalculator:
    def __init__(self, config: appconfig.AppConfig) -> None:
        self.config: appconfig.AppConfig = config
        self.last_command_time: datetime = datetime.min
        self.last_limit_value: float = config.command.min_power
        self.last_limit_has: bool = False
        self.limit_max: float = config.command.max_power
        self.limit_min: float = config.command.min_power

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
        is_calibration = False
        is_throttled = False
        is_not_over_min_diff = False
        is_retransmit = False

        sample = self.__sampleReading(reading)
        
        if not self.last_limit_has:
            logging.debug(f"First reading. Calibrate...")
            self.last_limit_value = self.__get_calibration()
            self.last_limit_has = True
            is_calibration = True
            logging.debug(f"Calibration value is: {self.last_limit_value}")

        elapsed = round((datetime.now() - self.last_command_time).total_seconds(), 2)
        overshoot = self.__convert_reading_to_relative_overshoot(sample)
        limit = self.__convert_overshot_to_limit(overshoot)

        # Ignore conditions on calibration
        if not is_calibration:

            # Check if command must be throttled
            if elapsed < self.config.command.throttle:
                is_throttled = True

            # Ignore mindiff when retransmit > elapsed
            elif self.config.command.retransmit > 0 and elapsed >= self.config.command.retransmit:
                is_retransmit = True

            # Check for mindiff
            elif not self.__limit_is_min_diff(limit):
                is_not_over_min_diff = True

        command: float | None = None

        if not (is_throttled or is_not_over_min_diff):
            command = self.__convert_to_command(limit)
            self.last_command_time = datetime.now()
            self.last_limit_value = limit

        return LimitCalculatorResult(reading=reading,
                                     sample=sample,
                                     overshoot=overshoot,
                                     limit=limit,
                                     command=command,
                                     is_calibration=is_calibration,
                                     is_throttled=is_throttled,
                                     is_not_over_min_diff=is_not_over_min_diff,
                                     is_retransmit=is_retransmit,
                                     elapsed=elapsed)

    def get_command_min(self) -> float:
        return self.__convert_to_command(self.limit_min)

    def get_command_max(self) -> float:
        return self.__convert_to_command(self.limit_max)

    def reset(self) -> None:
        self.__samples.clear()
        self.last_command_time: datetime = datetime.min
        self.last_limit_value: float = float(0)
        self.last_limit_has: bool = False
        logging.debug("Limit context was reseted")

    def __get_calibration(self) -> float:
        try:
            val = customize.calibrate(self.config.customize.calibration)
            if val is not None:
                return self.__cap_limit(val)
        except Exception as ex:
            logging.warning(f"customize.calibrate threw exception: {ex}")

        return float(self.limit_max)

    def __get_smoothing_avg(self, reading: float) -> float:
        self.__samples.append(reading)
        return statistics.mean(self.__samples)

    def __get_smoothing_none(self, reading: float) -> float:
        self.__samples.append(reading)
        return self.__samples[0]

    def __convert_reading_to_relative_overshoot(self, reading: float) -> float:
        return (self.config.command.target - reading) * -1

    def __convert_overshot_to_limit(self, overshoot: float) -> float:
        return self.__cap_limit(self.last_limit_value + overshoot)

    def __limit_is_min_diff(self, limit: float) -> bool:
        if self.config.command.min_diff == 0:
            return True
        return abs(self.last_limit_value - limit) >= self.config.command.min_diff

    def __convert_to_command(self, limit: float) -> float:
        if self.config.command.type == appconfig.InverterCommandType.RELATIVE:
            return (limit / self.limit_max) * 100
        else:
            return limit

    def __cap_limit(self, limit: float) -> float:
        return max(self.limit_min, min(self.limit_max, limit))

    @staticmethod
    def __log_result(result: LimitCalculatorResult) -> None:
        if logging.root.level is not logging.DEBUG:
            return

        seg = []
        seg.append(f"Reading: {result.reading:>8.2f}")
        seg.append(f"Sample: {result.sample:>6.2f}")
        seg.append(f"Overshoot: {result.overshoot:>6.2f}")
        seg.append(f"Limit: {result.limit:>7.2f}")

        if result.command is not None:
            seg.append(f"Command: {result.command:>7.2f}")
        else:
            seg.append(f"Command:    None")

        seg.append(f"Cal: {int(result.is_calibration)}")
        seg.append(f"Thr: {int(result.is_throttled)}")
        seg.append(f"Min: {int(result.is_not_over_min_diff)}")
        seg.append(f"Ret: {int(result.is_retransmit)}")
        seg.append(f"Elapsed: {result.elapsed:.2f}")

        logging.debug(" | ".join(seg))
