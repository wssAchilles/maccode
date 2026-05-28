from __future__ import annotations

from application.services.runtime_state import DemoRuntime, ProcessingTask


class ProcessVideoUseCase:
    def __init__(self, runtime: DemoRuntime) -> None:
        self.runtime = runtime

    def start(self, source: str) -> ProcessingTask:
        return self.runtime.start_task(source)

    def stop(self, task_id: str) -> ProcessingTask | None:
        return self.runtime.stop_task(task_id)

    def get_status(self, task_id: str) -> ProcessingTask | None:
        return self.runtime.get_task(task_id)
