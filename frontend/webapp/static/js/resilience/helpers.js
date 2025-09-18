// Group component data by type for a given record
function groupComponentsByType(record, grid, mode) {
  const map = {};
  if (!grid) return map;
  grid.components.forEach(comp => {
    map[comp.typeId] = {
      typeId: comp.typeId,
      totalAvailable: comp.quantity,
      quantity: 0,
      value: 0.0
    };
  });

  if (record.selected_components) {
    Object.entries(record.selected_components).forEach(([compId, data]) => {
      const comp = grid.components.find(c => c.id == compId);
      if (comp && map[comp.typeId]) {
        if (mode === 'disturbance') {
          map[comp.typeId].quantity = data.quantity || 0;
          map[comp.typeId].value = data.value || 0.0;
        } else {
          map[comp.typeId].value = data.value || 0;
        }
      }
    });
  }

  return map;
}

function buildComponentListHTML(componentsByType, componentTypes, mode, grid, selectedComponents) {
  // Sort components alphabetically by name, then list each component individually for both modes
  return grid.components
    .sort((a, b) => a.name.localeCompare(b.name))
    .map(comp => {
    // For repair, get value from selectedComponents by component id
    let value = 0;
    if (mode === 'repair' && selectedComponents && selectedComponents[comp.id]) {
      value = selectedComponents[comp.id].value || 0;
    } else if (componentsByType[comp.typeId]) {
      value = componentsByType[comp.typeId].value || 0;
    }
    const typeDesc = componentTypes[comp.typeId]?.description || '';
    const imageName = componentTypes[comp.typeId]?.parameterName || typeDesc.replace(/\s+/g, '');
    let valueText = '';
    if (mode === 'repair') {
      valueText = `Repair time: ${value} hrs`;
    } else {
      // For disturbance, show quantity for this component
      let compData = null;
      if (grid && grid.selected_components && grid.selected_components[comp.id]) {
        compData = grid.selected_components[comp.id];
      } else if (componentsByType[comp.typeId] && componentsByType[comp.typeId].selected_components && componentsByType[comp.typeId].selected_components[comp.id]) {
        compData = componentsByType[comp.typeId].selected_components[comp.id];
      } else if (componentsByType[comp.typeId] && componentsByType[comp.typeId].quantity !== undefined) {
        compData = componentsByType[comp.typeId];
      }
      let quantity = 0;
      if (selectedComponents && selectedComponents[comp.id] && selectedComponents[comp.id].quantity !== undefined) {
        quantity = selectedComponents[comp.id].quantity;
      }
      valueText = `${quantity} of ${comp.quantity} non-operational`;
    }
    return `
      <div class="d-flex justify-content-start align-items-end">
        <div class="icon-quantity-container">
          <img src="/static/images/${imageName}.png" class="mb-1">
        </div>
        <div class="text">
          <span class="fw-bold text-secondary mb-1 tooltip-on-hover" style="font-size: 0.8rem; line-height: 1.1;" title="${comp.name}">${comp.name}</span>
          <div class="text-secondary resilience-text-secondary tooltip-on-hover" style="font-size: 0.8rem; line-height: 1.1;" title="${typeDesc}">${typeDesc}</div>
          <div class="text-secondary tooltip-on-hover" style="font-size: 0.8rem; line-height: 1.1; padding-right: 5px;" title="${valueText}">${valueText}</div>
        </div>
      </div>
    `;
  }).join('');
}

function createDisturbanceRepairWidget(record, grid, method, mode, componentTypes, elId, showDelete = false) {
  const componentsByType = groupComponentsByType(record, grid, mode);
  // For repair, sum values from selected_components by component id
  let summary = 0;
  if (mode === "repair" && record.selected_components) {
    summary = Object.values(record.selected_components).reduce((sum, c) => sum + (c.value || 0), 0);
  } else if (mode === "disturbance" && record.selected_components) {
    // Sum quantity for each affected component (by component id)
    summary = Object.values(record.selected_components).reduce((sum, c) => sum + (c.quantity || 0), 0);
  } 
  const summaryText = mode === "repair"
    ? `${summary} hour${summary !== 1 ? 's' : ''} total repair time`
    : `${summary} component${summary !== 1 ? 's' : ''}`;

  const componentHtml = buildComponentListHTML(componentsByType, componentTypes, mode, grid, record.selected_components);
  const viewLinkHtml = `<a href="/tools/resilience/${method}/${mode}s/${record.id}/" class="card-link">View</a>`;
  if (showDelete) {
    // Management page card (with delete button)
    const deleteButtonHtml = `<a href="#" id="${record.id}-open-confirm-delete-btn" data-name="${mode}s" class="card-link float-end delete">Delete</a>`;
    $(elId).append( `
      <h5>${record.name}</h5>
      <div class="card-body">
        <span class="text-secondary">${summaryText}</span>
        <div class="card-text description">${record.description}</div>
        <div class="widget-data components-mini-list">${componentHtml}</div>
        <div>
          <a href="/tools/resilience/${method}/${mode}s/${record.id}/" class="card-link float-start">View</a>
          ${deleteButtonHtml}
        </div>
      </div>
    `);
  } else {
    $(elId).append(`
      <h5>${toTitleCase(mode)}</h5>
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-center">
          <h5 class="card-title mb-0 flex-grow-1" style="flex-basis: 75%;">${record.name}</h5>
          <div style="flex-basis: 25%;" class="text-end">${viewLinkHtml}</div>
        </div>
        <span class="text-secondary">${summaryText}</span>
        <div class="card-text description">${record.description}</div>
        <div class="widget-data components-mini-list">${componentHtml}</div>
      </div>
    `);
  }
}

// Configurable cutoffs for health gauge status
const healthGaugePercentages = {
  good: 80,   // percent >= good is 'Good'
  okay: 61,   // percent >= okay is 'Okay', below is 'Poor'
  // percent < okay is 'Poor'
};

function createHealthGaugeWidget(value) {
  let percent = Math.max(0, Math.min(1, value)) * 100;
  let color = "#e74c3c"; // red
  let status = "Poor";
  if (percent >= healthGaugePercentages.good) { color = "#27ae60"; status = "Good"; }
  else if (percent >= healthGaugePercentages.okay) { color = "#f1c40f"; status = "Okay"; }
  let displayValue = percent.toFixed(2);
  // SVG for gauge graphic
  const size = 117;
  const stroke = 13; 
  const radius = (size - stroke) / 2;
  const center = size / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - percent / 100);
  return `
    <div class="radial">
      <div class="gauge-radial-container">
        <svg width="${size}" height="${size}" class="gauge-radial-svg">
          <circle
            class="gauge-bg"
            cx="${center}"
            cy="${center}"
            r="${radius}"
            stroke="#e0e0e0"
            stroke-width="${stroke}"
            fill="none"
          />
          <circle
            class="gauge-arc"
            cx="${center}"
            cy="${center}"
            r="${radius}"
            stroke="${color}"
            stroke-width="${stroke}"
            fill="none"
            stroke-linecap="round"
            stroke-dasharray="${circumference}"
            stroke-dashoffset="${offset}"
            transform="rotate(-90 ${center} ${center})"
          />
          <text x="50%" y="54%" text-anchor="middle" dominant-baseline="middle" class="gauge-radial-value">${displayValue}</text>
        </svg>
      </div>
      <div class="gauge-status-label mt-2" style="color:${color}">${status}</div>
    </div>
  `;
}

function getHealthGaugeCardTitleAndDesc(metricKey, numShiftHours) {
  const keyLower = metricKey.toLowerCase();
  let title = metricKey;
  let desc = '';
  let localHours = numShiftHours;
  if (keyLower.includes('local')) {
    // Extract the window size (hours) from the key, due to multiple local shifts cases. So we can extract the default + user input value
    let match = metricKey.match(/local\s*\((\d+)\)/i);
    if (match && match[1]) {
      localHours = match[1];
    }
    title = 'Local Shift Method';
    desc = 'Analyzed at a specific time based on user input.';
  } else if (keyLower.includes('global')) {
    title = 'Global Shift Method';
    desc = 'Analyzed based on every point in the timeframe.';
  } else if (keyLower.includes('fixed window')) {
    title = 'Fixed Window Method';
    desc = 'Based on a specific time in the simulation window.';
  }
  return { title, desc, localHours };
}

function createHealthGaugeCardWidget(metricName, value, descOverride = null, numShiftHours = null) {
  // Renders a health gauge card. For local cards, shows a subtitle with the window size.
  let desc = descOverride;
  let isLocal = metricName.toLowerCase().includes('local');
  if (desc === null) {
    const t = metricName.toLowerCase();
    if (t.includes('local')) desc = 'Analyzed at a specific time based on user input.';
    else if (t.includes('global')) desc = 'Analyzed based on every point in the timeframe.';
    else if (t.includes('fixed window')) desc = 'Based on a specific time in the simulation window.';
    else desc = '';
  }
  return `
    <div class="widget">
      <div class="card grid-widget" style="width: 100%;">
        <div class="card-body d-flex flex-column align-items-center justify-content-space-between h-100">
          <h5 style="background:none !important; color:#222 !important;">${metricName}</h5>
          ${isLocal && numShiftHours ? `<h6 class="text-secondary"><span style="font-weight: bold">${numShiftHours}</span> Hour Window</h6>` : '</br>'}
          <div class="mb-2 mt-2 text-secondary" style="text-align:center !important;">${desc}</div>
          <div class="d-flex justify-content-center my-3 w-100">
            ${createHealthGaugeWidget(value)}
          </div>
        </div>
      </div>
    </div>
  `;
}

const clearHealthGauges = () => {
    $("#health-gauges").empty();
    $("#results-container").hide();
}

function createRunParametersWidget(locationData, metadata) {
  if ($('#run-parameters-card').length) {
    const params = {
      location: formatLocationString(locationData),
      disturbanceStart: metadata.disturbanceStartdatetime,
      extendTimeframe: metadata.extendTimeframe,
      numShiftHours: metadata.numShiftHours,
      numRuns: metadata.numRuns
    };
    $('#run-parameters-card').html(`
    <div class="widget" style="height: 100%;">
      <h5>Additional Run Parameters</h5>
      <div class="card grid-widget" style="width: 100%;">
        <div class="card-body d-flex flex-column align-items-start justify-content-center h-100">
          <ul class="list-unstyled mb-0">
            <li><b>Location:</b> ${params.location}</li>
            <li><b>Disturbance Start:</b> ${params.disturbanceStart}</li>
            <li><b>Extend Timeframe:</b> ${params.extendTimeframe}</li>
            ${params.numShiftHours > 0 ? `<li><b>Num Shift Hours:</b> ${params.numShiftHours}</li>` : ''}
            ${params.numRuns == 1 ? '' : `<li><b>Num Runs:</b> ${params.numRuns}</li>`}
          </ul>
        </div>
      </div>
    </div>`
  );
  }
}

//Bring locationData in separately so we can format before it hits the function
function formatLocationString(locationData) {
  return `${locationData.name}, ${locationData.region}, ${locationData.country}`;
}

function renderHealthGauges(data, numShiftHours) {
  if (!data || numShiftHours === null || numShiftHours === undefined) return '';
  
  const gauges = { fixedWindow: [], local: [], global: [] };
  
  Object.entries(data).forEach(([key, value]) => {
    const keyLower = key.toLowerCase();
    if (keyLower.includes('median demand')) {
      const { title, desc, localHours } = getHealthGaugeCardTitleAndDesc(key, numShiftHours);
      if (keyLower.includes('local')) {
        gauges.local.push({ title, desc, value, localHours });
      } else if (keyLower.includes('fixed window')) {
        gauges.fixedWindow.push({ title, desc, value });
      } else if (keyLower.includes('global')) {
        gauges.global.push({ title, desc, value });
      }
    }
  });

  // Sort local gauges by ascending hours in case doesnt come in order from backend
  gauges.local.sort((a, b) => a.localHours - b.localHours);
  //spread arrays into individual elements
  if ($('#health-gauges').length) {
    const htmlString = [
      ...gauges.fixedWindow.map(g => createHealthGaugeCardWidget(g.title, g.value, g.desc)),
      ...gauges.local.map(g => createHealthGaugeCardWidget(g.title, g.value, g.desc, g.localHours)),
      ...gauges.global.map(g => createHealthGaugeCardWidget(g.title, g.value, g.desc))
    ].join('');
    
    $('#health-gauges').html(htmlString);
  }
  $("#results-container").removeClass("results-hidden");
  $("#results-container").show();
}