// Sidebar + drag-drop logic for the main page calendar.
//
// The sidebar shows ONE card per Event template that still has unplaced
// instances, with a counter of how many are left. Dragging a sidebar card
// onto a day column picks the first unplaced instance for that template
// and POSTs to /schedule-event/<pk>/place/ so the placement persists to
// the DB. We then reload so the calendar rerenders cleanly from the server.

let schedule_events
let events
let beingDragged

// Weekday bitmask helpers — mirrors the bitmask the backend stores on Event.repeat_days.
// Mon=1, Tue=2, Wed=4, Thu=8, Fri=16, Sat=32, Sun=64.
// JS getDay() gives 0=Sun..6=Sat, so we need a conversion array.
const JS_DAY_TO_BITMASK = [64, 1, 2, 4, 8, 16, 32];
const DAY_NAMES_SHORT = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function dateStrToDayBit(dateStr) {
    // dateStr is "YYYY-MM-DD" — parse it as a local date and get the bitmask bit
    const d = new Date(dateStr + 'T12:00:00');
    return JS_DAY_TO_BITMASK[d.getDay()];
}

function bitmaskToDayNames(mask) {
    // Turn a repeat_days bitmask into a readable list like "Mon, Wed, Fri"
    const bits = [1, 2, 4, 8, 16, 32, 64];
    const names = [];
    bits.forEach((bit, i) => {
        if (mask & bit) names.push(DAY_NAMES_SHORT[i]);
    });
    return names.join(', ');
}

/** Fetch the current schedule events + event templates, render the sidebar,
 *  and wire up drag listeners on the day columns. */
async function renderEvents() {
    try {
        const params = new URLSearchParams(document.location.search);
        const filters = params.getAll('filter');
        const filterString = formatParameterList('filter', filters);
        schedule_events = await fetch('/api/schedule-events/' + filterString).then(r => r.json());
        events = await fetch('/api/events').then(r => r.json());

        renderSidebarTemplates();
        attachSidebarDropListener();
    } catch (err) {
        console.error("Could not load events: ", err);
    }
}

/** Render one card per Event template that has at least one CREATED
 *  (unplaced) instance. Styled to match the dashboard template cards. */
function renderSidebarTemplates() {
    const container = document.getElementById('event-container');
    if (!container) return;
    container.innerHTML = '';

    const unplacedByEvent = {};
    schedule_events.forEach(se => {
        if (se.status === 1) {
            unplacedByEvent[se.event_id] = (unplacedByEvent[se.event_id] || 0) + 1;
        }
    });

    events.forEach(ev => {
        const count = unplacedByEvent[ev.id] || 0;
        if (count === 0) return;
        container.appendChild(buildSidebarCard(ev, count));
    });

    if (container.children.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'sidebar-empty-msg';
        empty.textContent = 'Nothing to place — all caught up!';
        container.appendChild(empty);
    }
}

/** Build a single sidebar template card. Drag handlers attached here. */
function buildSidebarCard(ev, count) {
    const importanceColours = {
        1: '#c53030', 2: '#c05621', 3: '#b7791f', 4: '#276749', 5: '#2b6cb0',
    };

    const card = document.createElement('div');
    card.className = 'sidebar-template-card';
    card.draggable = true;
    card.dataset.templateCard = 'true';
    card.dataset.eventId = ev.id;
    card.dataset.title = ev.title;
    card.dataset.duration = ev.duration || 60;
    card.dataset.hasStartTime = ev.has_start_time ? 'true' : 'false';
    card.dataset.constrainedHour = ev.constrained_hour != null ? ev.constrained_hour : '';
    card.dataset.constrainedMinute = ev.constrained_minute != null ? ev.constrained_minute : '';
    // Constraint fields — used by placeTemplateAt/movePlacedInstance to reject invalid drops.
    // repeat_days bitmask: 0 means any day, otherwise only listed days allowed.
    card.dataset.repeatDays = ev.repeat_days != null ? ev.repeat_days : '0';
    // Case C (fully fixed): both start + end are real ISO datetimes (real year).
    // When present, drops snap to these values regardless of where the user dropped.
    const isFixed = !!(ev.start && ev.end);
    card.dataset.isFixed = isFixed ? 'true' : 'false';
    card.dataset.fixedStart = isFixed ? ev.start : '';
    card.dataset.fixedEnd = isFixed ? ev.end : '';




    const bg = (ev.category_colour || '#888888') + '20';
    const border = importanceColours[ev.importance_num] || '#888';
    card.style.background = bg;
    card.style.borderLeft = '4px solid ' + border;

    card.innerHTML =
        '<div class="sidebar-card-title">' + escapeText(ev.title) + '</div>' +
        '<div class="sidebar-card-meta">' + count + ' to place</div>';

    card.addEventListener('dragstart', function (e) {
        beingDragged = card;
        window._draggedCalCard = card;
        if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move';
    });
    card.addEventListener('dragend', function () {
        window._draggedCalCard = null;
    });
    return card;
}

/** Simple text escape so event titles can't inject HTML into the sidebar. */
function escapeText(str) {
    const div = document.createElement('div');
    div.textContent = str || '';
    return div.innerHTML;
}

/** Wire a drop listener onto the sidebar so users can drag a placed card
 *  back into the sidebar to unplace it. */
function attachSidebarDropListener() {
    const sidebar = document.getElementById('gcal-sidebar');
    if (!sidebar) return;
    sidebar.addEventListener('dragover', function (e) { e.preventDefault(); });
    sidebar.addEventListener('drop', async function () {
        const card = window._draggedCalCard || beingDragged;
        if (!card) return;
        // Only handle backend-rendered placed cards — not sidebar cards dropped
        // back on the sidebar (that would be a no-op).
        if (card.dataset.backend !== 'true') return;
        const id = card.dataset.id;
        if (!id) return;
        try {
            const res = await fetch('/schedule-event/' + id + '/unplace/', {
                method: 'POST',
                headers: { 'X-CSRFToken': CSRF_TOKEN },
            });
            if (res.ok) {
                window.location.reload();
                return;
            }
            // Backend refused (e.g. instance is completed) — show its reason.
            const body = await res.json().catch(() => ({}));
            alert(body.error || 'Could not remove this event from the calendar.');
        } catch (err) {
            console.error('Unplace failed:', err);
        }
    });
}

/** Apply the 3 drag-drop constraint cases before placing/moving:
 *  - Case C (fully fixed): overrides dateStr + startMinutes with the event's locked values
 *  - Case B (time-locked): overrides startMinutes with constrainedHour/Minute
 *  - repeat_days check: rejects drops on days not in the mask
 *  Returns { dateStr, startMinutes } on success, or null if rejected.
 */
function enforceConstraints(card, dateStr, startMinutes) {
    // Case C — fully fixed event, snap everything to its locked slot
    if (card.dataset.isFixed === 'true' && card.dataset.fixedStart) {
        const fs = new Date(card.dataset.fixedStart);
        const fe = card.dataset.fixedEnd ? new Date(card.dataset.fixedEnd) : null;
        const y = fs.getFullYear();
        const m = String(fs.getMonth() + 1).padStart(2, '0');
        const d = String(fs.getDate()).padStart(2, '0');
        dateStr = y + '-' + m + '-' + d;
        startMinutes = fs.getHours() * 60 + fs.getMinutes();
        // Also override duration so the card height matches the locked window
        if (fe) {
            const dur = Math.max(1, Math.round((fe - fs) / 60000));
            card.dataset.duration = String(dur);
        }
        return { dateStr, startMinutes };
    }

    // Case B — time-only locked (Case 5 in backend). Force the time, keep the date.
    const ch = card.dataset.constrainedHour;
    const cm = card.dataset.constrainedMinute;
    if (ch !== '' && ch != null) {
        startMinutes = parseInt(ch) * 60 + (parseInt(cm) || 0);
    }

    // Repeat-day check — rejects the drop if the target weekday isn't in the mask
    const mask = parseInt(card.dataset.repeatDays) || 0;
    if (mask !== 0) {
        const dayBit = dateStrToDayBit(dateStr);
        if (!(mask & dayBit)) {
            alert('This event can only be placed on ' + bitmaskToDayNames(mask) + '.');
            return null;
        }
    }

    return { dateStr, startMinutes };
}

/** Called by week-calendar.js when a sidebar template card is dropped onto
 *  a day column. Places the first unplaced instance of that template at the
 *  drop location via the backend, then reloads so the calendar rerenders. */
async function placeTemplateAt(card, dateStr, startMinutes) {
    const eventId = parseInt(card.dataset.eventId);
    if (!eventId) return;
    const unplaced = schedule_events.find(se => se.event_id === eventId && se.status === 1);
    if (!unplaced) {
        alert('No more instances of this event left to place.');
        return;
    }

    // Apply the 3 constraint cases — rejects invalid drops or snaps to locked slots
    const ok = enforceConstraints(card, dateStr, startMinutes);
    if (!ok) return;
    dateStr = ok.dateStr;
    startMinutes = ok.startMinutes;

    const duration = parseInt(card.dataset.duration) || 60;
    const placedStart = dateStr + 'T' + minutesToHHMM(startMinutes) + ':00';
    const placedEnd = dateStr + 'T' + minutesToHHMM(startMinutes + duration) + ':00';

    try {
        const res = await fetch('/schedule-event/' + unplaced.id + '/place/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF_TOKEN,
            },
            body: JSON.stringify({ placed_start: placedStart, placed_end: placedEnd }),
        });
        if (res.ok) {
            window.location.reload();
        } else {
            alert('Could not save placement. Please try again.');
        }
    } catch (err) {
        console.error('Place failed:', err);
        alert('Something went wrong placing this event.');
    }
}

function minutesToHHMM(total) {
    const h = Math.floor(total / 60);
    const m = total % 60;
    return (h < 10 ? '0' : '') + h + ':' + (m < 10 ? '0' : '') + m;
}

/** Called by week-calendar.js when an already-placed backend card is
 *  dragged to a new slot. Updates its placed_start / placed_end via the
 *  same /place/ endpoint used for initial placements, then reloads. */
async function movePlacedInstance(card, dateStr, startMinutes) {
    const id = card.dataset.id;
    if (!id) return;

    // Same constraint checks as placeTemplateAt — snap fixed events back, reject bad days
    const ok = enforceConstraints(card, dateStr, startMinutes);
    if (!ok) return;
    dateStr = ok.dateStr;
    startMinutes = ok.startMinutes;

    const duration = parseInt(card.dataset.duration) || 60;
    const placedStart = dateStr + 'T' + minutesToHHMM(startMinutes) + ':00';
    const placedEnd = dateStr + 'T' + minutesToHHMM(startMinutes + duration) + ':00';

    try {
        const res = await fetch('/schedule-event/' + id + '/place/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF_TOKEN,
            },
            body: JSON.stringify({ placed_start: placedStart, placed_end: placedEnd }),
        });
        if (res.ok) {
            window.location.reload();
            return;
        }
        const body = await res.json().catch(() => ({}));
        alert(body.error || 'Could not move this event.');
    } catch (err) {
        console.error('Move failed:', err);
        alert('Something went wrong moving this event.');
    }
}

/** Utility to format ?filter=a&filter=b query strings. */
function formatParameterList(parameterName, values) {
    if (values.length === 0) return '';
    let out = '?' + parameterName + '=' + values[0];
    for (let i = 1; i < values.length; i++) out += '&' + parameterName + '=' + values[i];
    return out;
}

// Expose the drop helpers so week-calendar.js can call them from handleDrop
window.placeTemplateAt = placeTemplateAt;
window.movePlacedInstance = movePlacedInstance;

renderEvents();

if (typeof module !== 'undefined') {
    module.exports = { formatParameterList, minutesToHHMM };
}
