// Returns double digit given single number (ex: 1 ==> 01)
const makeDoubleDigit = (num) => {
  return ((num < 10 ? '0' : '') + num);
};

// Takes a date object and returns hh:mm string
// If withSeconds = true, returns hh:mm:ss string
const getTimeString = (options) => {
  const {date, withSeconds} = options;
  let hours = date.getHours();
  let minutes = date.getMinutes();
  let timeString = makeDoubleDigit(hours) + ":" + makeDoubleDigit(minutes);
  if (withSeconds) {
    let seconds = date.getSeconds();
    timeString += ":" + makeDoubleDigit(seconds);
  }
  return timeString;
};

// Takes a JS date and returns it in the format mm-dd-yyyy
const getDateString = (date) => {
  let monthNum = date.getMonth() + 1;
  let dayNum = date.getDate();
  if (monthNum < 10) {
    monthNum = `0${monthNum}`;
  }
  if (dayNum < 10) {
    dayNum = `0${dayNum}`;
  }
  return monthNum + "/" + dayNum + "/" + date.getFullYear();
};

// Takes a JS date and returns it in the format MM dd yy (ex: Jan 03 2023)
const getDateStringReadable = (date) => {
  const monthName = date.toLocaleString("default", { month: "short" });
  const day = date.getDate();
  let formattedDay = (day < 10 ? '0' : '') + day;
  return formattedDay + " " + monthName + " " + date.getFullYear();
};

// Takes a start and end date and returns a string representing the timeframe
const getTimeFrameStringReadable = (startDate, endDate) => {
  startDate = new Date(startDate);
  endDate = new Date(endDate);
  const startDateString = getDateStringReadable(startDate) + " " + getTimeString({date: startDate, withSeconds: false});
  const endDateString = getDateStringReadable(endDate) + " " + getTimeString({date: endDate, withSeconds: false});
  return startDateString + " - " + endDateString;
};

// Takes a date mm/dd/yyy and optional time HH:mm string and returns JS date object
const getDateFromDateTimeStrings = (dateString, timeString) => {
  if (!dateString) return null;
  const [month, day, year] = dateString.split('/').map(Number);
  if (!timeString?.trim()) {
    return new Date(year, month - 1, day);
  }
  const [hours, minutes] = timeString.split(':').map(Number);
  return new Date(year, month - 1, day, hours, minutes, 0);
};

// Gets and returns start/end dates strings, min/max, and full start/end dates
const getFormDateTimes = () => {
  const startDateString = $("#startdate").val();
  const startTimeString = $("#starttime").val();
  const startDateTimeString = startDateString + " " + startTimeString;
  const startDate = getDateFromDateTimeStrings(startDateString, startTimeString);
  const endDateString = $("#enddate").val();
  const endTimeString = $("#endtime").val();
  const endDate = getDateFromDateTimeStrings(endDateString, endTimeString);
  const endDateTimeString = endDateString + " " + endTimeString;
  const disturbanceStartDateString = hasDisturbanceElements() ? $("#disturbance_startdate").val() : null;
  const disturbanceStartTimeString = hasDisturbanceElements() ? $("#disturbance_starttime").val() : null;
  const disturbanceStartDateTimeString = disturbanceStartDateString && disturbanceStartTimeString ? 
    disturbanceStartDateString + " " + disturbanceStartTimeString : null;
  const disturbanceStartDate = getDateFromDateTimeStrings(disturbanceStartDateString, disturbanceStartTimeString);
  return ({
    startDateString,
    startTimeString,
    "startdatetime": startDateTimeString,
    startDate,
    endDateString,
    endTimeString,
    "enddatetime": endDateTimeString,
    endDate,
    disturbanceStartDateString,
    disturbanceStartTimeString,
    "disturbance_startdatetime": disturbanceStartDateTimeString,
    disturbanceStartDate
  })
};

// Calculate minutes gap based on time window duration
const minutesGap = (startDate, endDate) => {
  const durationMs = endDate.getTime() - startDate.getTime();
  const durationMinutes = durationMs / (1000 * 60);
  
  if (durationMinutes < 1) {
    alert("Sim: Powerload window is not long enough to run an analysis due to too short of a time window.");
  } 
  if (durationMinutes < 5) {
    return 1;
  } else if (durationMinutes < 10) {
    return 5;
  } else if (durationMinutes < 15) {
    return 10;
  } else if (durationMinutes < 30) {
    return 15;
  } else {
    return 30; // default
  }
};

const showAutoCorrectionAlert = (message, duration = 9000, fifo = true) => {
  const $container = $('.toast-container');
  const $template  = $('#global-toast');
  if (!$container.length || !$template.length) return alert(message);
  
  const isSim = message.includes('Sim:');
  const $toast = $template.clone().removeAttr('id');
  const $icon = $toast.find('i');

  if (isSim) {
    $toast.removeClass('bg-success text-white').addClass('bg-warning text-dark');
    $icon.removeClass('bi-check-circle-fill').addClass('bi-exclamation-triangle-fill');
  } else {
    $toast.removeClass('bg-warning text-dark').addClass('bg-success text-white');
    $icon.removeClass('bi-exclamation-triangle-fill').addClass('bi-check-circle-fill');
  }
  $toast.find('.toast-text').text(message);
  fifo ? $container.prepend($toast) : $container.append($toast);
  $toast.toast('show');
  setTimeout(() => { $toast.toast('hide'); }, duration);
};

// Check if disturbance elements exist on the page
const hasDisturbanceElements = () => {
  return $("#disturbance_startdate").length > 0 && $("#disturbance_starttime").length > 0;
};

// Initialize powerload window constraints
const initializePowerloadWindow = (powerloadData) => {
  const minDate = new Date(powerloadData.startdatetime);
  const maxDate = new Date(powerloadData.enddatetime);
  const m = minutesGap(minDate, maxDate);

  return {
    minDate,
    maxDate,
    minTime: getTimeString({date: minDate, withSeconds: false}),
    maxTime: getTimeString({date: maxDate, withSeconds: false}),
    minutesGap: m
  };
};

const shiftEndpoint = (endpoint, minutesThreshold, operator) => {
  const baseEndPoint = endpoint.getTime();
  const milliseconds = minutesThreshold * 60000;
  const newTime = operator === "+" ? baseEndPoint + milliseconds : baseEndPoint - milliseconds;
  return new Date(newTime);
};

const updateDatePicker = (elId, minDate, maxDate) => {
  $(elId).datepicker("option", {
    minDate,
    maxDate
  });
};

const updateTimePicker = (elId, start = null, end = null) => {
  $(elId).timepicker("option", {
    minTime: start || "00:00",
    maxTime: end || "23:30"
  });
}

const updateDateTimePickers = (plWindow) => {
  const { startDateString, startDate, endDateString, endDate, disturbanceStartDateString } = getFormDateTimes();

  const shiftedEndDate = shiftEndpoint(endDate, plWindow.minutesGap, "-");
  updateDatePicker("#startdate", plWindow.minDate, shiftedEndDate);
  updateTimePicker(
    "#starttime",
    startDateString === getDateString(plWindow.minDate) ? plWindow.minTime : null,
    startDateString === endDateString
      ? getTimeString({ date: shiftedEndDate, withSeconds: false })
      : null
  );

  const shiftedStartDate = shiftEndpoint(startDate, plWindow.minutesGap, "+");
  updateDatePicker("#enddate", shiftedStartDate, plWindow.maxDate);
  updateTimePicker(
    "#endtime",
    startDateString === endDateString
      ? getTimeString({ date: shiftedStartDate, withSeconds: false })
      : null,
    endDateString === getDateString(plWindow.maxDate) ? plWindow.maxTime : null);

  if (hasDisturbanceElements()) {
    updateDatePicker("#disturbance_startdate", startDate, shiftedEndDate);
    updateTimePicker(
      "#disturbance_starttime",
      disturbanceStartDateString === startDateString ? getTimeString({ date: startDate, withSeconds: false }) : null,
      disturbanceStartDateString === endDateString
        ? getTimeString({ date: shiftedEndDate, withSeconds: false })
        : null
    );
  }
};

const validatePowerloadDateTimeInputs = (plWindow, lastChangedField = null, displayAutoCorrectionAlert = true) => {
  
  const getNormalizedDate = (date) => {
    const n = new Date(date);
    n.setSeconds(0);
    n.setMilliseconds(0);
    return n;
  };

  const limitToMaxDateTime = (newEndDate) => {
    return newEndDate > nPlMax ? new Date(nPlMax) : newEndDate; //checks if date is past max time, if so, set date as max time, otherwise, user set date
  };

  const limitToMinDateTime = (newStartDate) => {
    return newStartDate < nPlMin ? new Date(nPlMin) : newStartDate; //checks if date is before min time, if so, set to min time, otherwise, user set date
  };

  const isNotValidTimeGap = (start, end, minutesGap) => {
    const diffMinutes = (end.getTime() - start.getTime()) / 60000;
    return diffMinutes < minutesGap;
  }

  const setDateTimeInputs = (start, end, disturbance = null) => {

    const updateDateField = (selector, date) => { //helper to help set values in form for both time and date
      const value = getDateString(date);
      $(selector).datepicker('setDate', date);
    };

    const updateTimeField = (selector, date, withSeconds) => { //helper to help set values in form for both time and date
      const value = getTimeString({date: date, withSeconds: withSeconds});
      $(selector).timepicker("setTime", value);
    };

    updateDateField("#startdate", start);
    updateTimeField("#starttime", start, false);
    updateDateField("#enddate", end);
    updateTimeField("#endtime", end, false);

    if (disturbance && hasDisturbanceElements()) {
      updateDateField("#disturbance_startdate", disturbance);
      updateTimeField("#disturbance_starttime", disturbance, false);
    };
  };

  const generateCorrectionRules = (tStart, tEnd, tDisturbance = null) => {
    const correctionRules = [
      {
        condition: tStart < nPlMin, 
        newStart: nPlMin, 
        newEnd: tEnd, 
        message: "Sim: Start Date/Time has been adjusted to ensure it comes after the powerload start time."
      },
      {
        condition: tStart > nPlMax, 
        newStart: shiftEndpoint(nPlMax, plWindow.minutesGap, "-"), 
        newEnd: tEnd, 
        message: "Sim: Start Date/Time has been adjusted to ensure it comes before the powerload end time."
      },
      {
        condition: tEnd < nPlMin, 
        newStart: tStart, 
        newEnd: shiftEndpoint(nPlMin, plWindow.minutesGap, "+"), 
        message: "Sim: End Date/Time has been adjusted to ensure it comes after the powerload start time."
      },
      {
        condition: tEnd > nPlMax, 
        newStart: tStart, 
        newEnd: nPlMax, 
        message: "Sim: End Date/Time has been adjusted to ensure it does not come after the powerload end time."
      },
      {
        condition: lastChangedField === 'start' && isNotValidTimeGap(tStart, tEnd, plWindow.minutesGap),
        newStart: limitToMinDateTime(shiftEndpoint(tEnd, plWindow.minutesGap, "-")),
        newEnd: tEnd, 
        message: "Sim: Start Date/Time has been adjusted to ensure it comes before the end time."
      },
      {
        condition: lastChangedField === 'end' && isNotValidTimeGap(tStart, tEnd, plWindow.minutesGap), 
        newStart: tStart, 
        newEnd: limitToMaxDateTime(shiftEndpoint(tStart, plWindow.minutesGap, "+")), 
        message: "Sim: End Date/Time has been adjusted to ensure it comes after the start time."
      }
    ]
    if (tDisturbance) {
      const maxDisturbance = shiftEndpoint(tEnd, plWindow.minutesGap, "-");
      correctionRules.push(
        {
          condition: tDisturbance < tStart, 
          newStart: tStart,
          newDisturbance: tStart,
          newEnd: tEnd, 
          message: "Sim: Disturbance start Date/Time has been adjusted to ensure it does not come before the simulation start time."
        },
        {
          condition: tDisturbance > maxDisturbance, 
          newStart: tStart,
          newDisturbance: tStart,
          newEnd: tEnd, 
          message: "Sim: Disturbance start Date/Time has been adjusted to simulation start time because it was after the simulation end time."
        }
      );
    }
    return correctionRules
  }
  
  const startDateString = $("#startdate").val();
  const startTimeString = $("#starttime").val();
  const endDateString = $("#enddate").val();
  const endTimeString = $("#endtime").val();
  
  if (!startDateString || !startTimeString || !endDateString || !endTimeString) {
    return false;
  }

  let nStart = getNormalizedDate(getDateFromDateTimeStrings(startDateString, startTimeString));
  let nEnd = getNormalizedDate(getDateFromDateTimeStrings(endDateString, endTimeString));
  let tDisturbance = null;
  if (hasDisturbanceElements()) {
    const disturbanceStartDateString = $("#disturbance_startdate").val();
    const disturbanceStartTimeString = $("#disturbance_starttime").val();
    if (disturbanceStartDateString && disturbanceStartTimeString) {
      tDisturbance = getNormalizedDate(getDateFromDateTimeStrings(disturbanceStartDateString, disturbanceStartTimeString));
    }
  }

  const nPlMin = getNormalizedDate(plWindow.minDate);
  const nPlMax = getNormalizedDate(plWindow.maxDate);
  
  const ruleCount = generateCorrectionRules(nStart, nEnd, tDisturbance).length;

  for (let i = 0; i < ruleCount; i++) {
    const rules = generateCorrectionRules(nStart, nEnd, tDisturbance);
    const r = rules[i];
    if (r.condition) {
      nStart = getNormalizedDate(r.newStart);
      nEnd = getNormalizedDate(r.newEnd);
      tDisturbance = r.newDisturbance ? getNormalizedDate(r.newDisturbance) : tDisturbance;
      setDateTimeInputs(nStart, nEnd, tDisturbance);
      if (displayAutoCorrectionAlert) showAutoCorrectionAlert(r.message);
    }
  }

};

const initializeDateTimePickers = (powerloadData, defaultStartDate, defaultEndDate, defaultDisturbanceStartDate) => {
  
  const initTimePicker = (elId, defaultTime) => {
    const minTime = "00:00";
    const maxTime = "23:30";
    $(elId).timepicker({ timeFormat: "H\\:i", show2400: true, listWidth: 1, maxTime, minTime });
    $(elId).on("change", (e) => { // Fired by dropdown select + typing
      // Prevent entering > 59 minutes
      if (!e.target.value || !e.target.value.includes(":")) return;
      let [thisHours, thisMinutes] = e.target.value.split(":").map(v => parseInt(v));
      if (parseInt(thisMinutes) > 59) {
        e.target.value = thisHours + ":" + "59";
      }
      $(elId).trigger('change.powerloadValidation');
    });
    $(elId).val(defaultTime);
  };

  const initDatePicker = (elId, defaultDate) => {
    const minDate = new Date(0);
    const maxDate = new Date(8.64e15);
    if ($(elId).datepicker("option", "defaultDate")) {
      $(elId).datepicker("destroy");
    }
    $(elId).datepicker({
      altFormat: "mm/dd/yy",
      minDate, maxDate,
      defaultDate,
      constrainInput: true,
      onSelect: (newDate) => {
        if (typeof newDate !== "string") {
          newDate = getDateString(newDate)
        }
        $(elId).trigger('change.powerloadValidation');
      }
    });
  };

  const initDateTimePickers = (elDateId, defaultDate, elTimeId, fieldReference) => {
    $(elDateId).datepicker("destroy");
    $(elTimeId).timepicker("remove");
    const defaultTime = getTimeString({ date: defaultDate, withSeconds: false });
    $(elDateId).val(getDateString(defaultDate));
    $(elTimeId).val(defaultTime);
    initDatePicker(elDateId, defaultDate);
    initTimePicker(elTimeId, defaultTime);
    [$(elDateId), $(elTimeId)].forEach(function($el) {
      $el.off('change.powerloadValidation').on('change.powerloadValidation', function() {
        runValidation(lastChangedField = fieldReference);
      });
    });
    [$(elDateId), $(elTimeId)].forEach(function($el) {
      $el.prop("disabled", false);
    });
  };

  const runValidation = (lastChangedField=null, includeGraph=true, displayAutoCorrectionAlert=true) => {
    validatePowerloadDateTimeInputs(powerloadWindow, lastChangedField, displayAutoCorrectionAlert);
    updateDateTimePickers(powerloadWindow);
    if (typeof updatePowerloadGraph === "function" && includeGraph) {
      updatePowerloadGraph();
    }
  };

  const powerloadWindow = initializePowerloadWindow(powerloadData);
  const previousSelections = getFormDateTimes();

  if (!defaultStartDate) defaultStartDate = powerloadWindow.minDate;
  if (!defaultDisturbanceStartDate) {
    if (previousSelections.disturbanceStartDate) {
      defaultDisturbanceStartDate = previousSelections.disturbanceStartDate;
    } else {
      defaultDisturbanceStartDate = defaultStartDate;
    }
  }
  if (!defaultEndDate) defaultEndDate = powerloadWindow.maxDate;

  initDateTimePickers("#startdate", defaultStartDate, "#starttime", "start");
  initDateTimePickers("#enddate", defaultEndDate, "#endtime", "end");
  if (hasDisturbanceElements()) {
    initDateTimePickers("#disturbance_startdate", defaultDisturbanceStartDate, "#disturbance_starttime", "disturbance_start");
  }

  runValidation(includeGraph=false, displayAutoCorrectionAlert=false);

  return powerloadWindow;
};
