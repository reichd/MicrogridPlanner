let mode = null; 
let records = [];
let quotas = {};
let componentTypes = {};
let grids = [];
let selectedComponents = {};

build();
addModalEvents();

// Entrypoint to load data and build the page
async function build() {
  mode = detectModeFromURL();
  const isDisturbance = mode === 'disturbance';

  // Fetch data for this mode
  records = await getData(isDisturbance ? "resilience_disturbances_get" : "resilience_repairs_get");
  componentTypes = await getData("component_types");
  quotas = await getData("quota");
  grids = await getData("grids_get");

  buildList();
  buildNewInputs();
  buildMicrogridSelection();
  $("#full-screen-loader").hide();
}

// Detect disturbance or repair from URL path or body data attribute
function detectModeFromURL() {
  // First check if mode is set in the data attribute
  const rootElement = document.getElementById('disturbance-repair-root');
  if (rootElement && rootElement.dataset.mode) {
    return rootElement.dataset.mode;
  }
  // Fall back to URL
  return window.location.pathname.includes("disturbance") ? "disturbance" : "repair";
}

function handleUserQuotaCheck() {
  userQuotaCheck(records.length, mode, quotas[mode]);
}

// Build the component type inputs for the new record modal
function buildNewInputs() {
  Object.keys(componentTypes).forEach(ctId => {
    const maxVal = mode === 'disturbance' ? 1 : "";
    const inputHtml = createNumberInput({ id: ctId, value: "", minVal: 0, maxVal: maxVal });
    $("#new-component-types").append(`
      <label for="ct-${ctId}" class="form-label">${componentTypes[ctId].description}</label>
      ${inputHtml}
    `);
  });
}

// Build the dropdown inside create modal of available microgrids
function buildMicrogridSelection() {
  const selectEl = $('#microgrid-select');
  selectEl.empty();
  selectEl.append('<option value="" selected disabled>Select a microgrid</option>');
  grids.forEach(grid => {
    if (grid.components.length > 0) {
      selectEl.append(`<option value="${grid.id}">${grid.name}</option>`);
    }
  });
}

// Build the list of records (repairs or disturbances)
function buildList() {
  const plural = records.length === 0 || records.length > 1 ? "s" : "";
  $("#list").empty();

  records.length === 0 ? $('#no-records-message').show() : $('#no-records-message').hide();

  $("#title").text(`${records.length} ${mode.charAt(0).toUpperCase() + mode.slice(1)}${plural}`);
  const method = $('#method').text();
  const $card = $(`<div class="widget"></div>`);

  records.forEach(record => {
    const grid = grids.find(g => g.id === record.gridId);

    createDisturbanceRepairWidget(record, grid, method, mode, componentTypes, "#list", true);
    $("#list").children(":not(.widget)").wrapAll($card);
    
    $(`#${record.id}-open-confirm-delete-btn`).on('click', (e) => {
      e.preventDefault();
      handleOpenConfirmDelete(e, record);
    });
  });
}

// Create new record modal (repair or disturbance)
async function create(e) {
  e.preventDefault();
  const formVals = getValuesFromForm("#new-form");
  const attributes = {};
  selectedComponents = {};

  Object.keys(componentTypes).forEach(ctId => {
    const valStr = $(`#ct-${ctId}`).val();
    if (valStr !== "") {
      const val = parseFloat(valStr);
      if (!isNaN(val)) {
        attributes[ctId] = val;

        const grid = grids.find(g =>
          g.components.some(c => c.typeId.toString() === ctId.toString())
        );
        if (grid) {
          const comp = grid.components.find(c => c.typeId.toString() === ctId.toString());
          if (comp) {
            selectedComponents[comp.id] = mode === "disturbance"
              ? { quantity: 1, value: val, typeId: comp.typeId }
              : { value: val, typeId: comp.typeId };
          }
        }
      }
    }
  });

  if (mode === "disturbance") {
    Object.values(selectedComponents).forEach(c => {
      if (!c.value) c.value = 0.0;
    });
  }
  const data = {
    name: formVals.name,
    description: formVals.description,
    attributes,
    selectedComponents: Object.keys(selectedComponents).length ? selectedComponents : null,
    gridId: formVals.gridId
  };

  try {
    const res = await postData(
      mode === "disturbance" ? "resilience_disturbances_add" : "resilience_repairs_add",
      null,
      data
    );
    if (res?.processed) {
      $('#new-modal').modal('hide');
      displayToastMessage(`New ${mode} created!`);
      build();
    } else {
      displayToastMessage(res?.status_message || res?.error || `Error creating ${mode}.`);
    }
  } catch (err) {
    console.error(`Error creating ${mode}:`, err);
    displayToastMessage(`Error creating ${mode}. Please try again.`);
  }
}

// Open confirm modal and set up deletion
async function handleOpenConfirmDelete(e, record) {
  openConfirmDeleteModal(e, record, deleteRecord);
  const results = await getData("resilience_results_get");
  const recordResults = results.filter(r => r[`${mode}Id`] === record.id);
  if (recordResults.length > 0) {
    createRelatedDataList(
      recordResults, 
      `The following resilience results will also be deleted:`, 
      "id"
    )
  }

  $('#confirm-delete-modal').modal('show');
}

// Delete the given record
async function deleteRecord(e) {
  const id = $(e.target).data('id');
  const res = await postData(
    mode === 'disturbance' ? "resilience_disturbances_remove" : "resilience_repairs_remove",
    null,
    { id }
  );

  if (!res.error) {
    closeConfirmDeleteModal(e);
    $('#confirm-delete-modal').modal('hide');
    displayToastMessage(`${mode} successfully deleted.`);
    build();
  }
}
