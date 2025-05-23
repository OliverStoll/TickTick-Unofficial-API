import requests
from pydantic import BaseModel

from ticktick_v2.cookies_login import get_authenticated_ticktick_headers
from ticktick_v2.utils.logger import create_logger


class TickTickTask(BaseModel):
    id: str
    projectId: str
    title: str
    status: int
    priority: int
    deleted: int
    createdTime: str
    creator: int
    items: list
    columnId: str | None = None
    isAllDay: bool | None = None
    startDate: str | None = None
    dueDate: str | None = None
    content: str | None = None

    class Config:
        extra = "allow"



class TicktickTaskHandler:
    log = create_logger("TickTick Task Handler")
    url_get_tasks = 'https://api.ticktick.com/api/v2/batch/check/0'

    def __init__(self):
        self.headers = get_authenticated_ticktick_headers()

    def get_all_tasks(self) -> list[TickTickTask] | None:
        """
        Get all TickTick tasks

        Returns:
            List of TickTickTask pydantic BaseModel objects. Objects can be converted via .dict()
        """
        response = requests.get(url=self.url_get_tasks, headers=self.headers).json()
        tasks_data = response.get('syncTaskBean', {}).get('update', None)
        if tasks_data is None:
            self.log.error("Getting Tasks failed")
            return None

        tasks = [TickTickTask(**task_data) for task_data in tasks_data]

        return tasks


if __name__ == '__main__':
    tasks = TicktickTaskHandler().get_all_tasks()
    print(tasks)