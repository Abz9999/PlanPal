// Khan - Smart Planner JavaScript
// Controls the 2-step Smart Planner popup wizard.
// Step 1: user sets constraints (dates, times, buffer, days)
// Step 2: user picks which events to smart plan

// Khan - Track which step we're currently on (1 or 2)
let spCurrentStep = 1;

// Khan - Tracks the keep/erase choice ('keep' or 'erase')
let spKeepOrErase = 'keep';

// Khan - Stores all events fetched from the server so we can filter them in JS
let spAllEvents = [];

// Ashrith - stores the result from /smart-plan/generate/ so Task 9 can render it
let spLastPlanResult = null;

// Ashrith - slide list built from the algorithm result (week slides + summary slide)

let spSlides = [];

// Ashrith - index of the slide on the screen

let spCurrentSlide = 0;

// Khan - OPEN AND CLOSE

// Khan - Opens the Smart Planner popup and resets everything to a clean state
function openSmartPlanner() {
    // Set the minimum allowed start date to tomorrow
    // (we don't allow today so we always start with a clean full day)
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const tomorrowStr = tomorrow.toISOString().split('T')[0];

    const startInput = document.getElementById('sp-start-date');
    const endInput   = document.getElementById('sp-end-date');

    startInput.min   = tomorrowStr;
    startInput.value = tomorrowStr;

    // Khan - Default end date is 2 weeks from tomorrow
    const twoWeeks = new Date(tomorrow);
    twoWeeks.setDate(twoWeeks.getDate() + 14);

    // Khan - Max end date is 10 weeks (70 days) from tomorrow
    const tenWeeks = new Date(tomorrow);
    tenWeeks.setDate(tenWeeks.getDate() + 70);

    endInput.min   = tomorrowStr;
    endInput.max   = tenWeeks.toISOString().split('T')[0];
    endInput.value = twoWeeks.toISOString().split('T')[0];

    // Reset everything back to step 1 clean state
    spGoToStep(1);
    document.getElementById('sp-step1-error').classList.remove('visible');

    // Show the modal overlay
    document.getElementById('smartPlannerModal').classList.remove('hidden');
}

// Khan - Closes the popup and discards everything - nothing is saved
function closeSmartPlanner() {
    document.getElementById('smartPlannerModal').classList.add('hidden');
    spCurrentStep  = 1;
    spKeepOrErase  = 'keep';
    spAllEvents    = [];
}

// Khan - STEP NAVIGATION

// Khan - Navigate to a specific step number and update the UI accordingly
function spGoToStep(stepNum) {
    spCurrentStep = stepNum;

    // Hide all steps, then show only the current one
    document.querySelectorAll('.sp-step').forEach(function(el) {
        el.classList.remove('active');
    });
    document.getElementById('sp-step-' + stepNum).classList.add('active');

    // Update the progress bar dots at the top
    document.getElementById('sp-dot-1').classList.toggle('done', stepNum >= 1);
    document.getElementById('sp-dot-2').classList.toggle('done', stepNum >= 2);

    // Show/hide the Back button (only visible on step 2)
    const backBtn = document.getElementById('sp-back-btn');
    backBtn.style.display = (stepNum > 1) ? 'inline-block' : 'none';

    // Change label of Next button on last step
    const nextBtn = document.getElementById('sp-next-btn');
    nextBtn.textContent = (stepNum === 2) ? 'Generate Plan' : 'Next →';
}

// Khan - Called when user clicks the Next / Generate Plan button
function spNext() {
    if (spCurrentStep === 1) {
        // Validate step 1 before moving on
        if (!spValidateStep1()) return;
        spGoToStep(2);
        spLoadEvents(); // Fetch events from server when landing on step 2
    } else if (spCurrentStep === 2) {
        // Khan - Make sure at least one event is ticked before we do anything
        const selectedIds = spGetSelectedEventIds();
        if (selectedIds.length === 0) {
            alert('Please select at least one event to smart plan.');
            return;
        }
        // Khan - Run the Task 6 pre-check sanity calculation
        spRunPreCheck(selectedIds);
    }

}

// Khan - Called when user clicks the Back button
function spBack() {
    if (spCurrentStep === 2) {
        spGoToStep(1);
    }
}

// Khan - STEP 1: CONSTRAINT INPUTS

// Khan - Toggle the keep/erase selection when user clicks one of the two panels
function spSetKeepErase(choice) {
    spKeepOrErase = choice;
    document.getElementById('sp-keep-btn').classList.toggle('selected', choice === 'keep');
    document.getElementById('sp-erase-btn').classList.toggle('selected', choice === 'erase');
}

// Khan - Wire up the day pill toggles
// Each day pill is a <label> - clicking it toggles the hidden checkbox + the .selected style
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.sp-day-pill').forEach(function(pill) {
        pill.addEventListener('click', function() {
            const checkbox = this.querySelector('input[type="checkbox"]');
            checkbox.checked = !checkbox.checked;
            this.classList.toggle('selected', checkbox.checked);
        });
    });
});

// Khan - Validates all Step 1 fields before letting the user proceed to Step 2
// Returns true if everything is valid, false if there's a problem
function spValidateStep1() {
    const errorEl = document.getElementById('sp-step1-error');
    errorEl.classList.remove('visible');

    const startDate = document.getElementById('sp-start-date').value;
    const endDate   = document.getElementById('sp-end-date').value;
    const dayStart  = document.getElementById('sp-day-start').value;
    const dayEnd    = document.getElementById('sp-day-end').value;

    // Khan - Both dates must be picked
    if (!startDate || !endDate) {
        errorEl.textContent = 'Please select both a start and end date.';
        errorEl.classList.add('visible');
        return false;
    }

    // Khan - Start date must be tomorrow or later (today is blocked)
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const start = new Date(startDate + 'T00:00:00');
    if (start <= today) {
        errorEl.textContent = 'Start date must be tomorrow or later — today is not allowed.';
        errorEl.classList.add('visible');
        return false;
    }

    // Khan - End date cannot be before the start date (same day is fine = 1 day of planning)
    const end = new Date(endDate + 'T00:00:00');
    if (end < start) {
        errorEl.textContent = 'End date cannot be before the start date.';
        errorEl.classList.add('visible');
        return false;
    }


    // Khan - Maximum planning range is 10 weeks (70 days)
    const diffDays = (end - start) / (1000 * 60 * 60 * 24);
    if (diffDays > 70) {
        errorEl.textContent = 'Date range cannot exceed 10 weeks (70 days).';
        errorEl.classList.add('visible');
        return false;
    }

    // Khan - Both time inputs must be filled in
    if (!dayStart || !dayEnd) {
        errorEl.textContent = 'Please set both a day start time and end time.';
        errorEl.classList.add('visible');
        return false;
    }

    // Khan - Day start must be before day end
    if (dayStart >= dayEnd) {
        errorEl.textContent = 'Day start time must be earlier than the end time.';
        errorEl.classList.add('visible');
        return false;
    }

    // Khan - At least one day must be selected
    const checkedDays = document.querySelectorAll('.sp-day-pill input[type="checkbox"]:checked');
    if (checkedDays.length === 0) {
        errorEl.textContent = 'Please select at least one active day.';
        errorEl.classList.add('visible');
        return false;
    }

    return true; // All good - proceed to step 2
}

// Khan - Collects all Step 1 values into one neat object
// This gets passed to the algorithm in Task 8
function spGetConstraints() {
    // Khan - Add up the bitmask values for all ticked day pills
    // Mon=1, Tue=2, Wed=4, Thu=8, Fri=16, Sat=32, Sun=64
    let daysBitmask = 0;
    document.querySelectorAll('.sp-day-pill input[type="checkbox"]:checked').forEach(function(cb) {
        daysBitmask += parseInt(cb.value);
    });

    return {
        start_date:           document.getElementById('sp-start-date').value,
        end_date:             document.getElementById('sp-end-date').value,
        day_start:            document.getElementById('sp-day-start').value,
        day_end:              document.getElementById('sp-day-end').value,
        buffer_minutes:       parseInt(document.getElementById('sp-buffer').value),
        selected_days_bitmask: daysBitmask,
        keep_or_erase:        spKeepOrErase,
    };
}

// Khan - STEP 2: EVENT SELECTION

// Khan - Fetches all the user's event templates from the backend
// Called automatically when step 2 is first opened
function spLoadEvents() {
    const listEl = document.getElementById('sp-event-list');
    // Safety check: if the list element doesnt exist in the HTML, stop here
    // This prevents a cryptic null crash if the HTML is accidentally broken
    if (!listEl) {
        console.error('Smart Planner: sp-event-list element not found in HTML');
        return;
    }
    listEl.innerHTML = '<div class="sp-empty-msg">Loading your events...</div>';

    fetch('/smart-plan/events/')
        .then(function(resp) {
            if (!resp.ok) throw new Error('Server returned ' + resp.status);
            return resp.json();
        })
        .then(function(data) {
            spAllEvents = data.events;
            spBuildCategoryFilter(data.events); // fill the category dropdown
            spRenderEvents(data.events);         // render all events
        })
        .catch(function(err) {
            listEl.innerHTML = '<div class="sp-empty-msg">Failed to load events. Please try again.</div>';
            console.error('Smart Planner: event load failed', err);
        });
}

// Khan - Fills the category filter dropdown with all unique categories
// from the events that were returned by the server
function spBuildCategoryFilter(events) {
    const select = document.getElementById('sp-category-filter');
    // Keep the first "All Categories" option, remove any previously added ones
    select.innerHTML = '<option value="all">All Categories</option>';

    const seen = {};
    events.forEach(function(ev) {
        if (ev.category_id && !seen[ev.category_id]) {
            seen[ev.category_id] = true;
            const opt = document.createElement('option');
            opt.value       = ev.category_id;
            opt.textContent = ev.category_name;
            select.appendChild(opt);
        }
    });
}

// Khan - Called whenever the category filter or search bar changes
// Filters spAllEvents and re-renders only the matching ones
function spFilterEvents() {
    spResetSelectAll(); // Khan - reset the "All" checkbox whenever the list changes
    const catFilter  = document.getElementById('sp-category-filter').value;
    const searchText = document.getElementById('sp-search').value.toLowerCase().trim();

    const filtered = spAllEvents.filter(function(ev) {
        const catMatch   = (catFilter === 'all') || (String(ev.category_id) === catFilter);
        const titleMatch = !searchText || ev.title.toLowerCase().includes(searchText);
        return catMatch && titleMatch;
    });

    spRenderEvents(filtered);
}

// Khan - Renders a list of event rows into the event list container
function spRenderEvents(events) {
    const listEl = document.getElementById('sp-event-list');

    if (events.length === 0) {
        listEl.innerHTML = '<div class="sp-empty-msg">No events found.</div>';
        return;
    }

    listEl.innerHTML = '';
    events.forEach(function(ev) {
        listEl.appendChild(spBuildEventRow(ev));
    });
}

// Khan - Builds one event row element: mini card + 4 counters + checkbox
// Matches the importance border colour and category background from the dashboard
function spBuildEventRow(ev) {
    // Khan - Map importance number to border colour
    // This matches exactly what event_card.html does in the dashboard
    const impColours = {
        5: '#c53030',  // Very Low - red border (matches dashboard)
        4: '#c05621',  // Low - orange border
        3: '#b7791f',  // Medium - amber border
        2: '#276749',  // High - green border
        1: '#2b6cb0',  // Critical - blue border
    };
    const borderCol = impColours[ev.importance] || '#cccccc';

    // Khan - Category background at ~12% opacity (append "20" to 6-digit hex)
    const bgCol = (ev.category_colour || '#888888') + '20';

    // Khan - duration_display now covers both flexible and fixed events from the backend
    // Fixed events show e.g. "1 hr · Fixed", flexible show e.g. "1 hr 30 mins"
    const durationStr = ev.duration_display || 'Duration unknown'

    const row = document.createElement('div');
    row.className         = 'sp-event-row';
    row.dataset.eventId   = ev.id;
    row.dataset.categoryId = ev.category_id;
    row.dataset.title     = ev.title.toLowerCase(); // used for search filtering

    row.innerHTML = `
        <div class="sp-card-area"
             style="background:${bgCol}; border-left-color:${borderCol};"
             onclick="spOpenInstancesPopup(${ev.id}, '${ev.title.replace(/'/g, "\\'")}')">
            <div class="sp-card-title">${ev.title}</div>
            <div class="sp-card-meta">${ev.category_name} &bull; ${durationStr}</div>
        </div>

        <div class="sp-counters">
            <div class="sp-counter-item">
                <div class="sp-dot created"></div>
                <span>${ev.created_count} created</span>
            </div>
            <div class="sp-counter-item">
                <div class="sp-dot scheduled"></div>
                <span>${ev.scheduled_count} scheduled</span>
            </div>
            <div class="sp-counter-item">
                <div class="sp-dot completed"></div>
                <span>${ev.completed_count} completed</span>
            </div>
            <div class="sp-counter-item">
                <div class="sp-dot missed"></div>
                <span>${ev.missed_count} missed</span>
            </div>
        </div>

        <div class="sp-cb-wrap">
            <input type="checkbox"
                   id="sp-cb-${ev.id}"
                   value="${ev.id}"
                   onchange="spToggleSelected(this)">
        </div>
    `;

    return row;
}

// Khan - When user ticks/unticks a checkbox, highlight the whole row
function spToggleSelected(checkbox) {
    const row = checkbox.closest('.sp-event-row');
    row.classList.toggle('sp-selected', checkbox.checked);
}

// Khan - Returns an array of event IDs that the user has ticked
function spGetSelectedEventIds() {
    const checked = document.querySelectorAll('#sp-event-list input[type="checkbox"]:checked');
    return Array.from(checked).map(function(cb) { return parseInt(cb.value); });
}

// Khan - INSTANCES POPUP (mini version for step 2)
// Clicking an event card in step 2 shows its instances
// Uses the same /event/<id>/instances/ endpoint as the dashboard

// Khan - Fetches instance data from the server then shows the popup
function spOpenInstancesPopup(eventId, eventTitle) {
    fetch('/event/' + eventId + '/instances/')
        .then(function(resp) {
            if (!resp.ok) throw new Error('Server error');
            return resp.json();
        })
        .then(function(data) {
            spShowInstancesModal(data, eventTitle);
        })
        .catch(function(err) {
            console.error('Smart Planner: could not load instances', err);
        });
}

// Khan - Builds and injects a simple instances list popup above the smart planner
function spShowInstancesModal(data, eventTitle) {
    // Remove any existing instances popup first (avoid duplicates)
    const existing = document.getElementById('sp-instances-overlay');
    if (existing) existing.remove();

    // Khan - Status labels and colours for each instance status code
    const statusMap = {
        1: { label: 'Created',   colour: '#888888' },
        2: { label: 'Scheduled', colour: '#1a73e8' },
        3: { label: 'Completed', colour: '#276749' },
        4: { label: 'Missed',    colour: '#c53030' },
    };

    // Khan - Build the list of instance rows
    let instancesHtml = '';
    const instances = data.instances || [];
    if (instances.length > 0) {
        instances.forEach(function(inst) {
            const s = statusMap[inst.status] || statusMap[1];
            // Show placed time if scheduled, otherwise 'Not placed yet'
            // Khan - Server already returns nicely formatted strings, use them directly
            // placed_start = "28 Feb 2026, 10:30", placed_end = "11:30"
            // Old code was slicing the string and cutting it off at 16 chars = "28 Feb 2026, 10:"
            let timeStr = 'Not placed yet';
            if (inst.placed_start) {
                timeStr = inst.placed_start;
                if (inst.placed_end) {
                    timeStr += ' \u2192 ' + inst.placed_end; // → arrow between start and end time
                }
            }


            instancesHtml += `
                <div style="display:flex;align-items:center;gap:10px;
                            padding:9px 0;border-bottom:1px solid #f0f0f0;">
                    <span style="font-size:11px;font-weight:600;color:#aaa;
                                 min-width:28px;">#${inst.occurrence_index}</span>
                    <span style="flex:1;font-size:13px;color:#111;">${timeStr}</span>
                    <span style="font-size:11px;font-weight:600;
                                 color:${s.colour};padding:2px 9px;
                                 border-radius:10px;background:${s.colour}20;">
                        ${s.label}
                    </span>
                </div>
            `;
        });
    } else {
        instancesHtml = '<div style="text-align:center;color:#888;padding:20px;">No instances found.</div>';
    }

    // Khan - Build the full overlay and modal box
    const overlay = document.createElement('div');
    overlay.id = 'sp-instances-overlay';
    overlay.style.cssText = [
        'position:fixed', 'inset:0',
        'background:rgba(0,0,0,0.45)',
        'display:flex', 'justify-content:center', 'align-items:center',
        'z-index:1100'   // sits above the smart planner modal (z-index 1000)
    ].join(';');

    overlay.innerHTML = `
        <div style="background:#fff;border-radius:16px;
                    box-shadow:0 8px 40px rgba(0,0,0,0.2);
                    width:460px;max-width:95vw;max-height:75vh;
                    display:flex;flex-direction:column;overflow:hidden;">

            <div style="padding:18px 22px 14px;
                        display:flex;align-items:center;
                        justify-content:space-between;
                        border-bottom:1px solid #f0f0f0;">
                <h3 style="margin:0;font-size:16px;font-weight:600;">
                    ${eventTitle} — Instances
                </h3>
                <button onclick="document.getElementById('sp-instances-overlay').remove();"
                        style="background:none;border:none;font-size:18px;
                               color:#888;cursor:pointer;padding:4px 8px;
                               border-radius:4px;">&#x2715;</button>
            </div>

            <div style="padding:4px 22px 16px;overflow-y:auto;flex:1;">
                ${instancesHtml}
            </div>
        </div>
    `;

    // Khan - Click outside the box to close the instances popup
    overlay.addEventListener('click', function(e) {
        if (e.target === overlay) overlay.remove();
    });

    document.body.appendChild(overlay);
}

// Khan - SELECT ALL / DESELECT ALL (Step 2)

// Khan - Called when the "All" checkbox in the filter bar is ticked or unticked
// Ticking it: checks all currently visible event rows
// Unticking it: unchecks all currently visible event rows
function spToggleSelectAll(checkbox) {
    const isChecked = checkbox.checked;
    // Khan - Only affect the rows currently visible in the list (respects current filter/search)
    const rows = document.querySelectorAll('#sp-event-list .sp-event-row');
    rows.forEach(function(row) {
        const cb = row.querySelector('input[type="checkbox"]');
        if (cb) {
            cb.checked = isChecked;
            row.classList.toggle('sp-selected', isChecked);
        }
    });
}

// Khan - Resets the select-all checkbox back to unchecked
// Called whenever the visible list changes (filter or search changed)
function spResetSelectAll() {
    const selectAll = document.getElementById('sp-select-all');
    if (selectAll) selectAll.checked = false;
}

// Khan - INITIALISE: Wire up buttons when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Khan - Smart Plan button on toolbar opens the modal
    const smartPlanBtn = document.getElementById('btn-smart-plan');
    if (smartPlanBtn) {
        smartPlanBtn.addEventListener('click', openSmartPlanner);
    }

    // Khan - X button in top right corner closes the modal
    document.getElementById('sp-close-btn').addEventListener('click', closeSmartPlanner);

    // Khan - Clicking the dark background outside the box also closes it
    document.getElementById('smartPlannerModal').addEventListener('click', function(e) {
        if (e.target === this) closeSmartPlanner();
    });

    // Khan - When user changes start date, update the max allowed end date
    // so the browser greys out dates beyond 10 weeks from the new start.
    // Attached once on DOMContentLoaded (not nested inside the modal click handler).
    document.getElementById('sp-start-date').addEventListener('change', function() {
        const startVal = this.value;
        if (!startVal) return;

        const startDate = new Date(startVal + 'T00:00:00');

        // Khan - Calculate the max end date = start + 70 days (10 weeks)
        const maxEnd = new Date(startDate);
        maxEnd.setDate(maxEnd.getDate() + 70);
        const maxEndStr = maxEnd.toISOString().split('T')[0];

        const endInput = document.getElementById('sp-end-date');
        endInput.min = startVal;
        endInput.max = maxEndStr;

        // Khan - If end date is now beyond the new max, pull it back to the max
        if (endInput.value > maxEndStr) {
            endInput.value = maxEndStr;
        }

        // Khan - If end date is before the new start, set it to start + 14 days
        const twoWeeks = new Date(startDate);
        twoWeeks.setDate(twoWeeks.getDate() + 14);
        const twoWeeksStr = twoWeeks.toISOString().split('T')[0];

        if (!endInput.value || endInput.value < startVal) {
            endInput.value = twoWeeksStr > maxEndStr ? maxEndStr : twoWeeksStr;
        }
    });
});

// ============================================================
// Khan - TASK 6: PRE-CHECK SANITY CALCULATION
// Runs before the algorithm to check if all instances can
// realistically fit in the time window the user has given us.
// If required time > available time, show a warning overlay.
// Otherwise go straight to the algorithm.
// ============================================================

// Khan - Helper: counts how many 1-bits are in a number
// Used to count selected days from the bitmask (e.g. Mon+Wed+Fri = 0b0010101 = 3 bits)
function spCountBits(n) {
    let count = 0;
    while (n > 0) {
        count += n & 1;   // check the lowest bit
        n >>= 1;          // shift right to check the next bit
    }
    return count;
}

// Khan - Helper: converts a "HH:MM" time string into minutes from midnight
// e.g. "08:30" -> 510 minutes,  "22:00" -> 1320 minutes
function spTimeToMinutes(timeStr) {
    const parts = timeStr.split(':');
    return parseInt(parts[0]) * 60 + parseInt(parts[1]);
}

// Khan - Helper: turns a raw minutes number into a readable string
// e.g. 210 -> "3 hrs 30 mins",  60 -> "1 hr",  45 -> "45 mins"
function spFormatMinutes(mins) {
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    if (h === 0)  return m + ' mins';
    if (m === 0)  return h + ' hr' + (h > 1 ? 's' : '');
    return h + ' hr' + (h > 1 ? 's' : '') + ' ' + m + ' mins';
}

// Khan - Counts how many actual calendar days in the date range fall on a selected active day
// e.g. if range is Mon 15th to Wed 17th, and user picked Mon+Wed, this returns 2
// This is the CORRECT way to get available time - not days_per_week × weeks formula
function spCountValidDaysInRange(startDateStr, endDateStr, selectedDaysBitmask) {
    // Khan - JS getDay() gives: 0=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat
    // Our bitmask uses:          Sun=64, Mon=1, Tue=2, Wed=4, Thu=8, Fri=16, Sat=32
    // This array lets us convert: jsDayToBitmask[0] = 64 (Sun), jsDayToBitmask[1] = 1 (Mon) etc.
    const jsDayToBitmask = [64, 1, 2, 4, 8, 16, 32];

    const start   = new Date(startDateStr + 'T00:00:00');
    const end     = new Date(endDateStr   + 'T00:00:00');
    const current = new Date(start);
    let count     = 0;

    // Khan - Walk day by day through the range, count only the selected active days
    while (current <= end) {
        const jsDay  = current.getDay();           // which day of week is this? (0-6)
        const bitval = jsDayToBitmask[jsDay];      // convert to our bitmask value
        if (selectedDaysBitmask & bitval) {        // is this day ticked in the day selector?
            count++;
        }
        current.setDate(current.getDate() + 1);    // move to next day
    }

    return count;
}

// Khan - Main pre-check function
// Figures out if the selected events can all fit in the user's given time window.
// Uses accurate day counting - walks through every day in the date range.
function spRunPreCheck(selectedIds) {
    const constraints = spGetConstraints();

    // Khan - Get only the events the user has ticked
    const selectedEvents = spAllEvents.filter(function(ev) {
        return selectedIds.indexOf(ev.id) !== -1;
    });

    // Khan - Include ALL events that have a known duration in minutes
    // Fixed events now return duration_minutes from the backend (derived from start/end)
    // Flexible events already have it from the duration field
    const eventsWithDuration = selectedEvents.filter(function(ev) {
        return ev.duration_minutes !== null && ev.duration_minutes > 0;
    });

    // Khan - Count total instances we're trying to place
    // In erase mode: scheduled instances get flipped back to created, so count both
    // In keep mode: only unplaced (created) instances matter
    let totalInstances = 0;
    eventsWithDuration.forEach(function(ev) {
        if (constraints.keep_or_erase === 'erase') {
            totalInstances += ev.created_count + ev.scheduled_count;
        } else {
            totalInstances += ev.created_count;
        }
    });

    // Khan - If nothing to place (e.g. only events with no duration selected), skip check
    if (totalInstances === 0) {
        spProceedToGenerate();
        return;
    }

    // Khan - STEP 1: Total time REQUIRED (in minutes)
    // = sum of (duration × instance count) for all selected events with a duration
    // + buffer gaps between every consecutive pair of instances
    let totalEventMinutes = 0;
    eventsWithDuration.forEach(function(ev) {
        const count = (constraints.keep_or_erase === 'erase')
            ? ev.created_count + ev.scheduled_count
            : ev.created_count;
        totalEventMinutes += ev.duration_minutes * count;
    });

    // Khan - N instances need N-1 buffer gaps between them
    const bufferMins         = constraints.buffer_minutes;
    const totalBufferMinutes = bufferMins * Math.max(0, totalInstances - 1);
    const totalRequiredMinutes = totalEventMinutes + totalBufferMinutes;

    // Khan - STEP 2: Total time AVAILABLE (in minutes)
    // Count only the actual days in the date range that fall on a user-selected active day
    // e.g. range is Mon 15 to Wed 17, active days = Mon+Wed → 2 valid days
    const validDays         = spCountValidDaysInRange(
        constraints.start_date,
        constraints.end_date,
        constraints.selected_days_bitmask
    );
    const dailyWindowMins   = spTimeToMinutes(constraints.day_end) - spTimeToMinutes(constraints.day_start);
    const totalAvailableMinutes = validDays * dailyWindowMins;

    // Khan - STEP 3: THE DECISION
    // If required time is more than available time, show the warning popup.
    // Otherwise everything fits in theory — go straight to the algorithm.
    if (totalRequiredMinutes > totalAvailableMinutes) {
        const overflowMins       = totalRequiredMinutes - totalAvailableMinutes;
        const avgMinsPerInstance = totalRequiredMinutes / totalInstances;
        const estimatedUnfit     = Math.min(
            totalInstances,
            Math.ceil(overflowMins / avgMinsPerInstance)
        );
        spShowPreCheckWarning({
            totalInstances:        totalInstances,
            totalRequiredMinutes:  totalRequiredMinutes,
            totalAvailableMinutes: totalAvailableMinutes,
            estimatedUnfit:        estimatedUnfit,
        });
    } else {
        // Khan - Enough time for everything, skip warning and run algorithm
        spProceedToGenerate();
    }
}

// Khan - Fills in the stats on the warning overlay and shows it
function spShowPreCheckWarning(stats) {
    // Khan - Fill the stat values in the overlay HTML
    document.getElementById('sp-pc-required').textContent  = spFormatMinutes(stats.totalRequiredMinutes);
    document.getElementById('sp-pc-available').textContent = spFormatMinutes(stats.totalAvailableMinutes);
    document.getElementById('sp-pc-unfit').textContent     = stats.estimatedUnfit;
    document.getElementById('sp-pc-total').textContent     = stats.totalInstances;

    // Khan - Reveal the overlay (remove the .hidden class)
    document.getElementById('sp-precheck-overlay').classList.remove('hidden');
}

// Khan - Called when user clicks "Change Constraints" on the warning overlay
// Hides the warning and drops the user back to Step 1 so they can adjust
function spPreCheckGoBack() {
    document.getElementById('sp-precheck-overlay').classList.add('hidden');
    spGoToStep(1);  // go back to constraints step
}

// Khan - Called when user clicks "Continue Anyway" on the warning overlay
// Hides the warning and runs the algorithm regardless
function spPreCheckContinue() {
    document.getElementById('sp-precheck-overlay').classList.add('hidden');
    spProceedToGenerate();
}

// Khan - Shows the loading overlay - called just before the algorithm fetch (Task 8)
// Once visible, the overlay blocks all mouse clicks until hidden again
function spShowLoadingOverlay() {
    document.getElementById('sp-loading-overlay').classList.remove('hidden');
}

// Khan - Hides the loading overlay - called by Task 8 once the response comes back
function spHideLoadingOverlay() {
    document.getElementById('sp-loading-overlay').classList.add('hidden');
}

// Read the csrftoken cookie set by Django so fetch() requests can include it in the
// X-CSRFToken header. Returns empty string if the cookie is missing (Django will then
// reject the request with 403, which makes the problem visible).
function spGetCsrfToken() {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.startsWith('csrftoken=')) {
            return cookie.substring('csrftoken='.length);
        }
    }
    return '';
}

// Ashrith - Entry point: called after the pre-check passes (or user skips the warning).
// JS calls the backend algorithm endpoint.
// waits for the response, then passes the result to spShowPreview() 

function spProceedToGenerate() {

    // Loading spinner will show to block the UI while the server generates the plan
    spShowLoadingOverlay();

    
    const constraints = spGetConstraints();
    const selectedIds = spGetSelectedEventIds();

    const csrfToken = spGetCsrfToken();

    // POST to the generate endpoint
    fetch('/smart-plan/generate/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({
            constraints: constraints,
            selected_template_ids: selectedIds,
        }),
    })
    .then(function(resp) {
        // If the server returned an error status, throw so we hit .catch
        if (!resp.ok) throw new Error('Server returned ' + resp.status);
        return resp.json();
    })
    .then(function(data) {
        // Algorithm finished successfully - hide the loading spinner
        spHideLoadingOverlay();

        // Save the result so preview UI can access it
        spLastPlanResult = data;

        // preview slide UI will replace spShowPreview 
        spShowPreview(data);
    })
    .catch(function(err) {
        // Something went wrong
        // Hide the spinner and show a simple error message to the user
        spHideLoadingOverlay();
        alert('Something went wrong while generating the plan. Please try again.');
        console.error('Smart Planner generate error:', err);
    });
}


// All preview overlay functions below. spProceedToGenerate calls these when it has the result.

// Show preview overlay with slides
function spShowPreview(data) {
    document.getElementById('smartPlannerModal').classList.add('hidden');

    // Build slides (weeks + summary)
    spSlides = [];

    (data.weeks || []).forEach(function(week) {
        spSlides.push({ type: 'week', data: week });
    });

    spSlides.push({
        type: 'summary',
        data: { summary: data.summary, unplaced: data.unplaced || [] }
    });

    spCurrentSlide = 0;
    spRenderSlide(spCurrentSlide);

    document.getElementById('sp-preview-overlay').classList.remove('hidden');
}


// Render current slide
function spRenderSlide(index) {
    const slide      = spSlides[index];
    const total      = spSlides.length;
    const contentDiv = document.getElementById('sp-slide-content');
    const slideLabel = document.getElementById('sp-slide-label');
    const prevArrow  = document.getElementById('sp-prev-slide');
    const nextArrow  = document.getElementById('sp-next-slide');

    // Update label
    if (slide.type === 'week') {
        slideLabel.innerHTML =
            `<span class="sp-slide-label-main">${slide.data.week_label}</span>` +
            `<span class="sp-slide-label-sub">Slide ${index + 1} of ${total}</span>`;
    } else {
        slideLabel.innerHTML =
            `<span class="sp-slide-label-main">Plan Summary</span>` +
            `<span class="sp-slide-label-sub">Slide ${index + 1} of ${total}</span>`;
    }

    // Enable/disable arrows
    prevArrow.disabled = (index === 0);
    nextArrow.disabled = (index === total - 1);

    // Render content
    contentDiv.innerHTML = (slide.type === 'week')
        ? spBuildWeekSlide(slide.data)
        : spBuildSummarySlide(slide.data);

    contentDiv.scrollTop = 0;
}


// Previous slide
function spPrevSlide() {
    if (spCurrentSlide > 0) {
        spCurrentSlide--;
        spRenderSlide(spCurrentSlide);
    }
}


// Next slide
function spNextSlide() {
    if (spCurrentSlide < spSlides.length - 1) {
        spCurrentSlide++;
        spRenderSlide(spCurrentSlide);
    }
}


// Build week slide HTML
function spBuildWeekSlide(week) {
    let html = '';

    if (!week.days || week.days.length === 0) {
        return '<div class="sp-no-events-msg">No events scheduled this week.</div>';
    }

    week.days.forEach(function(day) {
        html += `<div class="sp-week-day">`;
        html += `<div class="sp-week-day-label">${day.day}</div>`;

        day.events.forEach(function(item) {
            html += `<div class="sp-week-event">
                        <span class="sp-week-event-title">${item.title}</span>
                        <span class="sp-week-event-time">${item.start} → ${item.end}</span>
                     </div>`;
        });

        html += `</div>`;
    });

    return html;
}


// Build summary slide HTML
function spBuildSummarySlide(data) {
    const summary  = data.summary || {};
    const unplaced = data.unplaced || [];
    let html = '';

    const placedCount   = summary.total_placed || 0;
    const unplacedCount = summary.total_unplaced || 0;

    html += `<div class="sp-summary-totals">
                <span class="sp-summary-total-num">${placedCount}</span>
                <span class="sp-summary-total-label">instances placed</span>`;

    if (unplacedCount > 0) {
        html += `<span class="sp-summary-total-warn">${unplacedCount} couldn't be scheduled</span>`;
    } else {
        html += `<span class="sp-summary-all-placed">All instances scheduled!</span>`;
    }

    html += `</div>`;

    // Per-template progress
    (summary.by_template || []).forEach(function(t) {
        const pct = t.total > 0 ? Math.round((t.placed / t.total) * 100) : 0;

        let fillColor = '#276749';
        if (pct < 100) fillColor = '#b7791f';
        if (pct < 50)  fillColor = '#c53030';

        html += `<div class="sp-summary-row">
                    <span class="sp-summary-title">${t.title}</span>
                    <div class="sp-summary-bar-wrap">
                        <div class="sp-summary-bar" style="width:${pct}%;background:${fillColor};"></div>
                    </div>
                    <span class="sp-summary-count">${t.placed} / ${t.total}</span>
                 </div>`;
    });

    // Warnings
    if (unplaced.length > 0) {
        html += `<div class="sp-warnings-section">
                    <div class="sp-warnings-title">⚠ Couldn't be scheduled</div>`;

        unplaced.forEach(function(u) {
            html += `<div class="sp-warning-item">
                        <span class="sp-warning-name">${u.event_title} #${u.occurrence_index}</span>
                        <span class="sp-warning-reason">${u.reason}</span>
                     </div>`;
        });

        html += `</div>`;
    }

    return html;
}


// Go back to wizard
function spPreviewGoBack() {
    document.getElementById('sp-preview-overlay').classList.add('hidden');
    document.getElementById('smartPlannerModal').classList.remove('hidden');
    spGoToStep(2);
}


// Close completely
function spPreviewClose() {
    document.getElementById('sp-preview-overlay').classList.add('hidden');
    closeSmartPlanner();
}

// Approve Button- returns errors if something goes wrong, otherwise reloads the page to show the new schedule
function spPreviewApprove() {
    if (!spLastPlanResult || !spLastPlanResult.placed) {
        alert('Plan data missing. Please generate the plan again.');
        return;
    }

    const approveBtn = document.getElementById('sp-approve-btn');
    approveBtn.disabled = true;
    approveBtn.textContent = 'Saving...';

    const csrf = spGetCsrfToken();

    fetch('/smart-plan/confirm/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf,
        },
        body: JSON.stringify({
            placed: spLastPlanResult.placed,
            unplaced: spLastPlanResult.unplaced,
        }),
    })
    .then(function(resp) {
        if (!resp.ok) throw new Error('Server returned ' + resp.status);
        return resp.json();
    })
    .then(function(data) {
        document.getElementById('sp-preview-overlay').classList.add('hidden');
        closeSmartPlanner();
        alert('Plan approved! ' + data.placed_count + ' instances have been added to your schedule.');
        window.location.reload();
    })
    .catch(function(err) {
        approveBtn.disabled = false;
        approveBtn.textContent = 'Approve Plan';
        alert('Something went wrong saving the plan. Please try again.');
        console.error('Smart Planner confirm error:', err);
    });
}
window.spNextSlide = spNextSlide;
window.spPrevSlide = spPrevSlide;
window.spPreviewGoBack = spPreviewGoBack;
window.spPreviewClose = spPreviewClose;
window.spPreviewApprove = spPreviewApprove;


