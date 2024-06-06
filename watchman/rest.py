from flask import Flask,request,jsonify,Response
from flask.logging import default_handler
from multiprocessing import Process
import requests
import logging
import ecs_logging
from config import settings
from k8s import get_ns
import redis
import json
import waitress


app = Flask(__name__)
default_handler.setFormatter(ecs_logging.StdlibFormatter())
logger = logging.getLogger('waitress')
handler = logging.StreamHandler()
handler.setFormatter(ecs_logging.StdlibFormatter())
logger.addHandler(handler)


@app.route("/healthz/liveness", methods=['GET'])
def liveness():
    resp = {
            "status": 200,
            "application": "UP"}
    return jsonify(resp)

@app.route("/healthz/readiness", methods=['GET'])
def readiness():
    resp = {
            "status": 200,
            "application": "UP",
            "harold": "AVAILABLE",
            "kubernetes": "AVAILABLE",
            "redis": "AVAILABLE"}
    try:
        r =requests.get(settings["harold_url"] + "/branches")
    except:
        resp["harold"] = "NOT AVAILABLE"
        resp["status"] = 500
    try:
        get_ns()
    except:
        resp["kubernetes"] = "NOT AVAILABLE"
        resp["status"] = 500
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
    except:
        resp["kubredisernetes"] = "NOT AVAILABLE"
        resp["status"] = 500
    return Response(json.dumps(resp), status=resp["status"], mimetype='application/json')

def app_run():
    waitress.serve(app, listen="0.0.0.0:" + str(settings["http_port"]))

def run_rest():
    rest = Process(target=app_run, daemon=True, name="REST interface")
    rest.start()