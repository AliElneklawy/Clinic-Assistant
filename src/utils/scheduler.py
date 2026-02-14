import time
from threading import Thread

import schedule


class Scheduler:
    def __init__(self):
        self._thread = None
        self._running = False

    def start(self):
        if self._running:
            return

        schedule.every(1).minutes.do(self.run)
        self._thread = Thread(target=self._run_scheduler, daemon=False)
        self._running = True
        self._thread.start()

    def stop(self):
        if self._running:
            schedule.clear()
            self._running = False
            if self._thread is not None:
                self._thread.join(timeout=10)
                self._thread = None

    def _run_scheduler(self):
        while self._running:
            schedule.run_pending()
            time.sleep(1)

    def run(self):
        raise NotImplementedError("Subclasses must implement this method")
