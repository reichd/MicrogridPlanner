import statistics
import math
from datetime import timedelta
import src.data.mysql.resilience as database_resilience

class Resilience(object):

    def __init__(self, core_sim):
        self._core_sim = core_sim
    
    def _local_shift_method(self, timesteps, start_specified, duration, num_hours=None, max_num_shifts=100):
        """Compute resilience using the local shift method"""
        start, end = _local_shift_method_range(timesteps, start_specified, duration, num_hours=num_hours)
        if num_hours is not None and num_hours < max_num_shifts:
            max_num_shifts = int(num_hours)+1
        all_start_times = _time_window(timesteps, start, end)
        selected_start_time_indices = [i for i in range(0,len(all_start_times))]
        if len(all_start_times) > max_num_shifts:
            modulo_divisor = round(len(all_start_times) / (max_num_shifts-1))
            selected_start_time_indices = [i for i in range(0,len(all_start_times)) 
                                    if i % modulo_divisor == 0]
            if len(all_start_times)-1 not in selected_start_time_indices:
                selected_start_time_indices.append(len(all_start_times)-1)
        average_performance = {}
        for i in selected_start_time_indices:
            ts = all_start_times[i].time_period().start()
            self._core_sim.disturbance.start_datetime = ts
            metrics = self._core_sim.run()
            time_window = _time_window(timesteps, ts, ts + timedelta(hours=duration))
            results = _fixed_window_wrapper(metrics, time_window)
            for key, value in results.items():
                if key not in average_performance:
                    average_performance[key] = value
                else:
                    average_performance[key] += value
        results = {}
        prefix = (f"Local ({num_hours})" if num_hours else "Global")+" Shift Method - "
        for key in average_performance:
            results[prefix+key] = average_performance[key] / len(selected_start_time_indices)
        self._core_sim.disturbance.start_datetime = start_specified
        return results

    def _global_shift_method(self, timesteps, duration, max_num_shifts=100):
        """Compute resilience using the global shift method"""
        start = timesteps[0].time_period().start()
        return self._local_shift_method(timesteps, start, duration, max_num_shifts=max_num_shifts)

    def run(self, hours=None, results_dir=None, database_id=None, debug=False):
        metrics = self._core_sim.run()
        start = self._core_sim.disturbance.start_datetime
        end = self._core_sim.disturbance.end_datetime
        duration = self._core_sim.disturbance.duration
        time_window = _time_window(metrics.timesteps, start, end)
        fixed_window = _fixed_window_method(metrics, time_window)
        default_num_hours = 24
        local_shift = self._local_shift_method(metrics.timesteps, start, duration, num_hours=default_num_hours)
        if hours is not None and hours > 0 and hours != default_num_hours:
            local_shift_requested = self._local_shift_method(metrics.timesteps, start, duration, num_hours=hours)
            local_shift = {**local_shift, **local_shift_requested}
        global_shift = self._global_shift_method(metrics.timesteps, duration)
        results = {**fixed_window, **local_shift, **global_shift}
        if database_id is not None:
            _results_to_database(database_id, results)

def _results_to_database(id, results):
    """write the resilience analysis results to database"""
    database_resilience.results_add(id, results)

def _time_window(timesteps, start, end):
    """Return time window between given start and end datetimes"""
    time_window = []
    for t in timesteps:
        if start <= t.time_period().mid() <= end:
            time_window.append(t)
    if len(time_window) == 0:
        time_diff = math.inf
        for t in timesteps:
            curr_diff = (t.time_period().mid() - start).total_seconds()
            if curr_diff < time_diff:
                time_diff = curr_diff
                time_window = [t]
    return time_window

def _time_window_duration(window):
    """Compute the duration in hours of a time window"""
    time_difference = window[len(window)-1].time_period().end()-window[0].time_period().start()
    return time_difference.total_seconds() / 3600.0

def _fixed_time_window_giachetti_2022(metrics, time_window):
    """Compute resilience using the fixed time window method
    of Giachetti et. al. (2022)"""
    omega = 0.5
    if len(time_window) == 0:
        return 1.0
    invulnerability = metrics.load_satisfaction_ratio[time_window[0]]
    energy_supply = 0.0
    enery_load = 0.0
    for t in time_window:
        energy_supply += min(metrics.supply[t], metrics.load[t]) * t.time_period().duration()
        enery_load += metrics.load[t] * t.time_period().duration()
    recovery = energy_supply/enery_load if enery_load > 0.0 else 1.0
    return omega * invulnerability + (1-omega) * recovery

def _performance(metrics, t, denominator):
    """Generic performance function"""
    return min(1.0,metrics.supply[t]/denominator) if denominator > 0.0 else 1.0

def _peak_demand_performance_method(metrics, t):
    """Compute resilience at a given time t using the average demand method"""
    return _performance(metrics, t, metrics.load_peak)

def _demand_performance_method(metrics, t):
    """Compute resilience at a given time t using the average demand method"""
    return _performance(metrics, t, metrics.load[t])

def _fixed_time_window_average_performance_method(metrics, time_window, performance_method):
    """Compute resilience using a fixed time window
    average performance method"""
    if len(time_window) == 0:
        return 1.0
    time_window_duration = _time_window_duration(time_window)
    if time_window_duration == 0.0:
        return 1.0
    average_performance = 0.0
    for t in time_window:
        performance = performance_method(metrics, t)
        average_performance += performance * t.time_period().duration()
    average_performance /= time_window_duration
    return average_performance

def _fixed_time_window_average_performance_median(metrics, time_window):
    """Compute resilience using the fixed time window
    average performance median demand method"""
    if len(time_window) == 0:
        return 1.0
    time_window_duration = _time_window_duration(time_window)
    if time_window_duration == 0.0:
        return 1.0
    times_above_load_median = [t for t in time_window if metrics.load[t] > metrics.load_median]
    if len(times_above_load_median) == 0:
        time_window_load_median = statistics.median([metrics.load[t] for t in time_window])
        times_above_load_median = [t for t in time_window if metrics.load[t] >= time_window_load_median]
    average_performance = sum(_demand_performance_method(metrics, t) * t.time_period().duration()
                   for t in times_above_load_median)
    duration_measured = sum(t.time_period().duration() for t in times_above_load_median)
    average_performance /= duration_measured
    return average_performance

def _fixed_window_wrapper(metrics, time_window):
        """Wrapper to run all fixed window methods"""
        invulnerability_recovery = _fixed_time_window_giachetti_2022(metrics, time_window)
        average_performance_demand = _fixed_time_window_average_performance_method(
            metrics, time_window, _demand_performance_method
        )
        average_performance_peak_demand = _fixed_time_window_average_performance_method(
            metrics, time_window, _peak_demand_performance_method
        )
        average_performance_median_demand = _fixed_time_window_average_performance_median(
            metrics, time_window
        )
        return { 
            "Invulnerability-Recovery":invulnerability_recovery,
            "Average Performance Demand":average_performance_demand,
            "Average Performance Peak Demand":average_performance_peak_demand,
            "Average Performance Median Demand":average_performance_median_demand,
        }

def _fixed_window_method(metrics, time_window):
    """Compute resilience using the fixed window method"""
    results = _fixed_window_wrapper(metrics, time_window)
    return { "Fixed Window Method - "+key:results[key] for key in results }

def _local_shift_method_range(timesteps, start_specified, duration, num_hours=None):
    """Generate earliest and latest disturbance start times for local shift method"""
    horizon_start = timesteps[0].time_period().start()
    horizon_end = timesteps[len(timesteps)-1].time_period().end()
    horizon_duration = (horizon_end - horizon_start).total_seconds() / 3600.0
    if num_hours is None: num_hours = horizon_duration
    hours_to_start_specified = (start_specified - horizon_start).total_seconds() / 3600.0
    start = None
    end = None
    if duration >= horizon_duration:
        start = horizon_start
        end = horizon_start
    elif num_hours > horizon_duration - duration:
        start = horizon_start
        end =  horizon_end - timedelta(hours=duration)
    elif hours_to_start_specified < num_hours / 2.0:
        start = horizon_start
        end = horizon_start + timedelta(hours=num_hours)
    elif hours_to_start_specified > horizon_duration - duration - num_hours/2.0:
        start = horizon_end - timedelta(hours=duration+num_hours)
        end = horizon_end - timedelta(hours=duration)
    else:
        start = start_specified - timedelta(hours=num_hours/2.0)
        end = start_specified + timedelta(hours=num_hours/2.0)
    return start, end

