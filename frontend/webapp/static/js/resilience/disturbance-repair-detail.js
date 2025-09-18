let mode = null; // 'repair' or 'disturbance'
let record = null;
let componentTypes = {};
let grids = [];
let selectedComponents = {};

build();

async function build() {
  mode = detectModeFromURL();
  const id = getRecordIdFromURL();
  record = await loadData(id);
  if (!record) return;

  setupForm(record);
  setupSelectedComponents(record);
  buildMicrogridComponents();
  
  // Set the instruction text based on the mode and method
  const method = $("#method").text().trim();
  const instruction = {
    repair: 'Select components from an existing microgrid and set their repair times',
    disturbance: method === 'stochastic' 
      ? 'Select components from an existing microgrid and set their probability of failure'
      : 'Select components from an existing microgrid'
  };
  
  document.getElementById('instruction-text').innerText = instruction[mode] || '';

  if (record.gridId) $('#microgrid-components').show();
  $('#full-screen-loader').hide();
}

function detectModeFromURL() {
  return window.location.pathname.includes("disturbance") ? "disturbance" : "repair";
}

function getRecordIdFromURL() {
  const parts = window.location.pathname.split('/');
  return parseInt(parts[parts.length - 2]);
}

async function loadData(id) {
  const [items, types, allGrids] = await Promise.all([
    getData(mode === "disturbance" ? "resilience_disturbances_get" : "resilience_repairs_get"),
    getData("component_types"),
    getData("grids_get")
  ]);
  componentTypes = types;
  grids = allGrids;
  return items.find(item => item.id === id);
}

function setupForm(r) {
  $('#name').val(r.name);
  $('#description').val(r.description);
  const grid = grids.find(g => g.id === r.gridId);
  if (grid) $('#grid-name').text(grid.name);
}

function setupSelectedComponents(r) {
  selectedComponents = {};
  const grid = grids.find(g => g.id === r.gridId);
  if (!grid || !r.selected_components) return;

  Object.entries(r.selected_components).forEach(([id, data]) => {
    selectedComponents[id] = mode === "disturbance"
      ? {
          quantity: data.quantity ?? 0,
          value: data.value ?? 0.0,
          typeId: data.typeId
        }
      : {
          value: parseInt(data.value) || 0,
          typeId: data.typeId
        };
  });
}

function getComponentSelection(comp) {
  return selectedComponents[comp.id] || {
    typeId: comp.typeId,
    ...(mode === "disturbance" ? { quantity: 0, value: 0.0 } : { value: 0 })
  };
}

function buildMicrogridComponents() {
  if (!record || !record.gridId) return;
  const grid = grids.find(g => g.id === record.gridId);
  if (!grid) return;

  const method = $('#method').text();
  const isStochastic = method !== 'deterministic' && mode === "disturbance";

  const componentsByType = {};
  grid.components.forEach(comp => {
    if (!componentsByType[comp.typeId]) {
      componentsByType[comp.typeId] = { type: comp.typeDescription, components: [] };
    }
    componentsByType[comp.typeId].components.push(comp);
  });

  $('#components-accordion-left').empty();
  $('#components-accordion-right').empty();

  let counter = 0;
  Object.values(componentsByType).forEach(typeGroup => {
    typeGroup.components.forEach(comp => {
      counter++;
      const currentSelection = getComponentSelection(comp);
      const typeDescription = componentTypes[comp.typeId]?.description || '';
      const parameterName = componentTypes[comp.typeId]?.parameterName || typeDescription.replace(/\s+/g, '');
      const inputFields = mode === "disturbance"
        ? buildDisturbanceInputs(comp, currentSelection, isStochastic)
        : buildRepairInputs(comp, currentSelection);

      const componentHtml = `
        <div class="accordion-item">
          <div class="component-header">
            <div class="d-flex justify-content-start align-items-end">
              <div class="icon-quantity-container">
                <img src="/static/images/${parameterName}.png">
              </div>
              <div class="text">
                <span class="name">${comp.name}</span><br>
                <span class="text-secondary">${comp.typeDescription}</span>
              </div>
            </div>
            ${inputFields}
          </div>
          <div class="accordion-header" id="component-${comp.id}-heading">
            <div class="accordion-button collapsed" type="button" data-bs-toggle="collapse"
                 data-bs-target="#component-${comp.id}-collapse" aria-expanded="false"
                 aria-controls="component-${comp.id}-collapse">
              View specs
            </div>
          </div>
          <div id="component-${comp.id}-collapse" class="accordion-collapse collapse"
               aria-labelledby="component-${comp.id}-heading">
            <div class="accordion-body">
              <div class="spec-list d-flex align-content-around flex-wrap">
                ${buildSpecList(componentTypes[comp.typeId].specs.map(spec => ({
                  name: spec.name,
                  value: comp.attributes ? comp.attributes[spec.id] : null,
                  parameterType: spec.parameterType
                })))}
              </div>
            </div>
          </div>
        </div>
      `;
      $(`#components-accordion-${counter % 2 === 0 ? 'right' : 'left'}`).append(componentHtml);
    });
  });
}

function buildRepairInputs(comp, selection) {
  return `
    <div class="component-qty-rmv-container d-flex justify-content-between">
      <div class="name-display" id="display-component-${comp.id}-repair-time">
        <div class="d-flex align-items-center mt-2">
          <span class="text-muted me-2">Repair time (hours):</span>
          <div class="input-group me-3" style="width: 75px;">
            <input type="number" class="form-control component-repair-time"
              data-component-id="${comp.id}" data-type-id="${comp.typeId}"
              value="${Math.round(selection.value)}" min="0" step="1"
              onchange="handleComponentRepairTimeChange(event)">
          </div>
        </div>
      </div>
    </div>
  `;
}

function buildDisturbanceInputs(comp, selection, isStochastic) {
  return `
    <div class="component-qty-rmv-container d-flex justify-content-between">
      <div class="name-display" id="display-component-${comp.id}-quantity">
        <span>Quantity Available: ${comp.quantity}</span>
        <div class="d-flex align-items-center mt-2">
          <span class="text-muted me-2">Select quantity affected:</span>
          <div class="input-group me-3" style="width: 75px;">
            <select class="form-select component-quantity"
              data-component-id="${comp.id}" data-type-id="${comp.typeId}"
              onchange="handleComponentQuantityChange(event)">
              ${Array.from({ length: comp.quantity + 1 }, (_, i) => 
                `<option value="${i}" ${selection.quantity === i ? 'selected' : ''}>${i}</option>`
              ).join('')}
            </select>
          </div>
          ${isStochastic ? `
            <span class="text-muted me-2">Prob. of failure:</span>
            <div class="input-group" style="width: 75px;">
              <select class="form-select component-probability"
                data-component-id="${comp.id}"
                onchange="handleComponentProbabilityChange(event)">
                ${Array.from({ length: 11 }, (_, i) => 
                  `<option value="${i / 10}" ${selection.value === i / 10 ? 'selected' : ''}>${i / 10}</option>`
                ).join('')}
              </select>
            </div>
          ` : ''}
        </div>
      </div>
    </div>
  `;
}

function handleComponentRepairTimeChange(e) {
  const { componentId, typeId } = e.target.dataset;
  const value = Math.max(0, Math.round(parseFloat(e.target.value) || 0));
  selectedComponents[componentId] = {
    ...(selectedComponents[componentId] || {}),
    value,
    typeId
  };
}

function handleComponentQuantityChange(e) {
  const { componentId, typeId } = e.target.dataset;
  const quantity = parseInt(e.target.value) || 0;

  if (!selectedComponents[componentId]) {
    selectedComponents[componentId] = { quantity, typeId, value: 0.0 };
  } else {
    selectedComponents[componentId].quantity = quantity;
    selectedComponents[componentId].typeId = typeId;
  }
}

function handleComponentProbabilityChange(e) {
  const { componentId, typeId } = e.target.dataset;
  let value = parseFloat(e.target.value);
  
  if (!selectedComponents[componentId]) {
    selectedComponents[componentId] = {
      quantity: 0,
      value: 0.0,
      typeId: typeId
    };
  }
  
  selectedComponents[componentId].value = Math.min(1, Math.max(0, value));
}

async function saveRecord(e) {
  e.preventDefault();
  const formId = mode === "disturbance" ? "#disturbance-form" : "#repair-form";
  const formVals = getValuesFromForm(formId);
  formVals.id = record.id;

  const nameDescEndpoint = mode === "disturbance"
    ? "resilience_disturbances_update_name_description"
    : "resilience_repairs_update_name_description";

  const componentsEndpoint = mode === "disturbance"
    ? "resilience_disturbances_update_components"
    : "resilience_repairs_update_components";

  const nameRes = await postData(nameDescEndpoint, formId, formVals);
  if (nameRes.error) return displayToastMessage("Error saving name and description");

  const compRes = await postData(componentsEndpoint, null, {
    id: record.id,
    selectedComponents
  });
  if (compRes.error) return displayToastMessage("Error saving component selection");

  record.name = formVals.name;
  record.description = formVals.description;
  record.selected_components = selectedComponents;

  displayToastMessage("All changes saved successfully!");
}
