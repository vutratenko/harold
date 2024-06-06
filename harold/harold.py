#!/usr/bin/env python3

from flask import Flask,request,jsonify,Response
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import func
import sqlalchemy
from datetime import date,datetime
from flask.logging import default_handler
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
import json
import logging
import ecs_logging
from config import settings
import waitress
from paste.translogger import TransLogger

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = settings["db_string"]
app.config['SQLALCHEMY_POOL_TIMEOUT'] = settings["pool_timeout"]
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = settings["secret_key"]
app.config['FLASK_ADMIN_SWATCH'] = settings["admin_bootswatch_theme"]
admin = Admin(app, name='harold', template_mode='bootstrap3')
db = SQLAlchemy(app)
migrate = Migrate(app, db) 

branch_namespace_lifetime = int(settings["branch_namespace_lifetime"])


#default_handler.setFormatter(ecs_logging.StdlibFormatter())
app.logger.setLevel(logging.INFO)
logger = logging.getLogger('waitress')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(ecs_logging.StdlibFormatter())
logger.addHandler(handler)
app.logger.addHandler(handler)


class BranchModel(db.Model):
    __tablename__ = 'branches'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    lifetime = db.Column(db.Integer, nullable=False)
    creation_timestamp = db.Column(db.DateTime, nullable=False, server_default=func.now())
    last_change_timestamp = db.Column(db.DateTime, nullable=False)
    
    def __init__(self, name, last_change_timestamp):
            self.name = name
            self.lifetime = branch_namespace_lifetime #settings["branch_namespace_lifetime"]
            self.last_change_timestamp = last_change_timestamp
            
    def __repr__(self):
        return '<Branch %r>' % self.name

class BranchesView(ModelView):
    can_create = False
    can_edit = False
    page_size = 50
    

admin.add_view(BranchesView(BranchModel, db.session, name="Branches"))

def mutate_name(name):
    if name.split("-")[0] == "branch":
        new_name = ""
    else:
        new_name = "branch-"
    for character in name:
        if character.isalnum() or (character == "-"):
            new_name += character
        else:
            new_name += "---"
    return new_name.lower()

def process_branches(name,method):
    """
    process_branches - processing branches in DB

    Keyword arguments:
    name - branch name
    method - HTTP request method
    db - Flask_sqlalchemy DB session
    """
    app.logger.debug("Received name: " + str(name) + " and method: " + method)
    if name is not None:
        app.logger.debug(f"Name is not None: {name}")
        branch = BranchModel.query.filter_by(name=name).first()
        app.logger.debug(f"Got a branch { branch }")
    else:
        branch = None
    branches = None
    err = None
    try:
        if method == "POST":
            if branch is None :
                app.logger.debug(f"Creating with name { name }")
                new_branch = BranchModel(name=name, last_change_timestamp=func.now())
                db.session.add(new_branch)
            else:
                app.logger.debug(branch.name)
                branch.last_change_timestamp = func.now()
        elif method == "DELETE":
            app.logger.debug(str(branch))
            db.session.delete(branch)
        else:
            results = BranchModel.query.all()
            app.logger.debug(f"Trying to iterate results { str(results) }")
            branches = [
                {
                    "name": result.name,
                    "lifetime": result.lifetime,
                    "creation_timestamp": result.creation_timestamp,
                    "last_change_timestamp": result.last_change_timestamp
                } for result in results]
        db.session.commit()
    except (sqlalchemy.exc.DataError,NameError) as err:
        app.logger.error(err)
    return branches, err

@app.route("/branches", methods=['GET','POST','DELETE'])
def get_branches():
    """
    get_branches - handles branches CRUD

    HTTP methods
    GET - returns all branches
    POST - creates a branch
    DELETE - deletes a branch
    """
    if request.is_json:
        data = request.get_json()
        name = mutate_name(data["name"])
    else:
        name = None
        if (request.method == 'POST') or (request.method == 'DELETE'):
            return Response("message:" f"Please use Content-Type: application/json", status=400, mimetype='application/json')
    branches, err = process_branches(name=name,method=request.method)
    app.logger.debug("Processed branches")
    if err is not None:
        raise err
        return None
    else:
        if request.method == 'POST':
            return Response("message:" f"branch { name } has been created/updated successfully.", status=201, mimetype='application/json')
        elif request.method == 'DELETE':
            return {"message": f"branch { name } has been deleted successfully."}
        else:
            return jsonify(branches)

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
            "database": "AVAILABLE"}
    try:
        engine = db.get_engine()
        conn = engine.connect()
        conn.close()
    except:
        resp["database"] = "NOT AVAILABLE"
        resp["status"] = 500
        return Response(json.dumps(resp), status=500, mimetype='application/json')
    else:
        return jsonify(resp)

if __name__ == '__main__':
    waitress.serve(app, listen="0.0.0.0:" + str(settings["port"]))
