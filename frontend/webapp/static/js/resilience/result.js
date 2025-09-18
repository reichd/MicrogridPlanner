computeId = null;
energyManagementSystems = [];

build();

async function build() {
  computeId = $("#compute-id").text();
  const urlParams = new URLSearchParams(window.location.search);
  const hasAll = urlParams.has("all");  
  const method = $("#method").text();
  const resultsRes = await postData("resilience_results_get", null, {id: computeId});
  const metadata = resultsRes.data
  const data = await postData("resilience_data_get", null, {id: computeId});
  const componentTypes = await getData("component_types");
  const startDate = new Date(metadata["startdatetime"]);
  const endDate = new Date(metadata["enddatetime"]);
  const startDateString = getDateStringReadable(startDate) + " " + getTimeString({date: startDate, withSeconds: false});
  const endDateString = getDateStringReadable(endDate) + " " + getTimeString({date: endDate, withSeconds: false});
  const disturbanceId = metadata["disturbanceId"];
  const disturbanceStartDate = new Date(metadata["disturbanceStartdatetime"]);
  const disturbanceStartDateString = getDateStringReadable(disturbanceStartDate) + " " + getTimeString({date: disturbanceStartDate, withSeconds: false});
  const repairId = metadata["repairId"];
  const timeframe = startDateString + " - " + endDateString;
  const loadId = metadata["powerloadId"];
  const gridId = metadata["gridId"];
  const energyManagementSystemId = metadata["energyManagementSystemId"];
  const extendTimeframe = metadata["extendTimeframe"]
  const numShiftHours = metadata["numShiftHours"]
  const numRuns = metadata["numRuns"]
  const gridRes = await postData("grids_get", null, {"id": gridId});
  const disturbanceRes = await postData("resilience_disturbances_get", null, {"id": disturbanceId});
  const repairRes = await postData("resilience_repairs_get", null, {"id": repairId});
  const energyManagementSystems = await getData("energy_management_systems");
  const locationRes =  await postData("locations_get", null, {id: metadata["locationId"]});
  const location = locationRes.data;
  let powerloadRes = await postData("powerloads_get", null, {id: loadId});
  const energyManagementSystem = energyManagementSystems.find(ems => ems.id == energyManagementSystemId);
  powerloadRes.data.data = powerloadRes.data.data.filter(d => {
    const date = new Date(d.middatetime);
    return date >= startDate && date <= endDate;
  });
  createPowerloadWidget(powerloadRes.data, "#powerload", timeframe, false);
  createEnergyManagementSystemWidget(energyManagementSystem, "#energy-management-system", "Energy Management System");
  createGridWidget(gridRes.data, "#grid", false);
  createDisturbanceRepairWidget(disturbanceRes.data, gridRes.data, method, "disturbance", componentTypes, "#disturbance-card", false);
  createDisturbanceRepairWidget(repairRes.data, gridRes.data, method, "repair", componentTypes, "#repair-card", false);


  $("#full-screen-loader").hide();
  
  if (hasAll) {
    $("#location-name").show();
    $("#disturbance").show();
    $("#disturbance-start").show();
    $("#repair").show();
    $("#extend-timeframe").show();
    $("#num-shift-hours").show();
    $("#num-runs").show();
    $("#metrics").show();
    
    $("#location-name").append(`
      <b>Location: </b>${location.name}, ${location.region}, ${location.country}
    `);
    $("#disturbance").append(`
      <b>Disturbance: </b><a href="../../disturbances/${disturbanceId}/">${disturbanceRes.data.name}</a>
    `);
    $("#disturbance-start").append(`
      <b>Disturbance Start: </b>${disturbanceStartDateString}
    `);
    $("#repair").append(`
      <b>Repair: </b><a href="../../repairs/${repairId}/">${repairRes.data.name}</a>
    `);
    $("#extend-timeframe").append(`
      <b>Extend Timeframe: </b>${extendTimeframe}
    `);
    $("#num-shift-hours").append(`
      <b>Num Shift Hours: </b>${numShiftHours}
    `);
    $("#num-runs").append(`
      <b>Num Runs: </b>${numRuns}
    `);

    let metrics = "<table>"
    jQuery.each(data.data, function(key, value) {
      metrics += "<tr><td>" + key + "</td><td>" + value + "</td></tr>"
    });
    $("#metrics").append(`
      ${metrics}
    `);
  } else {
    $("#location-name").hide();
    $("#disturbance").hide();
    $("#disturbance-start").hide();
    $("#repair").hide();
    $("#extend-timeframe").hide();
    $("#num-shift-hours").hide();
    $("#num-runs").hide();
    $("#metrics").hide();
  }

  $("#results-container").removeClass("results-hidden");

  createRunParametersWidget(location, metadata);
  renderHealthGauges(data.data, numShiftHours);  
};