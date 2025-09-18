#!/usr/bin/env python3

import configargparse
import run.helpers as run_helpers
from datetime import datetime
from src.data.mysql import simulate, sizing, resilience

"""
Script to run models

Command-line inputs
"""

try:
    DATABASES = {"simulate": simulate, "sizing": sizing, "resilience": resilience}
    PARSER = configargparse.ArgParser()
    PARSER.add_argument("-c", "--config_file", is_config_file=True)
    PARSER.add_argument("-m", "--model_type", type=str, choices=list(DATABASES.keys()), default=None)
    PARSER.add_argument("-r","--compute_id", type=int, default=None)
    PARSER.add_argument("--grid_id", type=int, default=None)
    PARSER.add_argument("--location_id", type=int, default=None)
    PARSER.add_argument("--energy_management_system_id", type=int, default=None)
    PARSER.add_argument("--powerload_id", type=int, default=None)
    PARSER.add_argument("--startdatetime", type=str, default=None, help='Start date and time (format: YYYY-MM-DD_HH:MM:SS)')
    PARSER.add_argument("--enddatetime", type=str, default=None, help='End date and time (format: YYYY-MM-DD_HH:MM:SS)')
    PARSER.add_argument("--disturbance_startdatetime", type=str, default=None, help='Disturbance start date and time (format: YYYY-MM-DD_HH:MM:SS)')
    PARSER.add_argument("--disturbance_id", type=int, default=None)
    PARSER.add_argument("--repair_id", type=int, default=None)
    PARSER.add_argument("--extend_timeframe", type=float, default=None, help="proportion of duration to add past end date (e.g., 1.0 for double time)")
    PARSER.add_argument("--num_runs", type=int, default=None)
    PARSER.add_argument("--num_shift_hours", type=int, default=None)    
    PARSER.add_argument("--method", type=str, default=None)
    PARSER.add_argument("--num_levels", type=int, default=11)
    PARSER.add_argument("--algorithm", type=str, default="heuristic")
    PARSER.add_argument("--debug", dest="debug", action="store_true")
    MODEL_TYPE = PARSER.parse_args().model_type
    RUN_ID = PARSER.parse_args().compute_id
    if RUN_ID is not None:
        DATABASES[MODEL_TYPE].MODEL_HELPERS.compute_job_starttime_add(RUN_ID)
        RUN_INFO = DATABASES[MODEL_TYPE].MODEL_HELPERS.result_get(RUN_ID, objectFlag=True)
        GRID_ID = RUN_INFO["gridId"]
        LOCATION_ID = RUN_INFO["locationId"]
        ENERGY_MANAGEMENT_SYSTEM_ID = RUN_INFO["energyManagementSystemId"]
        POWERLOAD_ID = RUN_INFO["powerloadId"]
        STARTDATETIME = RUN_INFO["startdatetime"]
        ENDDATETIME = RUN_INFO["enddatetime"]
        DISTURBANCE_STARTDATETIME = RUN_INFO["disturbanceStartdatetime"] if "disturbanceStartdatetime" in RUN_INFO else None
        DISTURBANCE_ID = RUN_INFO["disturbanceId"] if "disturbanceId" in RUN_INFO else None
        REPAIR_ID = RUN_INFO["repairId"] if "repairId" in RUN_INFO else None
        EXTEND_TIMEFRAME = RUN_INFO["extendTimeframe"] if "extendTimeframe" in RUN_INFO else None
        NUM_RUNS = RUN_INFO["numRuns"] if "numRuns" in RUN_INFO else None
        NUM_SHIFT_HOURS = RUN_INFO["numShiftHours"] if "numShiftHours" in RUN_INFO else None
        METHOD = RUN_INFO["method"] if "method" in RUN_INFO else None
    else:
        GRID_ID = PARSER.parse_args().grid_id
        LOCATION_ID = PARSER.parse_args().location_id
        ENERGY_MANAGEMENT_SYSTEM_ID = PARSER.parse_args().energy_management_system_id
        POWERLOAD_ID = PARSER.parse_args().powerload_id
        if PARSER.parse_args().startdatetime:
            try:
                STARTDATETIME = datetime.strptime(PARSER.parse_args().startdatetime, '%Y-%m-%d_%H:%M:%S')
            except ValueError:
                raise ValueError("Invalid startdatetime format. Please use YYYY-MM-DD_HH:MM:SS.")
        else: STARTDATETIME = None
        if PARSER.parse_args().enddatetime:
            try:
                ENDDATETIME = datetime.strptime(PARSER.parse_args().enddatetime, '%Y-%m-%d_%H:%M:%S')
            except ValueError:
                raise ValueError("Invalid enddatetime format. Please use YYYY-MM-DD_HH:MM:SS.")
        else: ENDDATETIME = None
        if PARSER.parse_args().disturbance_startdatetime:
            try:
                DISTURBANCE_STARTDATETIME = datetime.strptime(PARSER.parse_args().disturbance_startdatetime, '%Y-%m-%d_%H:%M:%S')
            except ValueError:
                raise ValueError("Invalid disturbanceStartdatetime format. Please use YYYY-MM-DD_HH:MM:SS.")
        else: DISTURBANCE_STARTDATETIME = None
        DISTURBANCE_ID = PARSER.parse_args().disturbance_id
        REPAIR_ID = PARSER.parse_args().repair_id
        EXTEND_TIMEFRAME = float(PARSER.parse_args().extend_timeframe) 
        NUM_RUNS = int(PARSER.parse_args().num_runs)
        NUM_SHIFT_HOURS = int(PARSER.parse_args().num_shift_hours)
        METHOD = PARSER.parse_args().method
    NUM_LEVELS = PARSER.parse_args().num_levels
    ALGORITHM = PARSER.parse_args().algorithm
    DEBUG = PARSER.parse_args().debug

    RUN_PARAMS = {
        run_helpers.LOAD_ID:POWERLOAD_ID,
        run_helpers.GRID_ID:GRID_ID,
        run_helpers.LOCATION_ID: LOCATION_ID,
        run_helpers.ENERGY_MANAGEMENT_SYSTEM_ID:ENERGY_MANAGEMENT_SYSTEM_ID,
        run_helpers.STARTDATETIME:STARTDATETIME,
        run_helpers.ENDDATETIME:ENDDATETIME,
        run_helpers.WEATHER_SAMPLE_METHOD : "mean", # NEED TO UPDATE FOR RESILIENCE
        run_helpers.DISTURBANCE_ID:DISTURBANCE_ID, # only applies to resilience
        run_helpers.DISTURBANCE_STARTDATETIME:DISTURBANCE_STARTDATETIME, # only applies to resilience
        run_helpers.REPAIR_ID:REPAIR_ID, # only applies to resilience
        run_helpers.EXTEND_TIMEFRAME:EXTEND_TIMEFRAME, # only applies to resilience
        run_helpers.NUM_RUNS:NUM_RUNS, # only applies to resilience
        run_helpers.NUM_SHIFT_HOURS:NUM_SHIFT_HOURS, # only applies to resilience
        run_helpers.METHOD:METHOD, # only applies to resilience
        run_helpers.NUM_LEVELS:NUM_LEVELS, # only applies to sizing
        run_helpers.ALGORITHM:ALGORITHM, # only applies to sizing
        run_helpers.DEBUG:DEBUG,
    }
    send_email = True
    if MODEL_TYPE == "simulate":
        send_email = False
        results_relative_url = "simulate/compute/?id="
    elif MODEL_TYPE == "sizing":
        results_relative_url="sizing/results/"
    elif MODEL_TYPE == "resilience":
        send_email = False
        results_relative_url="resilience/results/"
    else:
        raise ValueError("run unknown type = "+MODEL_TYPE)
    run_helpers.run_analysis(table_name=MODEL_TYPE, id=RUN_ID, params=RUN_PARAMS, results_relative_url=results_relative_url, send_email=send_email)
except Exception as error:
    admin_only = MODEL_TYPE == "simulate"
    DATABASES[MODEL_TYPE].MODEL_HELPERS.compute_job_status_add(RUN_ID, False)
    run_helpers.email_compute_failure(table_name=MODEL_TYPE, id=RUN_ID, error=error, admin_only=admin_only)
    raise RuntimeError(MODEL_TYPE+" run failed")
