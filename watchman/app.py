#!/usr/bin/env python3

from nameops import run_services_monitor
from fake_dns import run_dns_server
from rest import run_rest
from watcher import watcher
import logging
import ecs_logging
from multiprocessing import Pipe
from config import settings, level



# Get the Logger
logger = logging.getLogger("app")
logger.setLevel(level)

# Add an ECS formatter to the Handler
handler = logging.StreamHandler()
handler.setFormatter(ecs_logging.StdlibFormatter())
logger.addHandler(handler)


if __name__ == '__main__':
    run_services_monitor()
    run_dns_server()
    run_rest()
    watcher()