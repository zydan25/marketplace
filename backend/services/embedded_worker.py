import logging
import os
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from django.db import close_old_connections

logger = logging.getLogger(__name__)

_START_LOCK = threading.Lock()
_STARTED = False
_STOP = threading.Event()
_THREAD = None


def _enabled():
    value = os.getenv("SERVICES_EMBEDDED_WORKER", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def _allowed_process():
    argv = {str(x).lower() for x in sys.argv}
    blocked = {
        "test", "pytest", "makemigrations", "migrate", "check", "collectstatic",
        "shell", "shell_plus", "dbshell", "showmigrations", "sqlmigrate",
        "createsuperuser", "process_service_tasks",
    }
    if argv & blocked:
        return False
    if "runserver" in argv and os.getenv("RUN_MAIN") != "true":
        return False
    if os.getenv("PYTEST_CURRENT_TEST"):
        return False
    return True


@contextmanager
def _process_lock():
    """A host-level singleton lock shared by all Gunicorn workers."""
    import fcntl

    path = Path(os.getenv("SERVICES_WORKER_LOCK_PATH", "/tmp/shabik-services-worker.lock"))
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+")
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        yield True
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def _loop():
    from .executor import process_task

    idle_sleep = max(0.25, float(os.getenv("SERVICES_WORKER_IDLE_SLEEP", "1")))
    error_sleep = max(1.0, float(os.getenv("SERVICES_WORKER_ERROR_SLEEP", "2")))
    logger.info("Embedded services worker started")
    while not _STOP.is_set():
        try:
            close_old_connections()
            with _process_lock() as leader:
                if not leader:
                    _STOP.wait(idle_sleep)
                    continue
                task = process_task()
                close_old_connections()
            _STOP.wait(0 if task else idle_sleep)
        except Exception:
            logger.exception("Embedded services worker iteration failed")
            close_old_connections()
            _STOP.wait(error_sleep)
    logger.info("Embedded services worker stopped")


def start_embedded_worker():
    global _STARTED, _THREAD
    if not _enabled() or not _allowed_process():
        return None
    with _START_LOCK:
        if _STARTED and _THREAD and _THREAD.is_alive():
            return _THREAD
        _STOP.clear()
        _THREAD = threading.Thread(target=_loop, name="services-worker", daemon=True)
        _THREAD.start()
        _STARTED = True
        return _THREAD


def stop_embedded_worker():
    _STOP.set()
    thread = _THREAD
    if thread and thread.is_alive():
        thread.join(timeout=3)
