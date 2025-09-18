
componentTypes = {};

build();

async function build() {
  componentTypes = await getData("component_types");
  await initializeComputeForm(null, {isSizing: true});
}

async function runAnalysis(e) {
  e.preventDefault();
  setButtonsLoading();
  await runAnalysisAndNoWait(null, "sizing_compute", "compute-message-container");
};