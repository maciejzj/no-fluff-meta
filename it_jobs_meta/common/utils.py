"""Utility tools shared across the application."""

import functools
import logging
import sys
import time
from pathlib import Path
from typing import Any, Callable, ParamSpec, TypeVar

import yaml


def setup_logging(*args: Path, log_level: int = logging.INFO):
    """Enable logging to stdout and the given files.

    :param *args: Paths to log output files.
    """
    log_file_handlers = []
    for log_path in args:
        log_path.parent.mkdir(exist_ok=True, parents=True)
        log_file_handlers.append(logging.FileHandler(log_path))

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            *log_file_handlers,
            logging.StreamHandler(sys.stdout),
        ],
    )


def load_yaml_as_dict(path: Path) -> dict[str, Any]:
    with open(path, 'r', encoding='UTF-8') as yaml_file:
        return yaml.safe_load(yaml_file)


P = ParamSpec("P")
R = TypeVar("R")


def throttle(seconds: float) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            ret = func(*args, **kwargs)
            time.sleep(seconds)
            return ret

        return wrapper

    return decorator
