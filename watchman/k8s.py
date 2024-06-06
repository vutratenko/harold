from kubernetes import client, config
from kubernetes.client import V1Namespace
import logging

# Get the Logger
logger = logging.getLogger("app")
logger.setLevel(logging.DEBUG)

config.load_incluster_config()
v1 = client.CoreV1Api()

def get_ns():
    """
    get_ns - getting a list of namespaces
    """
    namespaces = []
    response = v1.list_namespace()
    for i in response.items:
        namespaces.append(i.metadata.name)
    #logger.debug("Got namespaces list")
    return namespaces

def get_svc(namespace):
    """
    get_svc - gets all services from specified namespace

    Keyword arguments:
    namespace - a k8s namespace to get services from
    """
    services = v1.list_service_for_all_namespaces(watch=False)
    svcs = []
    for service in services.items:
        if service.metadata.namespace == namespace:
            svc = dict(name=service.metadata.name, ip=service.spec.cluster_ip)
            svcs.append(svc)
            #logger.debug(svc)
    return svcs

def create_ns(name):
    """
    create_ns - creates a namespace

    Keyword arguments:
    name - namespace name
    """
    response = v1.create_namespace(V1Namespace(metadata=dict(name=name)))
    logger.debug(f"Created namespace { name } ")

def delete_ns(name):
    """
    delete_ns - deletes a namespace

    Keyword arguments:
    name - namespace name
    """
    response = v1.delete_namespace(name)
    logger.debug(f"Deleted namespace { name } ")
