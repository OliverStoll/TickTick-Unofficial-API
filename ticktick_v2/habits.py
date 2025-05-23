import requests
from datetime import datetime, timedelta
from typing import Literal
from pydantic import BaseModel

from ticktick_v2.utils.logger import create_logger
from ticktick_v2.utils.time_utils import get_datetime_now_utc_millisecond
from ticktick_v2.cookies_login import get_authenticated_ticktick_headers
from ticktick_v2.web.api_request import post_request


# TODO: dataclass for habit metadata


class TickTickHabitEntry(BaseModel):
    habitId: str
    checkinStamp: int
    goal: float | int
    value: float | int
    status: Literal[0, 1, 2]
    id: str | None
    checkinTime: str | None = None
    opTime: str | None = None

    class Config:
        extra = "allow"

    @classmethod
    def init(
            cls,
            habit_id: str,
            date_stamp: int,
            habit_goal: int,
            status: Literal[0, 1, 2] | None = None,
            value: int | float | None = None,
    ) -> "TickTickHabitEntry":

        assert not (status and value), "You can only provide status or value, not both"
        assert status is not None or value is not None, "You need to provide either status or value"

        if value is None:
            value = habit_goal if status == 2 else 0
        if status is None:
            status = 2 if value >= habit_goal else 0

        now = get_datetime_now_utc_millisecond()
        return cls(
            checkinStamp=date_stamp,
            checkinTime=now,
            goal=habit_goal,
            habitId=habit_id,
            opTime=now,
            status=status,
            value=value,
        )




class TicktickHabitHandler:
    """Class that accesses the TickTick habits API. Used to post habit checkins.

    Definitions:
    - Habit: A habit is a task that can be checked in multiple times a day, with a goal value.
             Habits have a unique name and id, stored in their metadata.
    - Checkin: A checkin is a single entry of a habit, with a status and a value.
    """

    status_codes = {0: "Not completed", 1: "Failed", 2: "Completed"}
    url_habits = "https://api.ticktick.com/api/v2/habits"
    url_batch_checkin = "https://api.ticktick.com/api/v2/habitCheckins/batch"
    url_query_checkin = "https://api.ticktick.com/api/v2/habitCheckins/query"


    def __init__(self, always_raise_exceptions: bool = False):
        self.log = create_logger("Ticktick Habits")
        self.headers = get_authenticated_ticktick_headers()
        self.habits, self.habit_ids = self._get_all_habits_metadata()
        self.raise_exceptions = always_raise_exceptions

    def _get_all_habits_metadata(self) -> tuple[dict, dict]:
        """Get the metadata of all habits and their ids"""

        habit_data = requests.get(url=self.url_habits, headers=self.headers).json()
        if "errorId" in habit_data:
            error_message = f"Error loading habits: {habit_data}"
            self.log.error(error_message)
            raise ValueError(error_message)

        habits_metadata = {habit["id"]: habit for habit in habit_data if 'id' in habit}
        habit_name_to_id_mapping = {habit["name"]: habit["id"] for habit in habit_data}
        return habits_metadata, habit_name_to_id_mapping

    def _post_habit_metadata(self, habit_id):
        # todo: update a single habit metadata, to update checkins quickly
        raise NotImplementedError

    def _init_habit_entry(
            self,
            habit_name: str,
            date_stamp: int,
            status: int | None = None,
            value: int | None = None,
    ) -> TickTickHabitEntry:
        """Collect all data needed for a single habit checkin."""

        habit_id = self.habit_ids[habit_name]
        habit_goal = int(self.habits[habit_id]["goal"])
        return TickTickHabitEntry.init(
            habit_id=habit_id,
            date_stamp=date_stamp,
            status=status,
            value=value,
            habit_goal=habit_goal,
        )

    def post_checkin(
            self,
            habit_name: str,
            date_stamp: int,
            status: int | None = None,
            value: int | None = None,
            raise_exception: bool = False,
         ) -> None:
        """Post a single habit checkin to the TickTick API.

        Args:
            habit_name: Name of the habit to check-in
            date_stamp: Date of the check-in, in the format YYYYMMDD
            status: Status of the check-in. 0: Not completed, 1: Failed, 2: Completed
            value: The value amount to check in. for habits who require multiple units
            raise_exception: Flag to raise exception in case of an error
        """

        checkin_entry = self._init_habit_entry(habit_name, date_stamp, status, value)
        self.log.info(f"Checking {habit_name} on {date_stamp} as {status}: {value}/{checkin_entry.goal}")

        # create payload depending on if a checkin for that day already exists
        existing_checkin_entry = self.get_checkin(checkin_entry.habitId, date_stamp)
        payload: dict[str, list[dict[str, str | int]]] = {"add": [], "update": [], "delete": []}

        if existing_checkin_entry:
            checkin_entry.id = existing_checkin_entry.id
            payload["update"].append(checkin_entry.model_dump())
        else:
            payload["add"].append(checkin_entry.model_dump())

        response = post_request(url="batch_checkin", payload=payload, headers=self.headers)
        if response:
            self.log.info(f"Checkin for {habit_name} successful with response: {response}")
        elif raise_exception or self.raise_exceptions:
            raise ValueError(f"Error posting Habit Checkin: {response}")

    def get_checkin(
            self,
            habit_id: str,
            date_stamp: int,
            raise_exception: bool = False,
    ) -> TickTickHabitEntry | None:
        """Retrieve a single checkin entry for a habit on a specific date, or None if not found"""

        date = datetime.strptime(str(date_stamp), "%Y%m%d")
        after_stamp = (date - timedelta(days=1)).strftime("%Y%m%d")
        after_stamp = int(after_stamp)  # type: ignore
        payload = {"habitIds": [habit_id], "afterStamp": after_stamp}
        response = post_request(url=self.url_query_checkin, payload=payload, headers=self.headers)

        if response is None or response.get('checkins', None) is None:
            error_msg = f"No or malformed response from TickTick API for get_checkin: {response}"
            self.log.error(error_msg)
            if raise_exception or self.raise_exceptions:
                raise ValueError(error_msg)
            return None

        all_entries = response.get('checkins', {})
        habit_entries = all_entries.get(habit_id, [])
        for entry in habit_entries:
            if entry.get("checkinStamp", -1) == int(date_stamp):
                habit_entry = TickTickHabitEntry(**entry)
                return habit_entry

        return None

    def get_all_checkins(
            self,
            after_stamp: int = 19700101,
            habit_names: list[str] | str | None = None,
            raise_exception: bool = False
    ) -> dict[str, list[TickTickHabitEntry]] | None:
        """Get all checkins of all habits (or those provided), after a specific date stamp."""

        if not habit_names:
            habits_ids = list(self.habit_ids.values())
        else:
            habit_names = [habit_names] if isinstance(habit_names, str) else habit_names
            habits_ids = [self.habit_ids[habit] for habit in habit_names]

        payload = {"habitIds": habits_ids, "afterStamp": after_stamp}
        response = post_request(url=self.url_query_checkin, payload=payload, headers=self.headers)

        if response is None or response.get('checkins', None) is None:
            error_msg = f"No or malformed response from TickTick API for get_all_checkins: {response}"
            self.log.error(error_msg)
            if raise_exception:
                raise ValueError(error_msg)
            return None

        all_habits_entries = response.get("checkins", {})
        all_habits_entries_parsed = {}
        for habit_id, habits_entries in all_habits_entries.items():
            habit_name = self.habits[habit_id]["name"]
            habits_entries_objs = [TickTickHabitEntry(**entry, habitName=habit_name) for entry in habits_entries]
            all_habits_entries_parsed[habit_id] = habits_entries_objs

        return all_habits_entries_parsed


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    handlers = TicktickHabitHandler(always_raise_exceptions=True)
    single_checkin = handlers.get_checkin(habit_id='64f08ac16fc6ff16c2d1f3eb', date_stamp=20250520)
    checkins = handlers.get_all_checkins(after_stamp=20220101)
    print(checkins)