import math
import zlib
import json
from . import mysql_microgrid
from .components import types_names_get as component_types_names_get
from . import model_helpers

MODEL_HELPERS = model_helpers.ModelDatabaseHelpers("resilience")

def disturbance_repair_get(id, table_name):
    """Returns a dictionary containing disturbance or repair data
    for the specified id"""
    try:  
        record = mysql_microgrid.DB.query(
            """SELECT d.componentId,{0} d.value, c.componentTypeId
                FROM {1}_data d
                JOIN component c ON c.id = d.componentId
                WHERE d.{1}Id = %s""".format(
                    "d.quantity," if table_name == "disturbance" else "",
                    table_name,
                ),
            values=[id], output_format="dict"
        )
    except Exception as error:
        raise mysql_microgrid.MicrogridDBException("disturbance_repair_get select failed in {0}_data for id = {1}\n{2}".format(
            table_name, id, error))
    return record

def disturbance_repair_get_single(id, table_name, metadata=None):
    """Returns a dictionary containing disturbance or repair data formatted for the API"""
    if metadata is None:
        try:  
            metadata = mysql_microgrid.DB.query(
                """SELECT d.id, d.name, d.description, d.gridId
                    FROM {0} d
                    WHERE d.id = %s""".format(
                        table_name,
                    ),
                values=[id], output_format="dict"
            )[0]
        except Exception as error:
            raise mysql_microgrid.MicrogridDBException("disturbance_repair_get_single select failed in {0} for id = {1}\n{2}".format(
                table_name, id, error))
    record_data = {
        "id": metadata["id"],
        "name": metadata["name"],
        "description": metadata["description"],
        "gridId": metadata["gridId"],
        "specs": disturbance_repair_get(metadata["id"], table_name),
    }
    try:
        components = mysql_microgrid.DB.query(
            """SELECT d.componentId, {0} d.value, c.componentTypeId
                FROM {1}_data d
                JOIN component c ON c.id = d.componentId
                WHERE d.{1}Id = %s""".format(
                "d.quantity," if table_name == "disturbance" else "",
                table_name
            ),
            values=[id], output_format="dict"
        )
        record_data["selected_components"] = {
            str(comp["componentId"]): {
                "value": comp["value"],
                "typeId": comp["componentTypeId"],
                #quantity is only present in disturbance data, add to dict if table_name is disturbance
                **({"quantity": comp["quantity"]} if table_name == "disturbance" else {})
            } for comp in components
        }
    except Exception as error:
        record_data["selected_components"] = {}
    return record_data

def disturbances_repairs_get(user_id, table_name):
    """Returns a dictionary keyed by id with a value dictionary
    containing both {table_name} and {table_name}_data"""
    valid_table_names=["disturbance", "repair"]
    if table_name not in valid_table_names:
        raise ValueError("get_records: input must be one of %r." % valid_table_names)
    try:
        records = mysql_microgrid.DB.query(
            """SELECT id, name, description, gridId
                FROM {0}
                JOIN {0}_user
                ON {0}_user.{0}Id = {0}.id
                WHERE {0}_user.userId = %s
                ORDER BY name""".format(table_name),
            values=[user_id], output_format="dict")
    except Exception as error:
        raise mysql_microgrid.MicrogridDBException("disturbance_repair_get select failed in "+table_name+"\n"+str(error))
    records_list = []
    for r in records:
        record_data = disturbance_repair_get_single(r["id"], table_name, metadata=r)
        records_list.append(record_data)
    return records_list

def disturbance_repair_update_attributes(id, specs, table_name):
    """Update data for a disturbance or repair in the database"""
    print("specs:",specs)
    if specs:
        try:
            # Insert/update component-specific data
            for component_id, data in specs.items():
                value = data.get("value", 1.0) if table_name == "disturbance" else data.get("value")
                min_value = 0.0 if table_name == "repair" else 0.0
                max_value = 1.0 if table_name == "disturbance" else math.inf
                mysql_microgrid.validate_input_value("float", value, min_value, max_value, "for spec id = {0} of ".format(component_id))
            
                data_dict = {
                    "{0}Id".format(table_name): id,
                    "componentId": component_id,
                    "value": value,
                }
                if table_name == "disturbance":
                    data_dict["quantity"] = data["quantity"]
                mysql_microgrid.DB.insert_update(
                    table_name="{0}_data".format(table_name),
                    data_dict=data_dict,
                )
        except Exception as error:
            raise mysql_microgrid.MicrogridDBException("disturbance_repair_update_attributes failed update for data = {0}\n{1}".format(
                data, error))
    return True, "Success"

def disturbance_repair_add(user_id, name, description, table_name, specifications=None, grid_id=None):
    """Add a disturbance or repair to the database"""
    mysql_microgrid.user_quota_check(user_id, table_name)
    if not mysql_microgrid.unused_name_in_table(user_id, table_name, name):
        return False, "{0} named {1} already exists for this user".format(table_name, name)  
    try:
        id = mysql_microgrid.DB.insert(
            table_name=table_name, 
            data_dict={ "name": name, "description": description, "id": None, "gridId": grid_id }
        )
    except Exception as error:
        raise mysql_microgrid.MicrogridDBException("disturbance_repair_add insert failed for {0} with name = {1}\n{3}".format(
            table_name, name, error))
    try:
        mysql_microgrid.DB.insert(
            table_name=table_name+"_user", 
            data_dict={ table_name+"Id":id, "userId":user_id, "permissionId": mysql_microgrid.PERMISSION_WRITE }
        )
    except Exception as error:
        raise mysql_microgrid.MicrogridDBException("disturbance_repair_add insert failed for {0}_user with {0} id = {1}\n{3}".format(
            table_name, id, error))
    disturbance_repair_update_attributes(id, specifications, table_name)
    return True, "Success"

def disturbance_repair_remove(id, table_name):
    """Remove a disturbance or repair from the database"""
    try:
        mysql_microgrid.DB.delete(table_name, {"id": id})
    except Exception as error:
        raise mysql_microgrid.MicrogridDBException("disturbance_repair_remove failed for {0} id = {1}\n{2}".format(
            table_name, id, error))
    return True, "Success"

def results_get(id):
    """Return a results dictionary from the database"""
    try:
        record = mysql_microgrid.DB.query(
            """SELECT results
                FROM resilience
                WHERE id = %s""",
        values=[id],output_format="dict")[0]
    except Exception as error:
        raise mysql_microgrid.MicrogridDBException("results_get select failed for id="+str(id)+"\n"+str(error))
    if record["results"] is not None:
        return json.loads(zlib.decompress(record["results"]).decode())
    return None

def results_add(id, results):
    """Add a results object to the database"""
    try:
        data_dict = {"results": zlib.compress(json.dumps(results).encode())}
        where_dict = {"id": id}
        mysql_microgrid.DB.update(table_name="resilience", data_dict=data_dict, where_dict=where_dict)
    except Exception as error:
        raise mysql_microgrid.MicrogridDBException("results_add insert failed\n"+str(error))
