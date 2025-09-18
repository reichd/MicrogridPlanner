import random
import copy
from datetime import timedelta
from src.components import defaults as comp_defaults

class Disturbance(object):

    def __init__(self, start_datetime, probabilities, repair_times, method):
        """Grid constructor __init__

        Keyword arguments:
        start_datetime      datetime when disturbance event starts
        probabilities       dictionary mapping generator types to probabilities
        repair_times        dictionary mapping generator types to repair times
        method              resilience method
        """
        self.start_datetime = start_datetime
        self.end_datetime = None
        self.duration = 0.0
        self._probabilities = { c["componentId"]:c["value"] for c in probabilities }
        self._quantities = { c["componentId"]:c["quantity"] for c in probabilities }
        self._repair_times = { c["componentId"]:c["value"] for c in repair_times }
        self._method = method
        self._affected = {}
        self._affected_quantity = {}
        self._simulated_times_to_repair = {}
        self._rand_num_generator = random.Random(random.uniform(0,20000))
        self._rand_state = self._rand_num_generator.getstate()

    def __repr__(self):
        return (f'{self.__class__.__name__}('
           f'start_datetime={self.start_datetime!r},'
           f'probabilities={self._probabilities!r},'
           f'repair_times={self._repair_times!r},'
           f'affected={self._affected!r},'
           f'simulated_times_to_repair={self._simulated_times_to_repair!r})')

    def simulate(self, grid):
        """Construct dictionary generator ID --> boolean operational status"""
        self._affected = {}
        quantity_remaining = copy.deepcopy(self._quantities)
        for generator in grid.get_generators():
            if quantity_remaining.get(generator.id_(), 0) == 0:
                self._affected[generator] = False
                continue
            quantity_remaining[generator.id_()] -= 1
            repair_time = self._repair_times.get(generator.id_(), 0)
            if self._method == "stochastic" and repair_time > 0:
                probability = self._probabilities.get(generator.id_(), 0)
                self._affected[generator] = self._rand_num_generator.uniform(0, 1) <= probability
                if self._affected[generator]:
                    self._simulated_times_to_repair[generator] = self._rand_num_generator.expovariate(
                        1.0/repair_time
                    )
            else:
                self._affected[generator] = True
                self._simulated_times_to_repair[generator] = repair_time

    def propogate(self, grid, time_periods):
        """Construct dictionary generator ID --> boolean operational status"""
        status = {}
        disturbance_end = self.start_datetime
        for generator in grid.get_generators():
            unavailable_start = None
            if self._affected[generator]:
                unavailable_start = self.start_datetime
                unavailable_end = self.start_datetime + timedelta(
                    hours=self._simulated_times_to_repair[generator]
                )
                if unavailable_end <= unavailable_start:
                    unavailable_end = unavailable_start
                elif unavailable_end > disturbance_end: 
                    disturbance_end = unavailable_end
            for time_period in time_periods:
                if unavailable_start is None:
                    online_ratio = 1.0
                elif time_period.end() <= unavailable_start:
                    online_ratio = 1.0
                elif time_period.start() >= unavailable_end:
                    online_ratio = 1.0
                elif time_period.start() >= unavailable_start and \
                        time_period.end() <= unavailable_end:
                    online_ratio = 0.0
                elif time_period.start() >= unavailable_start:
                    time_on = (time_period.end() - unavailable_end).total_seconds()/3600.0
                    online_ratio = time_on / time_period.duration()
                elif time_period.end() <= unavailable_end:
                    time_on = (unavailable_start - time_period.start()).total_seconds()/3600.0
                    online_ratio = time_on / time_period.duration()
                if time_period not in status: status[time_period] = {}
                status[time_period][generator] = online_ratio
        if disturbance_end > self.start_datetime + timedelta(hours=comp_defaults.EPSILON):
            self.end_datetime = disturbance_end
            self.duration = (self.end_datetime - self.start_datetime).total_seconds() / 3600.0
        else:
            self.end_datetime = self.start_datetime
            self.duration = 0.0
        return status
