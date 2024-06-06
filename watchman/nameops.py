from multiprocessing import Process
from time import sleep
from k8s import get_svc
import logging
from config import settings
import redis
import json


# Get the Logger
logger = logging.getLogger("app")

r = redis.Redis(host='localhost', port=6379, db=0)

def services_monitor():
    """
    services_monitor - monitors services in mainline namespace and puts them into DB
    """
    while True:
        services = get_svc(settings["namespace"])
        r.set('services', json.dumps(services))
        sleep(0.05)

def run_services_monitor():
    """
    run_services_monitor - runs services_monitor thread
    """
    monitor = Process(target=services_monitor, daemon=True, name="Services Monitor")
    monitor.start()