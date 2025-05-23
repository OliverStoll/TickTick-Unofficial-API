import os
import requests
from datetime import datetime
import pytz
from pydantic import BaseModel, field_validator, model_validator

from ticktick_v2.utils.logger import create_logger
from ticktick_v2.cookies_login import get_authenticated_ticktick_headers
from ticktick_v2.utils.time_utils import get_timestamp_from_offset


class TickTickFocusTime(BaseModel):
    id: str
    startTime: str | datetime
    endTime: str | datetime
    status: int
    pauseDuration: int
    type: int
    totalDuration: int | None = None

    @field_validator("startTime", "endTime", mode="before")  # noqa
    @classmethod
    def _parse_datetime(cls, value):
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return value

    @model_validator(mode="after")
    def _set_timezone_and_duration(self):
        tz_name = os.getenv("LOCAL_TIMEZONE", "Europe/Berlin")
        tz = pytz.timezone(tz_name)
        self.startTime = self.startTime.astimezone(tz)
        self.endTime = self.endTime.astimezone(tz)
        self.totalDuration = int((self.endTime - self.startTime).total_seconds() / 60)
        return self


class TicktickFocusHandler:
    log = create_logger('TickTick Focus Handler')

    def __init__(self, always_raise_exceptions: bool = False):
        self.headers = get_authenticated_ticktick_headers()
        self.raise_exceptions = always_raise_exceptions

    def get_all_focus_times(
            self,
            to_timestamp: int | None = None,
            days_offset: int | None = None
    ) -> list[TickTickFocusTime] | None:
        if days_offset:
            to_timestamp = get_timestamp_from_offset(days_offset=days_offset)

        timestamp_query_param = f"?to={to_timestamp}" if to_timestamp else ''
        url = f"https://api.ticktick.com/api/v2/pomodoros/timeline{timestamp_query_param}"
        response = requests.get(url, headers=self.headers).json()
        if not isinstance(response, list):
            error_msg = f'No or malformed response to get_all_focus_times: {response}'
            self.log.error(error_msg)
            if self.raise_exceptions:
                raise ValueError(error_msg)
            return None

        focus_times = [TickTickFocusTime(**focus_time_data) for focus_time_data in response]
        return focus_times



if __name__ == '__main__':
    handlers = TicktickFocusHandler()
    focus_times_ = handlers.get_all_focus_times()
    print(focus_times_)