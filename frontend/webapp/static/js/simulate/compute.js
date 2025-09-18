let resultId = getIdFromURL();
let componentTypes = {};

const build = async () => {
  componentTypes = await getData("component_types");
  await initializeComputeForm("simulate_results_get",{});
};

const displayResults = async(resultId) => {
  const metricsRes = await postData("simulate_metrics_get", null, {id: resultId});
  const filename = createGraphFilenameFromForm($("#form"));
  buildAllApexCharts(metricsRes.data.output, componentTypes, filename);
  displayStats(metricsRes.data.summary_stats);
}

// Handles button click
async function runAnalysis(e) {
  e.preventDefault();
  setButtonsLoading();
  clearSimulationOutput();
  if (resultId) {
    await waitForResult("simulate_results_get", resultId, "#compute-message-container",
                        displayResults, resultId);
    resultId = null;
  }
  else {
    await runAnalysisAndWait(null, "simulate_compute", "simulate_results_get", 
                              "#compute-message-container", displayResults);
  }
};

build();