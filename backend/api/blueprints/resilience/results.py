from flask import Blueprint, request
from extensions import get_wrapper, post_wrapper, get_using_post_wrapper
import src.data.mysql.resilience as database_resilience

resilience_results_blueprint = Blueprint('resilience_results', __name__)

@resilience_results_blueprint.route('/get/', methods=["GET"])
@get_wrapper(pass_user_id=True)
def results_get(user_id):
    return database_resilience.MODEL_HELPERS.results_get(user_id)

@resilience_results_blueprint.route('/get/', methods=["POST"])
@get_using_post_wrapper(table_name="resilience", action="read", pass_user_id=True)
def result_get(request_dict, user_id):
    if 'id' in request_dict:
        return database_resilience.MODEL_HELPERS.result_get(request_dict['id'])
    return database_resilience.MODEL_HELPERS.results_get(user_id, method=request_dict['method'])

@resilience_results_blueprint.route('/remove/', methods=['POST'])
@post_wrapper(table_name="resilience", action="remove")
def remove(request_dict):
    return database_resilience.MODEL_HELPERS.remove(request_dict['id'])

@resilience_results_blueprint.route('/data_get/', methods=["POST"])
@get_using_post_wrapper(table_name="resilience", action="read")
def data_get(request_dict):
    return database_resilience.results_get(request_dict['id'])