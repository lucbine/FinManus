import asyncio
import uuid
from datetime import datetime
from typing import Dict

from app.agent.manus import Manus
from app.apis.models.task import Task

# 任务管理器
class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}    # 任务列表
        self.queues: Dict[str, asyncio.Queue] = {}  # 任务队列

    # 创建任务
    def create_task(self, task_id: str, agent: Manus) -> Task:
        task = Task(
            id=task_id,
            created_at=datetime.now(),
            agent=agent,
        )
        self.tasks[task_id] = task
        self.queues[task_id] = asyncio.Queue()  # 创建任务队列
        return task

    # 更新任务进度
    async def update_task_progress(
        self, task_id: str, event_name: str, step: int, **kwargs
    ):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            # Use the same step value for both progress and message
            await self.queues[task_id].put(
                {
                    "type": "progress",
                    "event_name": event_name,
                    "step": step,
                    "content": kwargs,
                }
            )

    # 终止任务
    async def terminate_task(self, task_id: str):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            await task.agent.terminate()
            await self.remove_task(task_id)

    async def remove_task(self, task_id: str):
        if task_id in self.tasks:
            del self.tasks[task_id]
            del self.queues[task_id]


task_manager = TaskManager()
