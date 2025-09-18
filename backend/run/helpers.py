import os
import sys
import configparser
import json
import pickle
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from src.grid import Grid, Disturbance
from src.models import CoreSimulation, Weather, Sizing, Simulate, Resilience
import src.data.mysql.users as database_users
import src.data.mysql.grids as database_grids
from src.data.mysql import simulate, sizing, resilience

"""
Helpers for all run scripts
"""

DATABASES = {"simulate": simulate, "sizing": sizing, "resilience": resilience}

_CONFIG_INI_GLOBAL = configparser.ConfigParser()
_CONFIG_INI_GLOBAL.read(os.path.join(os.path.dirname(os.getcwd()),"config.ini"))
_FRONTEND_URL = _CONFIG_INI_GLOBAL.get("FRONTEND","URL",fallback="")
_ADMIN_EMAIL = _CONFIG_INI_GLOBAL.get("MAIL","MAIL_REPLY_TO",fallback="")

RNG_SEED = "random_number_generator_seed"
LOAD_ID = "load_id"
GRID_ID = "grid_id"
METHOD = "method"
DISTURBANCE_STARTDATETIME = "disturbance_startdatetime"
DISTURBANCE_ID = "disturbance_id"
LOCATION_ID = "location_id"
STARTDATETIME = "startdatetime"
ENDDATETIME = "enddatetime"
EXTEND_TIMEFRAME = "extend_timeframe_proportion"
REPAIR_ID = "repair_id"
ENERGY_MANAGEMENT_SYSTEM_ID = "energy_management_system_id"
NUM_RUNS = "num_runs"
NUM_SHIFT_HOURS = "disturbance_shift_hours"
NUM_LEVELS = "num_levels"
ALGORITHM = "algorithm"
DEBUG = "debug"
WEATHER_SAMPLE_METHOD = "weather_sample_method"
PARAMS_JSON_FILENAME = "params.json"
PARAMS_PICKLE_FILENAME = "params.pkl"

def initialize_simulation_object(run_param_dict):
    """
    Initialize simulation object according to input run parameter dictionary
    """
    grid = Grid(diesel_level=sys.float_info.max)
    try:
        components = database_grids.get_components(run_param_dict[GRID_ID], objectFlag=True)
    except Exception as error:
        raise Exception("Error in initialize_simulation_object retrieving components:\n"+str(error))
    if len(components) == 0:
        raise ValueError("Cannot initialize_simulation_object on a microgrid with no components")
    try:
        weather = Weather(run_param_dict[LOCATION_ID], run_param_dict[WEATHER_SAMPLE_METHOD])
    except Exception as error:
        raise Exception("Error in initialize_simulation_object retrieving weather data:\n"+str(error))
    grid.initialize_components(components)
    if DISTURBANCE_ID in run_param_dict and run_param_dict[DISTURBANCE_ID] is not None:
        try:
            disturbance_probs = DATABASES["resilience"].disturbance_repair_get(run_param_dict[DISTURBANCE_ID], "disturbance")
        except Exception as error:
            raise Exception("initialize_simulation_object failed to retrieve disturbance probabilities:\n"+str(error))
        try:
            repair_times = DATABASES["resilience"].disturbance_repair_get(run_param_dict[REPAIR_ID], "repair")
        except Exception as error:
            raise Exception("initialize_simulation_object failed to retrieve repair times:\n"+str(error))
        disturbance = Disturbance(
            start_datetime=run_param_dict[DISTURBANCE_STARTDATETIME],
            probabilities=disturbance_probs,
            repair_times=repair_times,
            method=run_param_dict[METHOD],
        )
    else:
        disturbance = None
    sim = CoreSimulation(
        grid=grid,
        energy_management_system_id=run_param_dict[ENERGY_MANAGEMENT_SYSTEM_ID],
        powerload_id=run_param_dict[LOAD_ID],
        start_datetime=run_param_dict[STARTDATETIME] if STARTDATETIME in run_param_dict else None,
        end_datetime=run_param_dict[ENDDATETIME] if ENDDATETIME in run_param_dict else None,
        weather=weather,
        extend_proportion= run_param_dict[EXTEND_TIMEFRAME] 
                            if EXTEND_TIMEFRAME in run_param_dict and run_param_dict[EXTEND_TIMEFRAME] is not None else 0,
        disturbance=disturbance,
    )
    return sim

def timestamp_now():
    """Get current timestamp in format YYMMDD_HHMMSS"""
    return datetime.now().strftime("%y%m%d_%H%M%S")

def get_system_root_dir():
    """Get the root directory for results storage from config.ini"""
    config_file = "config.ini"
    config_dir_section = "DEFAULT"
    config_results_root = "RESULTS_ROOT_DIR"
    config = configparser.ConfigParser()
    config.read(config_file)
    try:
        root_dir = config.get(config_dir_section,config_results_root)
    except Exception as error:
        raise IOError("Copy config.ini.template to "+config_file+"\n"+str(error))
    if not os.path.isdir(root_dir):
        yno = input(root_dir + " Does not exist. Create it? [Y/n]: ")
        if len(yno) == 0:
            yno = "y"
        if yno.lower() == "y":
            try:
                os.makedirs(root_dir)
            except Exception as error:
                raise IOError("Unable to create directory "+root_dir+"\n"+str(error))
        else:
            raise IOError("Valid root directory for results must be specified in "+config_file+"\n")
    return root_dir

def email(recipient_email, subject, message_body):
    """Send an email to recipient_email with subject and message_body"""
    if _CONFIG_INI_GLOBAL.getboolean("MAIL","MAIL_DISABLE_FOR_RUN_LOCAL",fallback=False): return
    smtp_server = _CONFIG_INI_GLOBAL.get("MAIL","MAIL_SERVER")
    smtp_port = _CONFIG_INI_GLOBAL.get("MAIL","MAIL_PORT")
    sender_email = _CONFIG_INI_GLOBAL.get("MAIL","MAIL_USERNAME")
    sender_password = _CONFIG_INI_GLOBAL.get("MAIL","MAIL_PASSWORD", fallback=None)
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = subject
    message.add_header("reply-to", _ADMIN_EMAIL)
    message_body="<html><head></head><body>"+message_body+"</body></html>"
    message.attach(MIMEText(message_body, "html"))
    try:
        if _CONFIG_INI_GLOBAL.getboolean("MAIL","MAIL_USE_SSL",fallback=False):
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server = smtplib.SMTP(smtp_server, smtp_port)
        if sender_password is not None:
            if _CONFIG_INI_GLOBAL.getboolean("MAIL","MAIL_USE_TLS",fallback=False):
                server.ehlo()
                server.starttls()
                server.ehlo()
            server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, message.as_string())
        server.quit()
    except Exception as error:
        raise Exception(error)

def email_compute_success(table_name, id, results_relative_url):
    """Email the user that the computation has completed successfully."""
    if id is None: return
    recipient_email = None if id is None else database_users.get_result_email(table_name, id)
    if recipient_email is None: return
    try:
        email(
            recipient_email=recipient_email,
            subject="{0} complete: id = {1}".format(table_name, id),
            message_body="<a href=\"{0}/tools/{1}{2}\">View result</a>".format(
                _FRONTEND_URL, results_relative_url, id
            )
        )
    except Exception:
        raise RuntimeError("success email failed to send")

def email_compute_failure(table_name, id, error, admin_only=False):
    """Email the user that the computation has failed.
    Email the admin that the computation has failed with details."""
    if id == None: return
    recipient_email = database_users.get_result_email(table_name, id)
    try:
        email(
            recipient_email=_ADMIN_EMAIL,
            subject="{0} failed: id = {1}, user = {2}".format(table_name, id, recipient_email),
            message_body=str(error)
        )
    except Exception:
        raise RuntimeError("failure email failed to send to admin")
    if admin_only: return
    if recipient_email is None: return
    time.sleep(5)
    try:
        email(
            recipient_email=recipient_email,
            subject="{0} failed: id = {1}".format(table_name, id),
            message_body="Contact <a href=\"mailto:{0}\">{0}</a> for more info.".format(_ADMIN_EMAIL)
        )
    except Exception:
        raise RuntimeError("failure email failed to send to user")

def run_analysis(table_name, id, params, results_relative_url, send_email=True):
    """Run the analysis specified by table_name with input parameters params."""
    results_dir = None if id is not None else os.path.join(
        get_system_root_dir(),
        str(params[LOAD_ID]),
        table_name,
        timestamp_now(),
    )
    if results_dir is not None: 
        os.makedirs(results_dir)
        with open(os.path.join(results_dir, PARAMS_JSON_FILENAME), "wt", encoding="utf-8") as f:
            json.dump(params, f, indent=4, default=str)
        with open(os.path.join(results_dir, PARAMS_PICKLE_FILENAME), 'wb') as f:
            pickle.dump(params, f)
    try:
        core_sim = initialize_simulation_object(params)
        if table_name == "simulate":
            simulate = Simulate(core_sim)
            simulate.run(results_dir=results_dir, database_id=id)
        elif table_name == "sizing":
            simulate = Sizing(core_sim, params[NUM_LEVELS])
            simulate.run(algorithm=params[ALGORITHM], results_dir=results_dir, database_id=id, debug=params[DEBUG])
        elif table_name == "resilience":
            resilience = Resilience(core_sim)
            resilience.run(hours=params[NUM_SHIFT_HOURS], results_dir=results_dir, database_id=id, debug=params[DEBUG])
        else:
            raise ValueError("run_analysis unknown type = "+table_name)
    except Exception as error:
        raise RuntimeError("Error in "+table_name+" run\n"+str(error))
    DATABASES[table_name].MODEL_HELPERS.compute_job_status_add(id, True)
    if send_email:
        email_compute_success(table_name=table_name, id=id, results_relative_url=results_relative_url)
