// Created by Frankie and Ahmet

const field_steps = {
    title: 0,
    category: 1,
    dates: 2,
    duration: 3,
    location: 4,
    days: 5,
    weeks: 6,
    description: 7,
    importance: 8,
};

let form, steps, prevBtn, nextBtn, skipBtn, submitBtn, cancelBtn;
let currentStep, progressEl, stepLabelEl;

const stepValidators = {
    [field_steps.title]: validateTitle,
    [field_steps.category]: validateCategory,
    [field_steps.dates]: validateDates,
    [field_steps.duration]: validateDuration,
    [field_steps.days]: validateRepeatDays,
};

function showError(message) {
    let errorEl = steps[currentStep].querySelector(".form-error");
    if (!errorEl) {
        errorEl = document.createElement("p");
        errorEl.className = "form-error";
        steps[currentStep].appendChild(errorEl);
    }
    errorEl.textContent = message;
}

function clearError() {
    const errorEl = steps[currentStep].querySelector(".form-error");
    if (errorEl) errorEl.textContent = "";
}

function updateProgress() {
    if (progressEl) {
        progressEl.innerHTML = '';
        steps.forEach(function (_, i) {
            const dot = document.createElement('div');
            dot.className = 'step-dot' + (i <= currentStep ? ' done' : '');
            progressEl.appendChild(dot);
        });
    }
    if (stepLabelEl) {
        stepLabelEl.textContent = 'Step ' + (currentStep + 1) + ' of ' + steps.length;
    }
}

function showStep(index) {
    steps.forEach(step => step.classList.remove("active"));
    if (steps[index]) steps[index].classList.add("active");
    clearError();
    updateButtons();
    updateProgress();
    applyCase1Lockout();
}


function getDates() {
    const start = modalBody.querySelector("[name='start_date']").value;
    const end = modalBody.querySelector("[name='end_date']").value;
    return { start, end };
}

function getTimes() {
    const start = modalBody.querySelector("[name='start_time']").value;
    const end = modalBody.querySelector("[name='end_time']").value;
    return { start, end };
}

function getDuration() {
    const hrs = modalBody.querySelector("[name='hours']").value;
    const mins = modalBody.querySelector("[name='minutes']").value;
    return { hrs, mins };
}

function getNumberOfDays() {
    return parseInt(modalBody.querySelector("[name='number_of_days']").value) || 0;
}

function getRepeatDays() {
    return modalBody.querySelectorAll("[name='repeat_days']:checked");
}

// Case 1: full start+end dates and times
function isCase1() {
    const { start: sd, end: ed } = getDates();
    const { start: st, end: et } = getTimes();
    return !!(sd && st && ed && et);
}

// Case 5: start+end times only, no dates
function isCase5() {
    const { start: sd, end: ed } = getDates();
    const { start: st, end: et } = getTimes();
    return !!(st && et && !sd && !ed);
}

// Duration auto-computed for Case 1 and Case 5
function durationIsAutoComputed() {
    return isCase1() || isCase5();
}

function datesAnyEntered() {
    const { start: sd, end: ed } = getDates();
    const { start: st, end: et } = getTimes();
    return !!(sd || st || ed || et);
}

function updateButtons() {
    const step = steps[currentStep];
    const optional = step.classList.contains("optional");

    prevBtn.style.display = currentStep === 0 ? "none" : "inline-block";
    submitBtn.style.display = currentStep === steps.length - 1 ? "inline-block" : "none";

    if (currentStep === field_steps.dates) {
        const anyEntered = datesAnyEntered();
        nextBtn.style.display = anyEntered ? "inline-block" : "none";
        skipBtn.style.display = anyEntered ? "none" : "inline-block";
    } else if (optional) {
        const input = step.querySelector("input, textarea, select");
        const hasValue = input && input.value.trim() !== "";
        nextBtn.style.display = hasValue ? "inline-block" : "none";
        skipBtn.style.display = hasValue ? "none" : "inline-block";
    } else {
        nextBtn.style.display = currentStep === steps.length - 1 ? "none" : "inline-block";
        skipBtn.style.display = "none";
    }
}

function validateTitle() {
    clearError();
    const title = modalBody.querySelector("[name='title']").value;
    if (!title) { showError("Title is required."); return false; }
    if (title.length > 50) { showError("Title is too long. Must be less than 50 characters."); return false; }
    return true;
}

function validateCategory() {
    clearError();
    const category = modalBody.querySelector("[name='category']").value;
    if (!category) { showError("You must provide a category."); return false; }
    return true;
}

function validateDates() {
    clearError();
    const { start: start_date, end: end_date } = getDates();
    const { start: start_time, end: end_time } = getTimes();

    if (!start_date && !start_time && !end_date && !end_time) return true;

    // Case 5: times only, no dates
    if (!start_date && start_time && !end_date && end_time) {
        const [sh, sm] = start_time.split(':').map(Number);
        const [eh, em] = end_time.split(':').map(Number);
        if (eh * 60 + em <= sh * 60 + sm) {
            showError("End time must be after start time.");
            return false;
        }
        return true;
    }

    if (!start_date && !end_date) {
        if (start_time && !end_time) { showError("Please provide an end time, or add a start date."); return false; }
        if (!start_time && end_time) { showError("Please provide a start time."); return false; }
    }

    if ((end_date || end_time) && !start_date && !start_time) {
        showError("Please provide a start date or time first.");
        return false;
    }

    if (start_date && end_date && !end_time) { showError("Please provide an end time."); return false; }
    if (start_date && !end_date && end_time) { showError("Please provide an end date."); return false; }

    if (start_date && (end_date || end_time) && !start_time) {
        showError("Please provide a start time when specifying an end date.");
        return false;
    }

    // Case 1: all four filled
    if (start_date && start_time && end_date && end_time) {
        const start = new Date(start_date + 'T' + start_time);
        const end   = new Date(end_date   + 'T' + end_time);
        if (end <= start) { showError("End date/time must be after start date/time."); return false; }
        return true;
    }

    if (start_date && start_time && !end_date && !end_time) return true;
    if (start_date && !start_time && !end_date && !end_time) return true;

    showError("Please complete the date fields or leave them all empty.");
    return false;
}

function validateDuration() {
    clearError();
    const { start: start_date, end: end_date } = getDates();
    const { hrs, mins } = getDuration();

    if (durationIsAutoComputed()) return true;

    if (!start_date && !end_date) {
        if (!hrs && !mins) {
            showError("You must provide a duration if no start/end date was given.");
            return false;
        }
    }

    if (hrs >= 24 || mins >= 60) {
        showError("Hours must be less than 24 and minutes less than 60.");
        return false;
    }

    return true;
}

function validateRepeatDays() {
    clearError();
    const numberOfDays = getNumberOfDays();

    if (!numberOfDays) { showError("You must specify how many days the event repeats."); return false; }

    const selected = getRepeatDays();
    if (selected.length === 0) return true;

    if (selected.length !== numberOfDays) {
        showError(`You selected ${selected.length} day(s) but number of days is set to ${numberOfDays}.`);
        return false;
    }

    // If a start date was given, the selected repeat days must include that weekday.
    // JS getDay(): 0=Sun,1=Mon,2=Tue,3=Wed,4=Thu,5=Fri,6=Sat
    // Bitmask:     SUN=64,MON=1,TUE=2,WED=4,THU=8,FRI=16,SAT=32
    const { start: start_date } = getDates();
    if (start_date) {
        const jsDay = new Date(start_date + 'T12:00:00').getDay();
        const dayBits = [64, 1, 2, 4, 8, 16, 32]; // indexed by JS getDay()
        const startBit = dayBits[jsDay];
        const selectedBits = Array.from(selected).map(cb => parseInt(cb.value));
        if (!selectedBits.includes(startBit)) {
            const dayNames = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
            showError(`Your start date is a ${dayNames[jsDay]}, so the repeat days must include ${dayNames[jsDay]}.`);
            return false;
        }
    }

    return true;
}

function enforceDayLimit() {
    const limit = getNumberOfDays();
    const allBoxes = modalBody.querySelectorAll("[name='repeat_days']");
    const checkedCount = [...allBoxes].filter(cb => cb.checked).length;
    allBoxes.forEach(cb => {
        if (!cb.checked) cb.disabled = limit > 0 && checkedCount >= limit;
    });
}

// Case 1 one-off events (full start+end date+time) are pinned to a single
// moment, so the Repeat + Weeks fields can't mean anything. Lock them to 1
// with the event's own weekday pre-checked, and drop a hint on each step
// explaining why the inputs are disabled.
function applyCase1Lockout() {
    const locked = isCase1();
    const days = modalBody.querySelector("[name='number_of_days']");
    const weeks = modalBody.querySelector("[name='repeat_weeks']");
    const boxes = modalBody.querySelectorAll("[name='repeat_days']");

    // Tag each locked field with data-case1-locked so onSubmit can re-enable
    // them just before FormData serialisation (disabled inputs don't submit).
    if (days) {
        days.disabled = locked;
        days.dataset.case1Locked = locked ? 'true' : 'false';
        if (locked) days.value = 1;
    }
    if (weeks) {
        weeks.disabled = locked;
        weeks.dataset.case1Locked = locked ? 'true' : 'false';
        if (locked) weeks.value = 1;
    }

    // Work out which weekday bit the start date falls on so we can pre-tick it
    const { start: sd } = getDates();
    const startBit = sd ? [64, 1, 2, 4, 8, 16, 32][new Date(sd + 'T12:00:00').getDay()] : null;

    boxes.forEach(cb => {
        if (locked) {
            cb.checked = startBit != null && parseInt(cb.value) === startBit;
            cb.disabled = true;
            cb.dataset.case1Locked = 'true';
        } else {
            cb.disabled = false;
            cb.dataset.case1Locked = 'false';
        }
    });

    // Drop a small hint on the Repeat and Weeks steps when locked — tells the
    // user why the inputs are pre-filled and disabled (a fully-fixed event
    // only happens once, so repeats don't apply).
    const daysStep = steps && steps[field_steps.days];
    const weeksStep = steps && steps[field_steps.weeks];
    const hintText = "This event has a fixed date and time, so it only happens once and can't repeat. Fields locked.";
    [daysStep, weeksStep].forEach(step => {
        if (!step) return;
        const existing = step.querySelector(".case1-hint");
        if (locked && !existing) {
            const hint = document.createElement("p");
            hint.className = "case1-hint form-error";
            hint.textContent = hintText;
            step.appendChild(hint);
        } else if (!locked && existing) {
            existing.remove();
        }
    });
}


function bindDayLimitEnforcement() {
    const numDaysInput = modalBody.querySelector("[name='number_of_days']");
    if (numDaysInput) {
        numDaysInput.addEventListener("input", () => {
            modalBody.querySelectorAll("[name='repeat_days']").forEach(cb => {
                cb.checked = false;
                cb.disabled = false;
            });
            enforceDayLimit();
        });
    }
    modalBody.querySelectorAll("[name='repeat_days']").forEach(cb => {
        cb.addEventListener("change", enforceDayLimit);
    });
}

function onKeyDown(e) {
    if (modal.classList.contains("hidden")) return;
    if (e.key !== "Enter") return;
    if (e.target.tagName === "TEXTAREA") return; // Lets users use the enter key on the description field to move to the next line
    e.preventDefault();
    if (currentStep === steps.length - 1) { submitBtn.click(); return; }
    if (currentStep === field_steps.dates) { datesAnyEntered() ? nextBtn.click() : skipBtn.click(); return; }
    if (steps[currentStep].classList.contains("optional")) {
        const input = steps[currentStep].querySelector("input, textarea, select");
        (input && input.value.trim() !== "") ? nextBtn.click() : skipBtn.click();
        return;
    }
    nextBtn.click();
}

function onNext() {
    const validator = stepValidators[currentStep];
    if (validator && !validator()) return;
    // Skip duration step when auto-computed (Case 1 / Case 5)
    if (currentStep === field_steps.dates && durationIsAutoComputed()) {
        currentStep = field_steps.duration + 1;
        showStep(currentStep);
        return;
    }
    if (currentStep < steps.length - 1) { currentStep++; showStep(currentStep); }
}


function onSkip() {
    currentStep++;
    showStep(currentStep);
}

function onPrev() {
    if (currentStep === 0) return;
    // Jump back over skipped duration step
    if (currentStep === field_steps.duration + 1 && durationIsAutoComputed()) {
        currentStep -= 2;
    } else {
        currentStep--;
    }
    showStep(currentStep);
}


function onCancel() {
    modal.classList.add("hidden");
    if (form) form.reset();
    currentStep = field_steps.title;
    showStep(currentStep);
}

async function onSubmit(e) {
    e.preventDefault();
    if (currentStep !== steps.length - 1) return;

    // Re-enable Case 1 locked fields so their values (days=1, weeks=1, the
    // correct weekday) actually serialise into FormData. Disabled inputs are
    // silently dropped by the browser, which makes the server reject the form
    // and bounces the user back to step 0.
    const locked = form.querySelectorAll('[data-case1-locked="true"]');
    locked.forEach(f => { f.disabled = false; });

    const res = await fetch(form.action, {
        method: "POST",
        headers: { "X-Requested-With": "XMLHttpRequest" },
        body: new FormData(form),
    });

    // Re-apply the lockout immediately so the fields stay disabled in the UI
    // in case the form is still showing (non-redirect error response below).
    locked.forEach(f => { f.disabled = true; });

    if (res.redirected) { modal.classList.add("hidden"); location.reload(); return; }
    modalBody.innerHTML = await res.text();
    initializeEventForm();
}

function initializeEventForm() {
    form = modalBody.querySelector("form");
    steps = modalBody.querySelectorAll(".form-step");
    prevBtn = modalBody.querySelector(".prev-btn");
    nextBtn = modalBody.querySelector(".next-btn");
    skipBtn = modalBody.querySelector(".skip-btn");
    submitBtn = modalBody.querySelector(".submit-btn");
    cancelBtn = modalBody.querySelector(".cancel-btn");
    progressEl = modalBody.querySelector("#stepProgress");
    stepLabelEl = modalBody.querySelector("#stepLabel");
    currentStep = field_steps.title;
    bindDayLimitEnforcement();
    document.addEventListener("keydown", onKeyDown);
    nextBtn.addEventListener("click", onNext);
    skipBtn.addEventListener("click", onSkip);
    prevBtn.addEventListener("click", onPrev);
    cancelBtn.addEventListener("click", onCancel);
    form.addEventListener("submit", onSubmit);
    ["start_date", "start_time", "end_date", "end_time", "location", "description"].forEach(name => modalBody.querySelector(`[name='${name}']`)?.addEventListener("input", updateButtons));
    showStep(currentStep);
}
