
build();

async function build() {
  const method = $("#method").text();
  const results = await postData("resilience_results_get",null,{method:method});
  await mapResultsData(results.data, "resilience");
}