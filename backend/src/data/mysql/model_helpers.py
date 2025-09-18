import datetime
from . import mysql_microgrid

class ModelDatabaseHelpers(object):

    def __init__(self, table_name):
        """ModelDatabaseHelpers constructor __init__

        Keyword arguments:
        table_name          name of main database table for model
        """
        self._table_name = table_name

    def result_get_by_params(self, grid_id, energy_management_system_id, powerload_id, location_id, startdatetime, enddatetime,
                                disturbance_id=None, disturbance_startdatetime=None, repair_id=None, 
                                extend_timeframe=None, num_shift_hours=None, num_runs=None, method=None):
        """Returns the result id matching input params, if it exists"""
        try:
            if self._table_name == "resilience":
                record = mysql_microgrid.DB.query(
                    """SELECT id
                        FROM resilience
                        WHERE gridId = %s AND energyManagementSystemId = %s AND powerloadId = %s
                                AND locationId = %s AND startdatetime = %s AND enddatetime = %s
                                AND disturbanceId = %s AND disturbanceStartdatetime = %s  AND repairId = %s
                                AND extendTimeframe = %s AND numShiftHours = %s AND numRuns = %s AND method = %s""",
                values=[grid_id, energy_management_system_id, powerload_id, location_id, startdatetime, enddatetime,
                            disturbance_id, disturbance_startdatetime, repair_id, extend_timeframe, num_shift_hours, num_runs, method],
                output_format="dict")
            else:
                record = mysql_microgrid.DB.query(
                    """SELECT id
                        FROM {0}
                        WHERE gridId = %s AND energyManagementSystemId = %s AND powerloadId = %s
                                AND locationId = %s AND startdatetime = %s AND enddatetime = %s""".format(self._table_name),
                values=[grid_id, energy_management_system_id, powerload_id, location_id, startdatetime, enddatetime],
                output_format="dict")
        except Exception as error:
            raise mysql_microgrid.MicrogridDBException("result_get_by_params select failed \n"+str(error))
        return record[0]["id"] if len(record) > 0 else None

    def result_get(self, id, objectFlag=False):
        """Returns a dictionary with metadata for the input id"""
        try:
            record = mysql_microgrid.DB.query(
                """SELECT gridId, energyManagementSystemId, powerloadId, locationId, startdatetime, enddatetime, 
                        computeJobId, runsubmitdatetime, runstartdatetime, runenddatetime, success{0}
                    FROM {1}
                    WHERE id = %s""".format(
                        ", disturbanceId, disturbanceStartdatetime, repairId, extendTimeframe, numShiftHours, numRuns, method" \
                            if self._table_name == "resilience" else "",
                        self._table_name
                    ), values=[id],output_format="dict")[0]
            if not objectFlag:
                for dt in ["startdatetime", "enddatetime", "runsubmitdatetime", "runstartdatetime", "runenddatetime",
                           "disturbanceStartdatetime"]:
                    if dt in record and record[dt] is not None: 
                        record[dt] = record[dt].strftime(mysql_microgrid.DATETIMEFORMAT)
        except Exception as error:
            raise mysql_microgrid.MicrogridDBException("result_get select failed for id="+str(id)+"\n"+str(error))
        return record

    def results_get(self, user_id, method=None):
        """Returns list of dictionaries with metadata for all records for input user"""
        values=[user_id, 1 if self._table_name == "sizing" else 0]
        if method: values.append(method)
        try:
            records = mysql_microgrid.DB.query(
                """SELECT {0}.id, {0}.gridId, grid.name as gridName, {0}.energyManagementSystemId, 
                        energy_management_system.name as energyManagementSystemName,
                        {0}.powerloadId, powerload.name as powerloadName, {0}.locationId, {0}.startdatetime, {0}.enddatetime{1},
                        {0}.computeJobId, {0}.success, {0}.runsubmitdatetime, {0}.runstartdatetime, {0}.runenddatetime
                    FROM {0}
                    JOIN {0}_user
                    ON {0}_user.{0}Id = {0}.id
                    JOIN grid
                    ON grid.id = {0}.gridId
                    JOIN energy_management_system
                    ON energy_management_system.id = {0}.energyManagementSystemId
                    JOIN powerload
                    ON powerload.id = {0}.powerloadId
                    {2}
                    WHERE userId = %s AND grid.isSizingTemplate = %s {3}
                    ORDER BY {0}.id""".format(
                        self._table_name, 
                        ", disturbanceId, disturbance.name as disturbanceName, disturbanceStartdatetime, repair.id as repairId, "
                            + "repair.name as repairName, extendTimeframe, numShiftHours, numRuns, method" 
                            if self._table_name == "resilience" else "",
                        "JOIN repair ON repair.id = repairId\nJOIN disturbance on disturbance.id = disturbanceId"
                            if self._table_name == "resilience" else "",
                        "AND method = %s" if method is not None else ""
                    ), values=values,output_format="dict")
            for record in records:
                record["startdatetime"] = record["startdatetime"].strftime(mysql_microgrid.DATETIMEFORMAT)
                record["enddatetime"] = record["enddatetime"].strftime(mysql_microgrid.DATETIMEFORMAT)
                if self._table_name == "resilience":
                    record["disturbanceStartdatetime"] = record["disturbanceStartdatetime"].strftime(mysql_microgrid.DATETIMEFORMAT)
        except Exception as error:
            raise mysql_microgrid.MicrogridDBException("results_get select failed for user_id="+str(user_id)+"\n"+str(error))
        return records

    def result_add(self, user_id, grid_id, energy_management_system_id, powerload_id, location_id, startdatetime, enddatetime,
                disturbance_id=None, disturbance_startdatetime=None, repair_id=None, extend_timeframe=None, 
                num_shift_hours=None, num_runs=None, method=None):
        """Add a result to the database"""
        mysql_microgrid.user_quota_check(user_id, self._table_name)
        try:
            data_dict={
                "powerloadId": powerload_id,
                "locationId": location_id,
                "gridId": grid_id,
                "energyManagementSystemId": energy_management_system_id,
                "startdatetime":startdatetime,
                "enddatetime":enddatetime,
            }
            if self._table_name == "resilience":
                data_dict.update({
                    "disturbanceId": disturbance_id,
                    "disturbanceStartdatetime": disturbance_startdatetime,
                    "repairId": repair_id,
                    "extendTimeframe": extend_timeframe,
                    "numShiftHours": num_shift_hours,
                    "numRuns": num_runs,
                    "method": method,
                })
            id = mysql_microgrid.DB.insert(table_name=self._table_name, data_dict=data_dict)
        except Exception as error:
            if "Duplicate entry" in str(error) and "for key" and "unique" in str(error):
                raise mysql_microgrid.MicrogridDBException("An analysis has already been run for this set of input parameters. If you wish to rerun it, you must first delete the existing result.")
            raise mysql_microgrid.MicrogridDBException("result_add insert failed\n"+str(error))
        if id == 0:
            return False, "Unable to create new result entry"
        try:
            mysql_microgrid.DB.insert(
                table_name="{0}_user".format(self._table_name), 
                data_dict={ "{0}Id".format(self._table_name):id, "userId":user_id, "permissionId": mysql_microgrid.PERMISSION_WRITE }
            )
        except Exception as error:
            raise mysql_microgrid.MicrogridDBException("result_add insert failed with id = "+str(id)+"\n"+str(error))
        return id

    def compute_job_info_add(self, compute_id, compute_job_id):
        """Add a metrics object to the database"""
        try:
            data_dict = {"computeJobId": compute_job_id, "runsubmitdatetime":datetime.datetime.now()}
            where_dict = {"id": compute_id}
            id = mysql_microgrid.DB.update(table_name=self._table_name, data_dict=data_dict, where_dict=where_dict)
        except Exception as error:
            raise mysql_microgrid.MicrogridDBException("compute_job_info_add insert failed\n"+str(error))
        return id

    def compute_job_starttime_add(self, id):
        """Add starttime for computation"""
        try:
            data_dict = {"runstartdatetime":datetime.datetime.now()}
            where_dict = {"id": id}
            mysql_microgrid.DB.update(table_name=self._table_name, data_dict=data_dict, where_dict=where_dict)
        except Exception as error:
            raise mysql_microgrid.MicrogridDBException("compute_job_starttime_add insert failed\n"+str(error))
        
    def compute_job_status_add(self, id, flag):
        """Add status for computation"""
        if id is None: return
        try:
            data_dict = {"runenddatetime":datetime.datetime.now(), "success":flag}
            where_dict = {"id": id}
            mysql_microgrid.DB.update(table_name=self._table_name, data_dict=data_dict, where_dict=where_dict)
        except Exception as error:
            raise mysql_microgrid.MicrogridDBException("compute_job_status_add insert failed {0} {1}\n{2}".format(id, flag, error))

    def remove(self, id):
        """Delete record from database"""
        try:
            mysql_microgrid.DB.delete(self._table_name, {"id": id})
        except Exception as error:
            raise mysql_microgrid.MicrogridDBException("remove failed for id="+str(id)+"\n"+str(error))
        return True, "Success"
