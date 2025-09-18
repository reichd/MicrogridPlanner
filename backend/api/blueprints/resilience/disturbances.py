from flask import Blueprint
from extensions import get_wrapper, get_using_post_wrapper, post_wrapper, update_name_description
import src.data.mysql.resilience as database_resilience

resilience_disturbances_blueprint = Blueprint('disturbances', __name__)

@resilience_disturbances_blueprint.route('/get/', methods=["POST"])
@get_using_post_wrapper(table_name="disturbance", action="read", pass_user_id=False, pass_table_name=False)
def disturbance_get_single(request_dict):
    return database_resilience.disturbance_repair_get_single(request_dict["id"], "disturbance")

@resilience_disturbances_blueprint.route('/get/', methods=["GET"])
@get_wrapper(pass_user_id=True)
def disturbance_get(user_id):
    return database_resilience.disturbances_repairs_get(user_id, "disturbance")

@resilience_disturbances_blueprint.route('/update_name_description/', methods=['POST'])
@post_wrapper(table_name="disturbance", action="update", pass_user_id=True, pass_table_name=True)
def disturbance_update_name_description(request_dict, user_id, table_name):
    return update_name_description(request_dict, user_id, table_name)

@resilience_disturbances_blueprint.route('/update_attributes/', methods=['POST'])
@post_wrapper(table_name="disturbance", action="update")
def disturbance_update_attributes(request_dict):
    return database_resilience.disturbance_repair_update_attributes(
        id=request_dict['id'],
        specs=request_dict['attributes'],
        table_name="disturbance",
    )

@resilience_disturbances_blueprint.route('/add/', methods=['POST'])
@post_wrapper(table_name="disturbance", action="add", pass_user_id=True)
def disturbance_add(request_dict, user_id):
    return database_resilience.disturbance_repair_add(
        user_id=user_id,
        name=request_dict['name'], 
        description=request_dict['description'], 
        table_name="disturbance",
        specifications=request_dict.get('selectedComponents', {}),
        grid_id=request_dict['gridId']
    )

@resilience_disturbances_blueprint.route('/remove/', methods=['POST'])
@post_wrapper(table_name="disturbance", action="remove")
def disturbance_remove(request_dict):
    return database_resilience.disturbance_repair_remove(request_dict['id'], "disturbance")

@resilience_disturbances_blueprint.route('/update_components/', methods=['POST'])
@post_wrapper(table_name="disturbance", action="update")
def disturbance_update_components(request_dict):
    return database_resilience.disturbance_repair_update_attributes(
        id=request_dict['id'],
        specs=request_dict['selectedComponents'],
        table_name='disturbance'
    )
