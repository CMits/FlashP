"""A single-worker background queue.

FLASH-P runs must not overlap (two runs on the same network dir would collide),
so jobs are processed strictly one at a time on a daemon thread. The webhook
handler enqueues and returns immediately (within the Teams 5s window); the worker
runs the job and fires a completion callback that posts the result back.
"""
from __future__ import annotations

import queue
import threading
import traceback
from dataclasses import dataclass
from typing import Callable

from command_map import ParsedCommand


@dataclass
class Job:
    command: ParsedCommand
    requester: str            # display name, for the result message
    reply_to: str | None      # platform-specific return address (e.g. Power Automate URL)


class JobQueue:
    def __init__(self, worker: Callable[[Job], None]):
        self._q: "queue.Queue[Job]" = queue.Queue()
        self._worker = worker
        self._thread = threading.Thread(target=self._loop, name="flashp-bridge-worker", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def submit(self, job: Job) -> int:
        """Enqueue a job; return its position (0 = will run now, N = N ahead of it)."""
        ahead = self._q.qsize()
        self._q.put(job)
        return ahead

    def _loop(self) -> None:
        while True:
            job = self._q.get()
            try:
                self._worker(job)
            except Exception:  # never let one bad job kill the worker
                traceback.print_exc()
            finally:
                self._q.task_done()
