let resultId = getIdFromURL();
const method = $("#method").text().trim();
const methodType = $("#method-type").text().trim();

async function build() {
  const options = { includeDisturbance: true};
  await initializeComputeForm("resilience_results_get", options);
};

async function displayResults() {
  const resultId = getIdFromURL();
  if (!resultId) return;
  const data = await postData("resilience_data_get", null, {id: resultId});
  const resultsMeta = await getData("resilience_results_get");
  const metadata = resultsMeta.find(m => m["id"] == resultId);
  const numShiftHours = metadata["numShiftHours"];
  renderHealthGauges(data.data, numShiftHours);
}

async function runAnalysis(e) {
  e.preventDefault();
  setButtonsLoading();
  clearHealthGauges();
  if (resultId) {
    await waitForResult("resilience_results_get", resultId, "#compute-message-container",
                        displayResults, resultId);
    resultId = null;
  }
  else if (methodType === "wait") {
    await runAnalysisAndWait(null, "resilience_compute", "resilience_results_get", 
                              "#compute-message-container", displayResults);
  }
  else {
    await runAnalysisAndNoWait(null, "resilience_compute", "compute-message-container");
  }
};

build();