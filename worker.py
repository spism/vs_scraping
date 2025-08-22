# worker.py
import os
import time
import signal
import logging
from contextlib import contextmanager
from jobs import run_scrape_job, maybe_upload

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("worker")

INTERVAL_SECONDS = int(os.getenv("SCRAPE_INTERVAL_SECONDS", "600"))  # default 15min
RUN_AT_START = os.getenv("RUN_AT_START", "true").lower() == "true"
ALLOW_OVERLAP = os.getenv("ALLOW_OVERLAP", "false").lower() == "true"

STOP = False

def handle_stop(signum, frame):
    global STOP
    logger.info("Received signal %s; shutting down gracefully...", signum)
    STOP = True

signal.signal(signal.SIGINT, handle_stop)
signal.signal(signal.SIGTERM, handle_stop)

@contextmanager
def non_overlapping(lock_path=".scrape.lock"):
    """
    Prevent overlapping runs by creating a lock file.
    Set ALLOW_OVERLAP=true to bypass.
    """
    if ALLOW_OVERLAP:
        yield
        return

    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    except FileExistsError:
        logger.warning("Previous run still in progress (lock %s). Skipping this tick.", lock_path)
    finally:
        try:
            if os.path.exists(lock_path):
                os.remove(lock_path)
        except Exception:
            pass

def tick():
    logger.info("Starting scrape tick...")
    all_articles = run_scrape_job()
    maybe_upload(all_articles)
    logger.info("Tick finished: %d feeds.", len(all_articles))

def main():
    if RUN_AT_START:
        with non_overlapping():
            tick()

    while not STOP:
        slept = 0
        # interruptible sleep
        while slept < INTERVAL_SECONDS and not STOP:
            time.sleep(1)
            slept += 1
        if STOP:
            break
        with non_overlapping():
            tick()

    logger.info("Worker exited cleanly.")

if __name__ == "__main__":
    main()
