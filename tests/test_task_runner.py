from __future__ import annotations

from PySide6.QtCore import QEventLoop, QTimer

from desktop_app.services.task_runner import TaskRunner


def test_task_runner_executes_successful_task(qapp) -> None:
    runner = TaskRunner()
    loop = QEventLoop()
    results: list[object] = []

    def on_finished(task_id: str, result: object) -> None:
        results.append((task_id, result))
        loop.quit()

    runner.signals.finished.connect(on_finished)
    task_id = runner.run(lambda: "ok", task_id="test-task")
    QTimer.singleShot(3000, loop.quit)
    loop.exec()
    runner.shutdown()

    assert task_id == "test-task"
    assert results == [("test-task", "ok")]


def test_task_runner_emits_failure(qapp) -> None:
    runner = TaskRunner()
    loop = QEventLoop()
    failures: list[object] = []

    def fail() -> str:
        raise RuntimeError("boom")

    def on_failed(task_id: str, error: object) -> None:
        failures.append((task_id, str(error)))
        loop.quit()

    runner.signals.failed.connect(on_failed)
    task_id = runner.run(fail, task_id="failing-task")
    QTimer.singleShot(3000, loop.quit)
    loop.exec()
    runner.shutdown()

    assert task_id == "failing-task"
    assert failures == [("failing-task", "boom")]

