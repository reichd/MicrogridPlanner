#!/usr/bin/env python3

import os
import json
import pickle
import random
import run.helpers as run_helpers
from src.models import Rightsize

"""
Script to run microgrid rightsizing method from Reich & Oriti (2021)
(limited to diesel, photovoltaic, battery).
Replaced with more general sizing method in sizing.py,
but code maintained for comparison purposes only.
"""

STEP_SIZE_BATTERY = 1000
STEP_SIZE_DIESEL = 1000
STEP_SIZE_PHOTOVOLTAIC = 1000

RANDOM_SEED = 0
random.seed(RANDOM_SEED)

# edit run parameters
RUN_SIM = True # set to False when replotting rightsized points with zoom window
RUN_PARAMS = {
    run_helpers.RNG_SEED:RANDOM_SEED,
    run_helpers.LOAD_ID:1,
    run_helpers.GRID_ID:250,
    run_helpers.LOCATION_ID: 145612,
    run_helpers.WEATHER_SAMPLE_METHOD : "mean",
    run_helpers.ENERGY_MANAGEMENT_SYSTEM_ID:4,
    run_helpers.EXTEND_TIMEFRAME:0.0,
    run_helpers.ENERGY_MANAGEMENT_SYSTEM_ID:4,
    "step_size_battery":STEP_SIZE_BATTERY,
    "step_size_diesel":STEP_SIZE_DIESEL,
    "step_size_photovoltaic":STEP_SIZE_PHOTOVOLTAIC,
    run_helpers.DISTURBANCE_ID:None,
    run_helpers.DISTURBANCE_STARTDATETIME:None,
    run_helpers.REPAIR_ID:None,
}
RESULTS_DIR = os.path.join(
    run_helpers.get_system_root_dir(),
    str(RUN_PARAMS[run_helpers.LOAD_ID]),
    "rightsize",
    "b"+str(int(STEP_SIZE_BATTERY)) \
        +"_dg"+str(STEP_SIZE_DIESEL)
        +"_pv"+str(STEP_SIZE_PHOTOVOLTAIC),
    run_helpers.timestamp_now(),
)

# create results directory
os.makedirs(RESULTS_DIR, exist_ok=True)

# write params in human-readable format
with open(os.path.join(RESULTS_DIR,run_helpers.PARAMS_JSON_FILENAME), "wt", encoding="utf-8") as f:
    json.dump(RUN_PARAMS, f, indent=4, default=str)

# write params in machine-readable format
with open(os.path.join(RESULTS_DIR,run_helpers.PARAMS_PICKLE_FILENAME), 'wb') as f:
    pickle.dump(RUN_PARAMS, f)

CSV = os.path.join(RESULTS_DIR, "rightsize.csv")
if RUN_SIM:
    CORE_SIM = run_helpers.initialize_simulation_object(RUN_PARAMS)
    RIGHTSIZE = Rightsize(
        core_sim = CORE_SIM, 
        step_size_b = STEP_SIZE_BATTERY,
        step_size_dg = STEP_SIZE_DIESEL,
        step_size_pv = STEP_SIZE_PHOTOVOLTAIC,
        dirpath = RESULTS_DIR,
    )
    RIGHTSIZE.to_csv(CSV)
