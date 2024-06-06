from time import sleep
import redis
import logging
import requests
from datetime import datetime
import json
import k8s
from config import settings, level


logger = logging.getLogger("app")

r = redis.Redis(host='localhost', port=6379, db=0)


def to_integer(dt_time):
    """
    to_integer - Transforms Datetime to days (float)

    Keyword arguments:
    dt_time - Datetime delta between 2 times
    """
    try:
        days = dt_time.days + dt_time.seconds/60/60/24
    except AttributeError:
        days = dt_time.seconds/60/60/24
    return days

def calculate_last_change_lifetime(branch):
    """
    calculate_last_change_lifetime - calculates time between the last change and now

    Keyword arguments:
    branch - branch object
    """
    last_change_timestamp = datetime.strptime(branch['last_change_timestamp'], '%a, %d %b %Y %H:%M:%S %Z')
    ns_lifetime_time = datetime.now() - last_change_timestamp
    #logger.debug(f"Change lifetime { to_integer(ns_lifetime_time) }")    
    return to_integer(ns_lifetime_time)

def get_branches():
    try:
            r =requests.get(settings["harold_url"] + "/branches")
    except requests.exceptions.ConnectionError as err:
            #logger.error(err)
            return None
    return json.loads(r.text)

def check_cache(branches):
    branches_cached_bytes = r.get('branches')
    if branches_cached_bytes == None:
        r.set('branches', json.dumps(branches))
        return None
    cache_text = branches_cached_bytes.decode("utf-8")
    branches_cached = json.loads(branches_cached_bytes.decode("utf-8"))
    matched = None
    to_delete = []
    for cached_branch in branches_cached:
        for branch in branches:
            cb = cached_branch["name"]
            rb = branch["name"]
            logger.debug("Comparing " + cb + " to " + rb)
            if cb == rb:
                matched = True
                logger.debug("MATCH IS TRUE")
                break
            else:
                matched = False
                logger.debug("MATCH IS FALSE")
        logger.debug("Checking len(branches): " + str(len(branches)))
        if (matched is False) or len(branches) == 0:
            logger.debug("Marking branch to be deleted")
            to_delete.append(cached_branch)
    r.set('branches', json.dumps(branches))
    return to_delete

def delete_branch_namespace(branch):  
    name = branch["name"]  
    logger.debug(f"Deleting branch { name }")           
    try:
        payload = {'name':name}
        headers = {'content-type': 'application/json'}
        response = requests.delete(
            settings["harold_url"] + "/branches", 
            data=json.dumps(payload), 
            headers=headers)
    except requests.exceptions.ConnectionError as err:
        logger.error(err)
    finally:
        k8s.delete_ns(name)

def watcher():
    """
    watcher - is watching for changes in branches DB and runs according changes in a cluster
    """
    while True:
        sleep(1)
        branches = get_branches()
        if branches is None:
            continue
        branches_te_be_deleted = check_cache(branches)
        if branches_te_be_deleted is not None:
            for branch in branches_te_be_deleted:
                delete_branch_namespace(branch)
        for branch in branches:
            name = branch["name"]
            # Get list of namespaces
            namespaces = k8s.get_ns()
            match = False
            for namespace in namespaces:
                if name == namespace:
                    match = True
                    break
            black_mark = calculate_last_change_lifetime(branch) > branch["lifetime"] # namespace wipe criteria
            if (match == False) and black_mark:
                continue
            elif (match == False) and not black_mark:
                k8s.create_ns(name)
            elif (match == True) and black_mark:
                delete_branch_namespace(branch)
            else:
                continue                    
 