// Map summary stat keys to image URL
const statsToImageUrl = {
  "Battery": "/static/images/Battery.png",
  "DieselGenerator": "/static/images/DieselGenerator.png",
  "SolarPhotovoltaicPanel": "/static/images/SolarPhotovoltaicPanel.png",
  "WindTurbine": "/static/images/WindTurbine.png",
  "Unmet Energy": "/static/images/unmet_energy.png",
  "Diesel Generator Wet Stacking (hours)": "/static/images/total_diesel_wet_stacking_hours.png",
  "CO2 (pounds)": "/static/images/total_co2_pounds.png",
  "Diesel (gallons)": "/static/images/total_diesel_gallons.png",
  "Unmet Power (hours)": "/static/images/unmet_power_hours.png",
};

// Creates the component spec list
const buildSpecList = (list) => {
  return (`
    <div class="spec-list d-flex align-content-around flex-wrap">
      ${list.map(item => {
        let displayValue = item.value;
        if (item.parameterType === "boolean") {
          displayValue = item.value === 1 ? "yes" : "no";
        }
        return `<div class="spec-list-item"><b>${item.name}:</b> <span>${displayValue}</span></div>`;
      }).join('')}
    </div>
  `);
};

function toTitleCase(str) {
    return str.replace(/(?:^|\s)\w/g, function(match) {
        return match.toUpperCase();
    });
}

// Takes a component and builds the header (Image with title and component type)
const buildComponentHeader = (options) => {
  const { component, showQuantity } = options;
  return (`
    <div class="d-flex justify-content-start align-items-end">
      <div class="icon-quantity-container">
        <img src="/static/images/${component.typeName}.png"/>
        ${showQuantity && component.quantity ? `<span>x${component.quantity}</span>` : ""}
      </div>
      <div class="text">
        <span class="name">${component.name}</span>
        <br/>
        <span class="text-secondary">${component.typeDescription}</span>
      </div>
    </div>
  `);
}

// Gets value of cookie for input name
const getCookie = (name) => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

const clearSession = () => {
  alert("Your authentication token has expired. You will now be redirected to login again.")
  window.location.replace(window.location.origin + URLS.clear_session);
};

// Performs get request and attaches JWT from cookie
// URL: The api endpoint URL (ex: /api/components/json)
// dataName: the name of the data to append/update to global data object (ex: "grids" will be appended to data.grids)
// type: request type (ex: "POST")
// postData: any data object to add to the request body
const apiReq = async (url, type, postData) => {
  // Get JWT from cookie
  const jwt = getCookie("jwt")
  const responseObj = {error: false, data: null};
  const defaultErrorMessage = "There was an error with the request.";

  try {
    const res = await $.ajax({
      async: true,
      url: URLS.server + url,
      type,
      beforeSend: (request) => {
        request.setRequestHeader("Authorization", "Bearer " + jwt);
      },
      data: JSON.stringify(postData),
      contentType:"application/json; charset=utf-8",
      dataType: "json"
    });

    if (res.processed) {
      responseObj.data = res.data;
      responseObj.processed = true;
      responseObj.status_message = res.status_message;
    }
    else {
      responseObj.error = res.status_message ? res.status_message : defaultErrorMessage;
      responseObj.processed = false;
      responseObj.status_message = res.status_message;
    }
  }
  catch (err) {
    if (err) {
      if (err.responseJSON) {
        if (err.responseJSON.message) {
          if (err.responseJSON.message === "API authentication token expired. Please log in again.") {
            return clearSession();           
          }
          else {
            responseObj.error = err.responseJSON.message;
          }
        }
      }
      else if (err && err.statusText.includes("NetworkError")) {
        responseObj.error = "Could not establish API connection (network)";
      }
      else if (err && err.status == 403) {
        responseObj.error = "Could not establish API connection (forbidden)";
      }
      else if (err && err.statusText) {
        responseObj.error = "API error: ".concat(err.statusText);
      }
      else {
        responseObj.error = "API error (see console log for details)";
      }
    }
    else {
      responseObj.error = defaultErrorMessage.concat(" API error (see console log for details)");
    }
    responseObj.processed = false;
  }

  return responseObj;
}

// Sends a POST request and returns the response
async function postData(dataName, elementId, data) {
  $("#loader").show();

  const res = await apiReq(URLS.api[dataName], "POST", data);
  
  if (res.error) {
    if (elementId) {
      openAlert("danger", elementId, res.error);
    }
    else {
      openAlert("danger", "#tool-error", res.error);
    }
  }
  $("#loader").hide();
  return res;
}

// Sends a GET request and returns the response
async function getData(dataName, elementId) {
  $("#loader").show();
  const res = await apiReq(URLS.api[dataName], "GET");
  if (res.error) {
    openAlert("danger", "#tool-error", res.error);
  }
  $("#loader").hide();
  return res.data;
}

// Opens modal id #confirm-delete-modal and adds item ID to the delete button
const openConfirmDeleteModal = (e, item, handleDelete) => {
  e.preventDefault();
  $('#confirm-delete-modal .name').text(item.name);
  $('#delete-btn').data('id', item.id);
  $('#delete-btn').on('click', handleDelete)
  $('#confirm-delete-modal').modal('show');
}

// Closes a confirm delete modal
// Can only be called from an event handler (hence the event passed in parameter)
// Expects target element to have data-name property
const closeConfirmDeleteModal = (e) => {
  $(`#delete-btn`).off();
  $(`#delete-btn`).unbind();
  $(`#delete-btn`).removeData();
  const warningEl = $("#confirm-delete-modal .warning");
  if (warningEl) {
    warningEl.remove();
  };
  $(`#confirm-delete-modal`).modal('hide');
}

// Closes #confirm-save-modal and removes data
const closeConfirmSaveModal = (e) => {
  $(`#save-btn`).off();
  $(`#save-btn`).unbind();
  $(`#save-btn`).removeData();
  $(`#confirm-save-modal`).modal('hide');
}

// Closes #create-new-modal and clears form
const closeCreateNewModal = (e) => {
  $(`#new-form`)[0].reset();
  $(`#new-modal`).modal('hide');
  $(`#new-error-alert`).hide();
  $(`#create-new-modal`).modal('hide');
  if ($("#new-modal .alert").length) {
    $("#new-modal .alert").alert("close");
  }
}

const closeAlert = (e) => {
  $(e.target).parent().remove();
}

// Opens an error alert in parentElId
const openAlert = (type, parentElId, message) => {
  $(parentElId).append(`
    <div class="alert alert-${type} alert-dismissible" role="alert">
      <span clas="text">${message}</span>
      <button type="button" class="btn-close" aria-label="Close" onClick="closeAlert(event)"></button>
    </div>
  `);
};

// Displays more information about data related to the item being deleted
const createRelatedDataList = (list, message, itemKey) => {
  $('#confirm-delete-modal .modal-body').append(`
    <div class="warning">
      <p>${message}</p>
      <ul>
        ${list.map(item => {
          return `<li>${item[itemKey]}</li>`
        }).join('')}
      </ul>
    </div>
  `);
}

// Displays a green toast in the bottom right-hand corner of screen
const displayToastMessage = (message) => {
  $('#global-toast .toast-text').text(message);
  $('#global-toast').toast('show');
};


// Takes a name (e.g. "simulate"), and returns an object of data from the tab's form.
const getValuesFromForm = (formEl) => {
  const _formInputEls = $(formEl).find(":input:not(:submit):input:not(:button)");
  let data = {};
  _formInputEls.each((i, el) => {
    const name = el.name;
    if (name) {
      data[name] = el.value;
      if (el.type === "checkbox") {
        data[name] = el.checked ? 1 : 0
      }
    }
  });
  return data;
}

// Takes a form element name and returns an object of data containing the display text
const createGraphFilenameFromForm = (formEl) => {
  const startDate = $("#startdate").val();
  const gridName = $("#grid-selection option:selected").text();
  const powerloadName = $("#powerload-selection option:selected").text();
  return createGraphFilename(gridName, powerloadName, startDate);
}

// Takes a string and returns it as a string with file-safe characters
const sanitizeFilename = (string) => {
  const badCharsRegExp = /[<>:"\/\\|?*\x00-\x1F\s]/g;
  return string.replace(badCharsRegExp, '');
};

const createGraphFilename = (gridName, powerloadName, startDate) => {
  const formattedStartDate = startDate.replace(" ", "_");
  const fileName = `${formattedStartDate}_${gridName}_${powerloadName}`
  return sanitizeFilename(fileName)
}


// Handler for inputs which prevents decimals
const preventDecimal = (el, e) => {
  // Ignore delete and backspace keys
  if (e.keyCode === 46) {
    e.preventDefault();
    return;
  }  
};

// Takes spec data and returns a number input (string) with validation
const createNumberInput = (item) => {
  let {id, value, minVal, maxVal} = item;
  if (item.parameterType === "boolean") {
    return `<input name="${id}" class="checkbox-inline" type="checkbox" ${value !== null && value === 1 ? "checked" : ""}></input>`;
  }

  // Format min, max and step
  if (item.parameterType === "integer") {
    // Check that max/min are also integers
    if (isNumber(minVal) && !Number.isInteger(minVal)) {
      minVal = Math.ceil(minVal);
    }
    if (isNumber(maxVal) && !Number.isInteger(maxVal)) {
      maxVal = Math.floor(maxVal);
    }
  }

  return (`
    <input 
      id="spec-${id}"
      type="number"
      ${isNumber(minVal) ? `min=${minVal}` : ""}
      ${isNumber(maxVal) ? `max=${maxVal}` : ""}
      class="form-control no-step"
      step="${item.parameterType === "integer" ? "1" : "any"}"
      name="${id}" 
      ${isNumber(value) ? `value=${value}` : ""}
      required="true">
    </input>
  `)
};

// Displays the editing elements in the parent of the element that was clicked
const enableEdit = (e) => {
  $(".display-container").show();
  const currentEditEl = $(".edit-container.editing");

  if (currentEditEl.length > 0) {
    currentEditEl.hide(); // Close any open editors
    currentEditEl.closest("form").trigger("reset");
    currentEditEl.removeClass("editing"); 
  }

  const parentEl = $(e.target).parent().parent();
  $(parentEl).find(".display-container").hide();
  $(parentEl).find(".edit-container").show();
  $(parentEl).find(".edit-container").addClass("editing");
};

// Disables the editing elements int he parent of the element that was clicked
const disableEdit = (e) => {
  const parentEl = $(e.target).parent().parent();
  parentEl.find(".edit-container").removeClass("editing");
  parentEl.find(".display-container").show();
  parentEl.find(".edit-container").hide();
  parentEl.closest("form").trigger("reset");
};

// Takes a string, returns HTML for editing it (textarea with save/cancel buttons)
const createDescriptionEdit = (text) => {
  return (`
    <div class="description">
      <p style="margin-bottom: 5px;"><b>Description:</b> </p>
      <div class="display-container">
        <span>${text ? text : ""}</span>
        <i class="edit-pencil bi bi-pencil-square" onclick="enableEdit(event)"></i>
      </div>
      <div class="edit-container" style="display: none;">
        <textarea class="form-control" name="description" maxlength="128">${text ? text : ""}</textarea>
        <button type="submit" id="save-description-btn" class="btn btn-success btn-sm save">
          <i class="bi bi-check2"></i>
        </button>
        <button type="button" class="btn btn-secondary btn-sm cancel">
          <i class="bi bi-x-lg"></i>
        </button>
      </div>
    </div>
  `)
};

// Takes a string and returns HTML for editing it (inline input with save/cancel buttons)
const createNameEdit = (text) => {
  return (`
    <div class="name">
      <div class="display-container">
        <span>${text}</span>
        <i class="edit-pencil bi bi-pencil-square" onclick="enableEdit(event)"></i>
      </div>
      <div class="edit-container" style="display: none;">
        <input class="form-control" value="${text}" name="name" autocomplete="off" maxlength="32"></input>
        <button type="submit" class="btn btn-success btn-sm save">
          <i class="bi bi-check2"></i>
        </button>
        <button type="button" class="btn btn-secondary btn-sm cancel">
          <i class="bi bi-x-lg"></i>
        </button>
      </div>     
    </div>
  `)
};

// Takes a list of numbers and returns HTML of multiple elements to edit them (multiple inputs with save/cancel buttons)
const createListEdit = (list, title, id) => {
  return (
    `<div class="list">

      <div class="display-container">
        <h5 class="card-title align-center">${title}</h5>
        <i class="bi bi-pencil-square edit-pencil" onclick="enableEdit(event)"></i>
        <br/>
        ${buildSpecList(list)}
      </div>

      <div class="edit-container" style="display: none;">
        <h5 class="card-title align-center">${title}</h5>
        <div class="editable-list">
            ${list.map(item => {
              const inputHtml = createNumberInput(item);
              return `
                <div class="editable-list-item ${item.parameterType === "boolean" ? "inline" : ""}">
                  <b>${item.name}:</b> ${inputHtml}
                </div>
              `;
            }).join('')}
          </div>
          <br/>
          <button class="btn btn-secondary" type="button">Cancel</button>
          <button class="btn btn-success" type="submit" data-id="${id}">Save</button>
      </div>
    </div>`
  )
};

// Maps out an array of items using full-row Bootstrap cards
// Adds events to each card for editing and deleting items
const createFullRowCard = (dataArray, componentTypes, minVal, maxVal, specDescription, deleteCallback) => {
  dataArray.forEach(item => {
    $("#list").append(`
      <div class="card" id="card-${item.id}">
        <div class="header card-header d-flex justify-content-between align-items-baseline"> 
          <div id="name-container-${item.id}"></div>
        </div>
        <div class="card-body">
          <div id="description-container-${item.id}"></div>
          <br/>
          <div id="spec-list-${item.id}"></div>
          <a href="#" id="${item.id}-open-confirm-delete-btn" data-id="${item.id}" class="card-link float-end delete">Delete</a>
        </div>
      </div>
    `);

    const componentTypeList = Object.keys(componentTypes).map(ctId => {
      const itemSpec = item.specs.find(s => s.componentTypeId == ctId);
      return {
        id: ctId,
        value: itemSpec ? itemSpec.value : undefined,
        minVal,
        maxVal,
        name: componentTypes[ctId].description
      }
    });

    createFullRowCardFormEvents(item, componentTypeList, specDescription);
    $(`#${item.id}-open-confirm-delete-btn`).on('click', (e) => openConfirmDeleteModal(e, item, deleteCallback));

  });
};

// Creates the display and form views for full-row bootstrap cards
const createFullRowCardFormEvents = (item, componentTypeList, specDescription) => {
  createFormWithEvents(item.id, `#name-container-${item.id}`, item.name, "name", null, null, saveNameDescription);
  createFormWithEvents(item.id, `#description-container-${item.id}`, item.description, "description", null, null, saveNameDescription);
  createFormWithEvents(item.id, `#spec-list-${item.id}`, null, "list", componentTypeList, specDescription, saveAttributes)
}

// Creates a form with an onsubmit event and a single input
// id: and ID that will be passed to the form's data-id attributes
// parentElId: the ID of the element the form will be placed
// text: the input's value
// submitCallback: the function to be called onSubmit
// type: either "name" or "description"
const createFormWithEvents = (id, parentElId, text, type, list, title, submitCallback) => {
  const $form = $(`<form data-id="${id}"></form>`);
  let element = null;

  if (type === "description") {
    element = createDescriptionEdit(text);
  }

  if (type === "name") {
    element = createNameEdit(text);
  }

  if (type === "list") {
    element = createListEdit(list, title, id)
  }

  $form.append(element);

  $form.submit((e) => {
    e.preventDefault();
    $(e.target).find(".display-container").show();
    $(e.target).find(".edit-container").hide();
    submitCallback(e);
  });

  $form.find(".btn-secondary").click((e) => {
    $form.trigger("reset");
    $(e.target).find(".display-container").show();
    $(e.target).find(".edit-container").hide();
    disableEdit(e)
  });

  $(parentElId).append($form);

};

const userQuotaCheck = (numItems, dataName, quota) => {
  if (numItems >= quota) {
    alert(`You have reached user account quota of ${quota} entries in ${dataName}s. To add a new ${dataName}, you will first need to delete one of your existing ${dataName}s.`);
    return;
  }

  $(`#new-modal`).modal("show");
}

// Returns true if value is number including decimals and zero
const isNumber = (val) => {
  return typeof val === "number" && !isNaN(val);
};

// Checks if a string is made purely of numbers, returns true/false
const isNumericString = (str) => {
  if (typeof str === "number") return true;
  return !isNaN(parseFloat(str));
}

// Handles collapsing/expanding main mobile navigation
const toggleMobileToolNavMenu = (el, e) => {
  const navMenu = $("#tool-navigation");
  if (navMenu.hasClass("show-nav-dropdown")) {
    navMenu.removeClass("show-nav-dropdown");
  }
  else {
    navMenu.addClass("show-nav-dropdown");
  }
}

// Takes a dropdown element and dataArray, and appends the data to the dropdown
const populateDropdown = (dropdownEl, dataArray, defaultSelection) => {
  dataArray.forEach(item => {
    dropdownEl.append(new Option(item.name, item.id, false, false))
  });
  if (defaultSelection) {
    dropdownEl.val(defaultSelection);
  }
};

const populateLocationDropdown = (dropdownEl, locationObj) => {
  Object.keys(locationObj).forEach(name => {
    dropdownEl.append(new Option(name, name, false, false))
  });
};

// Adds bootstrap modal events to #new-modal and #confirm-delete-modal
const addModalEvents = () => {
  $(`#new-modal`).on('hidden.bs.modal', closeCreateNewModal);
  $("#confirm-delete-modal").on("hidden.bs.modal", closeConfirmDeleteModal)
};

const formatResultsStatus = (success, computeJobId) => {
  if (success === 0) return "Failure";
  if (success === 1) return "Success";
  if (computeJobId == null) return "Failed to submit";
  return "In progress";
};

const createCompactSpecList = (component) => {
  const componentTypeId = Object.keys(componentTypes).find(ct => {
    const componentType = componentTypes[ct];
    return componentType.parameterName === component.typeName;
  });
  const componentType = componentTypes[componentTypeId]

  return componentType.specs.map((s) => {
    return {name: s.name, value: component.attributes[s.id], parameterType: s.parameterType};
  });
};

const createCompactComponentsList = (options) => {
  const { components, allowEditQty, removeCallback, removeText } = options; 

  $(`#components-accordion-left`).empty();
  $(`#components-accordion-right`).empty();
  if (components.length > 0) {

    components.forEach((component, i) => {
      const componentSpecList = createCompactSpecList(component);

      $(`#components-accordion-${i % 2 == 0 ? "left" : "right"}`).append(`
        <div class="accordion-item">
          
          <div class="component-header">
            ${buildComponentHeader({component, showQuantity: false})}  
            
            <div class="component-qty-rmv-container d-flex ${allowEditQty ? "justify-content-between" : "justify-content-end"}">

              <div class="name-display" id="display-component-${component.id}-quantity" data-id="${component.id}" style=display:${allowEditQty ? "block" : "none"};>
                <span>Quantity: </span>
                <span id="edit-name-display">${component.quantity}</span>
                <i id="edit-component-${component.id}-quanity-btn" class="bi bi-pencil-square edit-pencil" onclick="showEditQuantity(event)" data-id="${component.id}"></i>
              </div>

              <div class="edit-container" data-id="${component.id}" id="edit-component-${component.id}-quantity-container" style="display: none;">
                <form onSubmit="saveComponentQuantity(event)" data-id="${component.id}">
                  <input 
                    id="edit-quantity-${component.id}-input"
                    name="component-quantity" 
                    type="number" 
                    class="form-control" 
                    value="${component.quantity}" 
                    min="1" 
                    max="20" 
                    step="1">
                  <button type="submit" id="save-component-${component.id}-quantity-btn" class="btn btn-success btn-sm save">
                    <i class="bi bi-check2"></i>
                  </button>
                  <button id="cancel-edit-component-${component.id}-quantity-btn" onclick="cancelEditQuantity(event)" data-id="${component.id}" class="btn btn-secondary btn-sm cancel">
                    <i class="bi bi-x-lg"></i>
                  </button>
                </form>
              </div>

              <a href="#" id="remove-component-${component.id}-from-btn" class="float-end delete" data-id="${component.id}">
                ${removeText} <i class="bi bi-x-lg"></i>
              </a>

            </div>
            
          </div>

          <div class="accordion-header" id="component-${component.id}-heading">
            <div class="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#component-${component.id}-collapse" aria-expanded="true" aria-controls="panelsStayOpen-collapseOne">
              View specs
            </div>
          </div>
          
          <div id="component-${component.id}-collapse" class="accordion-collapse collapse" aria-labelledby="#component-${component.id}-heading">
            <div class="accordion-body">
              ${buildSpecList(componentSpecList)}
            </div>
          </div>

        </div>
      </div>`);
      $(`#remove-component-${component.id}-from-btn`).on("click", removeCallback);
    });
  }
  else {
    $(`#no-components-message`).show();
  }

};

// Takes powerload data and returns a powerload widget 
// that displays powerload metadata and first 10 rows of the table
const createPowerloadWidget = (powerload, elId, timeframe, showDelete = false) => {
  const deleteButtonHtml = showDelete ? 
  `<a href="#" id="${powerload.id}-open-confirm-delete-btn" data-id="${powerload.id}" class="card-link float-end delete">Delete</a>` 
  : '';
  
  if (showDelete) {
    $(elId).append(`
      <h5>${powerload.name}</h5>
      <div class="card-body">
        <div>
          ${timeframe ? `<div class="text-secondary">${timeframe}</div>` : ""}
          <div class="card-text description">${powerload.description}</div>
          <img src="${powerload.image}"/>
        </div>
        <div>
          <a href="/tools/powerloads/${powerload.id}" class="card-link float-start">View</a>
          ${deleteButtonHtml}
        </div>
      </div>
    `);
  } else {
    $(elId).append(`
      <h5>Powerload</h5>
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-center">
          <h5 class="card-title mb-0 flex-grow-1" style="flex-basis: 75%;">${powerload.name}</h5>
          <div style="flex-basis: 25%;" class="text-end">
            <a href="/tools/powerloads/${powerload.id}" class="card-link" target="_blank">View</a>
          </div>
        </div>
        ${timeframe ? `<div class="text-secondary">${timeframe}</div>` : ""}
        <div class="card-text description">${powerload.description}</div>
        <div id="texttest"></div>
      </div>
    `);
    buildGraphPowerloadApex({
      data: powerload.data, 
      ...miniPowerloadDimensions,
      strokeWidth: 1,
      name: powerload.name,
      graphElId: "texttest"
    });
  }
};

// initialize variable to store powerload data for graph updates
let currentPowerloadData = null;

// Function to update powerload graph based on current date/time selections
const updatePowerloadGraph = () => {
  if (!currentPowerloadData) return;
  
  //declaring these to get the most updated values, otherwise, would grab the initial values on page load
  const startDate = $("#startdate").val();
  const endDate = $("#enddate").val();
  const startTime = $("#starttime").val();
  const endTime = $("#endtime").val();
  
  // If dates are not set, don't update
  if (!startDate || !endDate) return;
  
  const startDateTime = new Date(`${startDate} ${startTime}`);
  const endDateTime = new Date(`${endDate} ${endTime}`);
  
  // Filter data based on selected date/time range
  const filteredData = currentPowerloadData.data.filter(d => {
    const dataTime = new Date(d.middatetime);
    return dataTime >= startDateTime && dataTime <= endDateTime;
  });
  
  // Update the timeframe text
  const newTimeframe = getTimeFrameStringReadable(startDateTime, endDateTime);
  $("#powerload .text-secondary").text(newTimeframe);
  
  // Update the graph with filtered data
  $("#texttest").empty();
  buildGraphPowerloadApex({
    data: filteredData,
    ...miniPowerloadDimensions,
    strokeWidth: 1,
    name: currentPowerloadData.name,
    graphElId: "texttest"
  });
};

const createGridStats = (grid) => {
  if (grid.components.length > 0) {
    return (`
      <div class="d-flex grid-stats-container">
        <div>
          <b>Economic Lifespan:</b> <br/>
          <span id="economic_lifespan">${grid.economic_lifespan} year</span>
        </div>
        <div>
          <b>Investment Cost:</b> <br/>
          <span id="investment_cost">$${Math.round(grid.investment_cost)}</span>
        </div>
        <div>
          <b>OM Cost:</b> <br/>
          <span id="om_cost">$${Math.round(grid.om_cost)}</span>
        </div>
      </div>
    `)
  } 
  return "";
};

const createGridCardComponentList = (grid) => {

  let componentsOfEachType = {};
  let total = 0;

  grid.components.reduce((acc, c) => {
    componentsOfEachType[c.typeDescription] = componentsOfEachType[c.typeDescription] || {
      typeName: c.typeName,
      quantity: 0
    };
    componentsOfEachType[c.typeDescription].quantity += c.quantity;
    total += c.quantity;
  }, {});

  return (`
    <div>
      <span class="text-secondary">${total} components</span>
      <div class="card-text description">${grid.description}</div>
      ${createGridStats(grid)}
      <div class="widget-data components-mini-list">
        ${Object.keys(componentsOfEachType).map(typeDescription => {
          const cType = componentsOfEachType[typeDescription];
          return (`
            <div class="d-flex justify-content-start align-items-end">
              <div class="icon-quantity-container">
                <img src="/static/images/${cType.typeName}.png"/>
                <span>x${cType.quantity}</span>
              </div>
              <div class="text"><span class="text-secondary">${typeDescription}</span></div>
            </div>`);
        }).join("")}
      </div>
    </div>
  `)
};

const createGridWidget = (grid, elId, showDelete = false) => {
  const gridUrl = `/tools/${grid.isSizingTemplate ? "sizing/" : ""}microgrids/${grid.id}`;
  const deleteButtonHtml = showDelete ? 
  `<a href="#" id="${grid.id}-open-confirm-delete-btn" data-name="microgrids" class="card-link float-end delete">Delete</a>` 
  : '';
  if (showDelete) {
    $(elId).append(`
      <h5>${grid.name}</h5>
      <div class="card-body">
        ${createGridCardComponentList(grid)}
        <div>
          <a href="${gridUrl}" class="card-link float-start">View</a>
          ${deleteButtonHtml}
        </div>
      </div>
    `);
  } else {
    $(elId).append(`
      <h5>Microgrid</h5>
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-center">
          <h5 class="card-title mb-0 flex-grow-1" style="flex-basis: 75%;">${grid.name}</h5>
          <div style="flex-basis: 25%;" class="text-end">
            <a href="${gridUrl}" class="card-link" target="_blank">View</a>
          </div>
        </div>
        ${createGridCardComponentList(grid)}
      </div>
    `);
  }
};

const createEnergyManagementSystemWidget = (energyManagementSystem, elId, title) => {
  $(elId).append(`
    <h5>${title}</h5>
    <div class="card energy-management-system-widget" style="width: 100%">
      <div class="card-body">
        <div class="d-flex justify-content-between">
          <h5 class="card-title">${energyManagementSystem.name}</h5>
        </div>
        <div class="card-text description">${energyManagementSystem.description}</div>
      </div>
    </div>
  `);
};

// Utility functions for parsing disturbances and repairs by grid id in compute forms
const getDisturbancesByGridId = async (gridId = null) => {
  const disturbances = await getData("resilience_disturbances_get");
  if (gridId) {
    return disturbances.filter(d => d.gridId == gridId);
  }
  return disturbances;
};

const getRepairsByGridId = async (gridId = null) => {
  const repairs = await getData("resilience_repairs_get");
  if (gridId) {
    return repairs.filter(r => r.gridId == gridId);
  }
  return repairs;
};

const getGridById = async (gridId) => {
  const gridRes = await postData("grids_get", null, {"id": gridId});
  return gridRes.data;
}

const getComponentTypes = async() =>{
  const componentTypes = await getData("component_types");
  return componentTypes
}

// Populates the disturbance dropdown with options
const populateDisturbanceDropdown = (disturbances, selectedId = null) => {
  // Clear existing options
  $("#disturbance-selection").find('option:not(:first)').remove();
  
  // Add disturbance options with gridId data attribute
  disturbances.forEach(d => {
    $("#disturbance-selection").append(`<option value="${d.id}" data-grid-id="${d.gridId}">${d.name}</option>`);
  });
  
  // Set selected value if provided, otherwise clear selection
  if (selectedId) {
    $("#disturbance-selection").val(selectedId);
  } else {
    $("#disturbance-selection").val("");
    $("#disturbance-selection").trigger('change');
  }
};
// Populates the repair dropdown with options
const populateRepairDropdown = (repairs, selectedId = null) => {
  // Clear existing options
  $("#repair-selection").find('option:not(:first)').remove();
  
  // Add repair options with gridId data attribute
  repairs.forEach(r => {
    $("#repair-selection").append(`<option value="${r.id}" data-grid-id="${r.gridId}">${r.name}</option>`);
  });
  
  // Set selected value if provided, otherwise clear selection
  if (selectedId) {
    $("#repair-selection").val(selectedId);
  } else {
    $("#repair-selection").val("");
    $("#repair-selection").trigger('change');
  }
};

// Sets the disabled/enabledstate of the disturbance and repair dropdowns
const setDisturbanceRepairDropdownsState = (enabled) => {
  $("#disturbance-selection").prop('disabled', !enabled);
  $("#repair-selection").prop('disabled', !enabled);
};

// Handles country selection and sets region dropdowns
const handleCountrySelection = async (e) => {
  const defaultRegion = e.data.defaultRegion;
  const regionEl = $("#region-selection");
  const locationEl = $("#location-id-selection");
  resetDropdown(regionEl);
  resetDropdown(locationEl);
  locationEl.prop('disabled', true);
  const res = await postData("locations_get", null, {country: e.target.value});
  if (!res.error) {
    locationArray = res.data.map(k => { return {name: k, id: k} });
    regionEl.prop('disabled', false);
    populateDropdown(regionEl, locationArray, defaultRegion);
    if (defaultRegion) { 
      regionEl.change(); 
      e.data.defaultRegion = null; // Reset default region for next time
    }
  }
};

// Handles region selection and sets location dropdown
const handleRegionSelection = async (e) => {
  const defaultLocationId = e.data.defaultLocationId;
  const locationEl = $("#location-id-selection");
  resetDropdown(locationEl)
  const res = await postData("locations_get", null, {
    country: $("#country-selection").val(), 
    region: e.target.value
  });
  if (!res.error) {
    locationEl.prop('disabled', false);
    locationArray = Object.keys(res.data).map(k => { return {name: k, id: res.data[k].id} });
    populateDropdown(locationEl, locationArray, defaultLocationId);
    if (defaultLocationId) { 
      locationEl.change(); 
      e.data.defaultLocationId = ""; // Reset default location id for next time
    }
  }
};

//window.isInitialLoadFromPreviousJob = true;

function loadingPreviousJob() {
  return window.location.search.includes("id=");
}

// Helper to parse datetime strings
function parseDateTimeString(dateTimeStr) {
  // Handles "YYYY-MM-DD HH:mm:ss" and "YYYY-MM-DDTHH:mm:ss"
  if (typeof dateTimeStr === "string" && dateTimeStr.includes(" ")) {
    return new Date(dateTimeStr.replace(" ", "T"));
  }
  return new Date(dateTimeStr);
}

// Handle powerload selection, including setting up start and end dates
const handlePowerloadSelection = async (e) => {
  let defaultStartDate = e.data.defaultStartDate;
  let defaultEndDate = e.data.defaultEndDate;
  let defaultDisturbanceStartDate = e.data.defaultDisturbanceStartDate;

  // Get powerload data
  const powerloadRes = await postData("powerloads_get", null, {id: e.target.value});
  
  if (!powerloadRes.data) {
    console.error("Failed to load powerload data");
    return;
  }

  // Store powerload data globally for graph updates
  currentPowerloadData = powerloadRes.data;

  // Determine which defaults to use:
  // - If loading a previous job AND this is the initial load, use the loaded job's defaults
  if (loadingPreviousJob() && window.isInitialLoadFromPreviousJob) {
    if (defaultStartDate) defaultStartDate = parseDateTimeString(defaultStartDate);
    if (defaultEndDate) defaultEndDate = parseDateTimeString(defaultEndDate);
    if (defaultDisturbanceStartDate) defaultDisturbanceStartDate = parseDateTimeString(defaultDisturbanceStartDate);
  } else {
    defaultStartDate = null;
    defaultEndDate = null;
    defaultDisturbanceStartDate = null;
  }
  initializeDateTimePickers(currentPowerloadData, defaultStartDate, defaultEndDate, defaultDisturbanceStartDate);

  // Create powerload widget
  if (!defaultStartDate) defaultStartDate = new Date(currentPowerloadData.startdatetime);
  if (!defaultEndDate) defaultEndDate = new Date(currentPowerloadData.enddatetime);
  if (!defaultDisturbanceStartDate) defaultDisturbanceStartDate = defaultStartDate;
  const timeframe = getTimeFrameStringReadable(defaultStartDate, defaultEndDate);
  $("#powerload").show();
  $("#powerload").empty();
  createPowerloadWidget(currentPowerloadData, "#powerload", timeframe, false);

  // Mark initial load as complete after first powerload selection
  if (loadingPreviousJob() && window.isInitialLoadFromPreviousJob) {
    // Set a flag to indicate we're no longer in initial load mode
    window.isInitialLoadFromPreviousJob = false;
  }
};

// Removes all options from dropdown except disabled
const resetDropdown = (dropdownEl) => {
  dropdownEl.find("option:not(:disabled)").each((i, el) => {
    el.remove();
  });
  dropdownEl.val("");
};

const createStatEl = (name, value, imageName) => {
  return (
    `<div class="d-flex flex-column stat component">
      <img src="${statsToImageUrl[imageName]}"/>
      <span>${name}</span> 
      <span class="val">${value}</span>
    </div>`
  )
};

// Populates #stats-container using summary_stats
const displayStats = (stats) => {
  $("#stats-container").show();
  Object.keys(stats).forEach(key => {
    if (!isNaN(stats[key])) {
      const statEl = createStatEl(key, stats[key].toFixed(1), key);
      $("#non-component-stats .category").append(statEl)
    }
    if (typeof stats[key] === "object") {
      $("#stats-container .components").prepend(`<h5>${key}</h5>`)
      Object.keys(stats[key]).forEach(componentKey => {
        const componentType = Object.values(componentTypes).find(ct => ct.parameterName === componentKey);
        const displayName = componentType ? componentType.displayName : componentKey;
        const imageName = componentType ? componentType.parameterName : componentKey;
        let percentage = (stats[key][componentKey] * 100).toFixed(1);
        percentage = percentage <= 0 && percentage > -0.05 ? "0.0" : percentage;
        const componentStatEl = createStatEl(displayName, percentage + "%", imageName);
        $("#stats-container .components .category").append(componentStatEl);
      })
    }
  });
};

const handleGridSelection = async (e) => {
  const selectedGridId = parseInt(e.target.value);
  const selectedGrid = e.data.grids.find(g => g.id === selectedGridId);
  // Enable/disable disturbance and repair dropdowns based on grid selection
  if (selectedGridId) {
    setDisturbanceRepairDropdownsState(true);
    // Get filtered disturbances and repairs for the selected grid
    const filteredDisturbances = await getDisturbancesByGridId(selectedGridId);
    const filteredRepairs = await getRepairsByGridId(selectedGridId);
    // Preserve existing selections if they exist in the filtered options
    const currentDisturbanceId = $("#disturbance-selection").val();
    const currentRepairId = $("#repair-selection").val();
    // Check if current selections are valid for the new grid
    const validDisturbanceId = filteredDisturbances.some(d => d.id == currentDisturbanceId) ? currentDisturbanceId : null;
    const validRepairId = filteredRepairs.some(r => r.id == currentRepairId) ? currentRepairId : null;
    
    // Populate dropdowns with filtered options, preserving valid selections
    populateDisturbanceDropdown(filteredDisturbances, validDisturbanceId);
    populateRepairDropdown(filteredRepairs, validRepairId);
    $("#grid").show();
    $("#grid").empty()
    createGridWidget(selectedGrid, "#grid", false);
    $("#resilience-cards .disturbance-card").remove();
    $("#resilience-cards .repair-card").remove();
  } else {
    setDisturbanceRepairDropdownsState(false);
    $("#grid").hide();
    $("#grid").empty();
    $("#resilience-cards .disturbance-card").remove();
    $("#resilience-cards .repair-card").remove();
  }
};

const handleEnergyManagementSystemSelection = (e) => {
  const selectedId = parseInt(e.target.value);
  const ems = e.data.energyManagementSystems.find(e => e.id === selectedId);
  $("#energy-management-system").show();
  $("#energy-management-system").empty();
  createEnergyManagementSystemWidget(ems, "#energy-management-system", "Energy Management System");
};

const handleDisturbanceRepairSelection = async (e) => {
  const fieldType = e.currentTarget.id.split('-')[0];
  const selectedId = parseInt(e.target.value);
  if (selectedId) {
    let record = null;
    if (fieldType == "disturbance"){
      record = e.data.disturbances.find(d => d.id === selectedId);
    } else {
      record = e.data.repairs.find(d => d.id === selectedId);
    }
    if (record){
      const grid = await getGridById(record.gridId);
      const componentTypes = await getComponentTypes();
      const method = $("#method").text().trim();
      $(`#${fieldType}-card`).show();
      $(`#${fieldType}-card`).empty();
      createDisturbanceRepairWidget(record, grid, method, fieldType, componentTypes, `#${fieldType}-card`, false)
    }
  } else {
    // Hide the card if no selection is made
    $(`#${fieldType}-card`).hide().empty();
  }
};

const handleRepairSelection = (e) => {
  const selectedGridId = parseInt(e.target.value);
  const repair = e.data.repairs.find(r => r.id === selectedGridId);
  // placeholder for future widget
  if(selectedGridId) {
  }
};

// Takes an option object for resetting charts, summary stats and optional default selections
// Populates form inputs and adds event listeners.
const populateForm = async (options) => {
  const { isSizing, defaultSelections, defaultLocations, includeDisturbance} = options;
  
  // Set initial load flag for previous job loading
  if (loadingPreviousJob()) {
    window.isInitialLoadFromPreviousJob = true;
  }
  const grids = await getData(isSizing ? "sizing_grids_get" : "grids_get");
  const energyManagementSystems = await getData("energy_management_systems");
  const powerloads = await getData("powerloads_get");
  const locations = await getData("locations_get");
  const countryArray = locations.map(k => { return ({name: k, id: k}) });
  const gridsWithComponents = grids.filter(grid => grid.components.length > 0);
  let disturbances = null;
  let repairs = null;
  if (includeDisturbance) { 
    disturbances = await getDisturbancesByGridId();
    repairs = await getRepairsByGridId();
  }

  let defaultGrid;
  let defaultEnergyManagementSystem;
  let defaultPowerload;
  let defaultStartDate;
  let defaultEndDate;
  let defaultRegion;
  let defaultLocationId;
  let defaultDisturbanceId;
  let defaultDisturbanceStartDate;
  let defaultNumShiftHours;
  let defaultRepairId;

  /// Set defaults (if any)
  if (defaultSelections) {
    defaultStartDate = defaultSelections.startdatetime;
    defaultEndDate = defaultSelections.enddatetime;
    defaultPowerload = defaultSelections.powerloadId;
    defaultEnergyManagementSystem = defaultSelections.energyManagementSystemId;
    defaultGrid = defaultSelections.gridId;
    defaultRegion= defaultLocations ? defaultLocations.region : "";
    defaultLocationId = defaultSelections.locationId;
    defaultDisturbanceId = defaultSelections.disturbanceId;
    defaultDisturbanceStartDate = defaultSelections.disturbanceStartdatetime;
    defaultNumShiftHours = defaultSelections.numShiftHours;
    defaultRepairId = defaultSelections.repairId;
  }

  // Manually set microgrid label text for sizing
  if (isSizing) {
    $("#grid-selection").parent().find("label").text("Microgrid Sizing Template");
    $("#default-sizing-option").text("Select a microgrid sizing template");
  }

  // Populate dropdowns with data lists
  populateDropdown($("#grid-selection"), gridsWithComponents, defaultGrid);
  populateDropdown($("#energy-management-system-selection"), energyManagementSystems, defaultEnergyManagementSystem);
  populateDropdown($("#powerload-selection"), powerloads, defaultPowerload);
  populateDropdown($("#country-selection"), countryArray);
  
  // Disable disturbance and repair dropdowns initially
  setDisturbanceRepairDropdownsState(false);

  if (includeDisturbance) { 
    // Set number of shift hours
    const shiftHoursValue = defaultNumShiftHours !== undefined ? defaultNumShiftHours : "0";
    $("#disturbance-shift-hours-selection").val(shiftHoursValue).change();

    // If there's a default grid, filter the options
    if (defaultGrid) {
      // Get filtered disturbances and repairs for the default grid
      const filteredDisturbances = await getDisturbancesByGridId(defaultGrid);
      const filteredRepairs = await getRepairsByGridId(defaultGrid);
      
      // Populate dropdowns with filtered options
      populateDisturbanceDropdown(filteredDisturbances, defaultDisturbanceId);
      populateRepairDropdown(filteredRepairs, defaultRepairId);
      
      // Enable the dropdowns
      setDisturbanceRepairDropdownsState(true);
    } else {
      // Populate with all options (will be filtered when grid is selected)
      populateDisturbanceDropdown(disturbances, defaultDisturbanceId);
      populateRepairDropdown(repairs, defaultRepairId);
    }
  }

  $(".widget").hide();

  // OnChange event for ALL inputs to reset charts & stats
  $("#form :input").change((e) => {
    clearSummaryStats();
    if (!isSizing) {
      clearCharts(); // Charts don't display on sizing compute page
    }
  });

  // Set specific data and event handlers for each input
  $("#grid-selection").change({grids}, handleGridSelection);
  $("#energy-management-system-selection").change({energyManagementSystems}, handleEnergyManagementSystemSelection);
  $("#powerload-selection").change({defaultStartDate, defaultEndDate, defaultDisturbanceStartDate}, handlePowerloadSelection);
  $("#region-selection").change({defaultLocationId}, handleRegionSelection);
  $("#country-selection").change({defaultRegion}, handleCountrySelection);
  // placeholders for future disturbance and repair widgets
  $("#disturbance-selection").change({disturbances}, handleDisturbanceRepairSelection);
  $("#repair-selection").change({repairs}, handleDisturbanceRepairSelection);

  // Trigger change of default selections to force display of data in form and widgets
  if (defaultLocations) {
    $("#country-selection").val(defaultLocations.country).change();
    $("#grid-selection").change();
    $("#energy-management-system-selection").change();
    $("#powerload-selection").change();
  } else if (defaultSelections) {
    // When loading a previous job without locations, still trigger the necessary changes
    $("#grid-selection").change();
    $("#energy-management-system-selection").change();
    $("#powerload-selection").change();
  }
  if (includeDisturbance) { 
    $("#disturbance-selection").change();
    $("#repair-selection").change();
  }
};

// Handles deleting a result from results pages
async function deleteResult(e) {
  const computeId = $(e.target).data("id");
  const page = $(e.target).data("page");
  const res = await postData(`${page}_results_remove`, null,  {"id": computeId});
  closeConfirmDeleteModal(e);
  $('#confirm-delete-modal').modal('hide');
  if (!res.error) {
    displayToastMessage('Result successfully deleted.');
  }
  build();
}

// Handles opening confirm delete modals for results pages
function handleOpenConfirmDeleteResult(e) {
  const computeId = e.target.dataset.id;
  const page = e.target.dataset.page;
  openConfirmDeleteModal(e, {name: computeId, id: computeId}, deleteResult);
  $("#confirm-delete-modal .record-name").text(computeId);
  $("#delete-btn").data("id", computeId);
  $("#delete-btn").data("page", page);
  $("#confirm-delete-modal").modal("show");
}

// enables run button after computation terminates
const resetButtons = (elementId) => {
  $("#load-btn").hide();
  $("#compute-btn").show();
  const alertEl = $(`${elementId} .alert`);
  if (alertEl) { alertEl.alert("close") }
};

// disables run button when computation starts
const setButtonsLoading = () => {
  $("#compute-btn").hide();
  $("#load-btn").show();
};

// show message during computational run
const createComputeTimeAlert = (elementId) => {
  $(elementId).append(`
    <div class="alert alert-success alert-dismissible fade show" role="alert">
      The run may take a few minutes to complete. If you navigate away from this page, the run will continue. When complete, the results will be accessible through your simulation history.
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    </div>
  `);
}

// set result id in url
const setIdInURL = (id) => {
  const urlParams = new URLSearchParams(window.location.search);
  urlParams.set("id", id);
  window.history.pushState({}, document.title, window.location.pathname + `?id=${id}`);
}

// get result id from url
const getIdFromURL = () => {
  const urlParams = new URLSearchParams(window.location.search);
  let id = null
  if (urlParams.has("id")) {
    id = parseInt(urlParams.get("id"));
  }
  return id;
}

// get result id from url
const deleteIdFromURL = () => {
  const urlParams = new URLSearchParams(window.location.search);
  let id = null
  if (urlParams.has("id")) {
    id = parseInt(urlParams.get("id"));
  }
  return id;
}

// initialize run analysis page
const initializeComputeForm = async (apiEndpoint, options) => {
    let resultsRes = null;
    let locationRes = null;
    const resultId = getIdFromURL()
    if (resultId) {
      resultsRes = await postData(apiEndpoint, null, {id: resultId});
      locationRes =  await postData("locations_get", null, {id: resultsRes.data.locationId});
    }
  
    await populateForm({
      isSizing: options.isSizing ? options.isSizing : false,
      defaultSelections: resultsRes ? resultsRes.data : false,
      defaultLocations: locationRes ? locationRes.data : false,
      includeDisturbance: options.includeDisturbance ? options.includeDisturbance : false
    });
    
    setTimeout(() => {
      if (resultId) {
        $("#compute-btn").click();
      }
      //reminder to go back to solve async issue
      //console.log("1 second has passed");
    }, 1000);

}

// wait for an analysis to complete, then run a callback function
const waitForResult = (apiEndpoint, resultId, elementId, callback, ...callbackArgs) => {
  let isFirstCheck = true;
  return new Promise((resolve) => {
    const checkResult = async () => {
      const successRes = await postData(apiEndpoint, null, { id: resultId });
      if (successRes.data.success === null) {
        if (isFirstCheck) { createComputeTimeAlert(elementId); }
        isFirstCheck = false;
        setTimeout(checkResult, 15000); //the params are avail through checkResult() from the outer function of waitForResult, no longer need to add them here
      } 
      else if (successRes.data.success) {
        if (callback) callback(...callbackArgs);
        resetButtons(elementId);
        resolve(true);
      }
      else {
        openAlert("danger", "#tool-error", "Run failed. Please contact admin for more information.");
        resetButtons(elementId);
        resolve(false);
      }
    };
    checkResult();
  });
};

// run an analysis method and wait for the results
const runAnalysisAndWait = async (customFormData, computeApiEndpoint, resultApiEndpoint, elementId, callback) => {
  deleteIdFromURL();
  const powerloadWindow = currentPowerloadData ? initializePowerloadWindow(currentPowerloadData) : null;
  validatePowerloadDateTimeInputs(powerloadWindow, null)
  const formData = getValuesFromForm($("#form"));
  const dateTimeData = getFormDateTimes();
  const allFormData = {...formData, ...dateTimeData, ...(customFormData !== null ? customFormData : {})};
  const computeRes = await postData(computeApiEndpoint, null, allFormData);
  if (!computeRes.error) {
    setIdInURL(computeRes.data.compute_id)
    await waitForResult(resultApiEndpoint, computeRes.data.compute_id, elementId,
                        callback, computeRes.data.compute_id);
  } else {
    resetButtons(elementId);
  }
};

// run an analysis method and do not wait for the results
const runAnalysisAndNoWait = async (customFormData, computeApiEndpoint, elementId) => {
  const powerloadWindow = currentPowerloadData ? initializePowerloadWindow(currentPowerloadData) : null;
  validatePowerloadDateTimeInputs(powerloadWindow, null)
  const formData = getValuesFromForm($("#form"));
  const dateTimeData = getFormDateTimes();
  const allFormData = {...formData, ...dateTimeData, ...(customFormData !== null ? customFormData : {})};
  const computeRes = await postData(computeApiEndpoint, null, allFormData);
  if (!computeRes.error) {
    if (computeRes.data.compute_job_id !== null) {
      displayToastMessage(`Job submitted with Slurm ID ${computeRes.data.compute_job_id}.`);
    }
    else {
      const message = `Analysis has previously been submitted with result ID ${computeRes.data.compute_id}.
      If you wish to recompute the analysis, first delete the existing result.`;
      openAlert("warning", "#warning-container", message);
    }
  }
  resetButtons(elementId);
}
