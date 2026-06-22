/* 
   week-calendar.js — Created by Wazna and Bliss, redesigned */

const DAYS_SHORT  = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const DAYS_LONG   = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const MONTHS_LONG = ['January','February','March','April','May','June',
                     'July','August','September','October','November','December'];
const HOURS       = 24;
const PX_PER_HOUR = 60;

// Read view type and week start from Django config
const _cfg      = window.WEEK_CAL_CONFIG || {};
const VIEW_TYPE = (_cfg.viewType === 'day') ? 'day' : (_cfg.viewType === 'month') ? 'month' : 'week';
const NUM_DAYS  = VIEW_TYPE === 'day' ? 1 : 7;

let todaysDate = new Date();
todaysDate.setHours(0, 0, 0, 0);

let currentWeekDate = (function () {
  if (_cfg.weekStart) {
    const d = new Date(_cfg.weekStart + 'T00:00:00');
    if (!isNaN(d)) return d;
  }
  return new Date(todaysDate);
})();

/* ---- Helpers ---- */

function getMondayOf(date) {
  const d = new Date(date);
  const day = d.getDay();
  d.setDate(d.getDate() - (day === 0 ? 6 : day - 1));
  d.setHours(0, 0, 0, 0);
  return d;
}

function toISODate(d) {
  // Local ISO date (yyyy-mm-dd). Deliberately NOT toISOString() — that
  // returns UTC which, in BST, shifts every date back by a day.
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return y + '-' + m + '-' + dd;
}

function getStartDate(date) {
  return VIEW_TYPE === 'day' ? new Date(date) : getMondayOf(date);
}

/* ---- Build DOM ---- */

function buildGrid() {
  const timeCol = document.getElementById('gcal-time-col');
  const grid    = document.getElementById('gcal-grid');
  if (!timeCol || !grid) return;

  // Sticky blank cell at top of time column
  const timeHeader = document.createElement('div');
  timeHeader.className = 'gcal-time-header';
  timeCol.appendChild(timeHeader);

  // Time labels (h=0 is blank, avoids crowding)
  for (let h = 0; h < HOURS; h++) {
    const label = document.createElement('div');
    label.className = 'gcal-time-label';
    if (h !== 0) {
      label.textContent = h < 12 ? h + ' AM' : h === 12 ? '12 PM' : (h - 12) + ' PM';
    }
    timeCol.appendChild(label);
  }

  // Day columns — sticky header + 24 hour rows each
  for (let d = 0; d < NUM_DAYS; d++) {
    const col = document.createElement('div');
    col.className   = 'gcal-day-col';
    col.dataset.day = d;

    const hdr = document.createElement('div');
    hdr.className   = 'gcal-day-header';
    hdr.dataset.day = d;
    col.appendChild(hdr);

    for (let h = 0; h < HOURS; h++) {
      const row = document.createElement('div');
      row.className = 'gcal-hour-row';
      col.appendChild(row);
    }

    col.addEventListener('dragover',  function (e) { e.preventDefault(); showPreview(e, col); });
    col.addEventListener('dragleave', function (e) {
      // Only hide if leaving the column entirely (not just entering a child)
      if (!col.contains(e.relatedTarget)) hidePreview();
    });
    col.addEventListener('drop',      function (e) { hidePreview(); handleDrop(e, col); });
    grid.appendChild(col);
  }

  // Current-time line 
  const nowLine = document.createElement('div');
  nowLine.id = 'gcal-now-line';
  nowLine.style.display = 'none';
  grid.appendChild(nowLine);

  updateNowLine();
  setInterval(updateNowLine, 60000);
}

/* ---- Current time line ---- */

function updateNowLine() {
  const nowLine = document.getElementById('gcal-now-line');
  if (!nowLine) return;

  const now      = new Date();
  const todayMid = new Date(now);
  todayMid.setHours(0, 0, 0, 0);

  const startDate = getStartDate(currentWeekDate);
  const endDate   = new Date(startDate);
  endDate.setDate(endDate.getDate() + NUM_DAYS - 1);
  endDate.setHours(23, 59, 59);

  if (todayMid < startDate || todayMid > endDate) {
    nowLine.style.display = 'none';
    return;
  }

  // Which column index is today?
  const diffDays  = Math.round((todayMid - startDate) / 86400000);
  const dayCols   = document.querySelectorAll('.gcal-day-col');
  const targetCol = dayCols[diffDays];
  if (!targetCol) return;

  const mins = now.getHours() * 60 + now.getMinutes();
  nowLine.style.top    = (HEADER_HEIGHT + mins / 60 * PX_PER_HOUR) + 'px';
  nowLine.style.display = 'block';
  if (nowLine.parentElement !== targetCol) targetCol.appendChild(nowLine);
}

/* ---- Display ---- */

function display(date) {
  const startDate = getStartDate(date);

  // Toolbar date text
  const dateTextEl = document.getElementById('dateText');
  if (dateTextEl) {
    if (VIEW_TYPE === 'day') {
      const dow = startDate.getDay() === 0 ? 6 : startDate.getDay() - 1;
      dateTextEl.innerText =
        DAYS_LONG[dow] + ', ' + startDate.getDate() + ' ' +
        MONTHS_LONG[startDate.getMonth()] + ' ' + startDate.getFullYear();
    } else {
      dateTextEl.innerText = MONTHS_LONG[startDate.getMonth()] + ' ' + startDate.getFullYear();
    }
  }

  // Day header cells
  document.querySelectorAll('.gcal-day-col .gcal-day-header').forEach(function (el, i) {
    const d = new Date(startDate);
    d.setDate(startDate.getDate() + i);
    const isToday = d.getTime() === todaysDate.getTime();
    const dow = d.getDay() === 0 ? 6 : d.getDay() - 1;
    el.innerHTML =
      '<span class="gcal-day-name">' + DAYS_SHORT[dow] + '</span>' +
      '<span class="gcal-day-num' + (isToday ? ' today' : '') + '">' + d.getDate() + '</span>';
    el.dataset.date = toISODate(d);
  });

  // Update day column dates (used by drag-drop)
  document.querySelectorAll('.gcal-day-col').forEach(function (col, i) {
    const d = new Date(startDate);
    d.setDate(startDate.getDate() + i);
    col.dataset.date = toISODate(d);
  });

  updateNowLine();
  positionAllEvents();
}

/* ---- Navigation ---- */

function changeWeek(diff) {
  if (VIEW_TYPE === 'month') {
    if (typeof window.changeMonth === 'function') window.changeMonth(diff);
    return;
  }

  // Determine how many days to move (1 day for 'day' view, 7 days for 'week' view)
  var step = VIEW_TYPE === 'day' ? diff : 7 * diff;
  currentWeekDate.setDate(currentWeekDate.getDate() + step);

  // Update the day headers without a full page reload
  display(currentWeekDate);

  // Fetch events for the new week via AJAX
  var weekStr = toISODate(getStartDate(currentWeekDate));
  fetch('/api/schedule-events/?week=' + weekStr, {
    credentials: 'same-origin',
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    renderEventsFromData(data);
  })
  .catch(function(e) {
    console.error('Could not fetch events for week', weekStr, e);
  });
}

// Ashrith- Reads the events JSON embedded by Django and creates positioned card elements
function renderEventsFromData(eventsOverride) {
  // Accept pre-fetched data from changeWeek AJAX, or fall back to the embedded JSON
  var events;

  if (eventsOverride !== undefined) {
    events = eventsOverride;
  } else {
    var jsonBlock = document.getElementById('calendar-events-data');
    if (!jsonBlock) return;

    try {
      events = JSON.parse(jsonBlock.textContent);
    } catch (e) {
      console.error('renderEventsFromData: could not parse events JSON', e);
      return;
    }
  }

  if (!events || events.length === 0) return;

  // Remove previously rendered backend event cards to avoid duplicates
  document.querySelectorAll('.gcal-day-col .card[data-backend="true"]').forEach(function(el) {
    el.parentElement.removeChild(el);
  });

  // Build a mapping from date strings to calendar column elements
  var dateToCol = {};
  document.querySelectorAll('.gcal-day-col').forEach(function(col) {
    if (col.dataset.date) {
      dateToCol[col.dataset.date] = col;
    }
  });

  // Border color by importance level
  var importanceColors = {
    1: '#c53030',
    2: '#c05621',
    3: '#b7791f',
    4: '#276749',
    5: '#2b6cb0',
  };

  // Iterate over each event and render it
  events.forEach(function(ev) {
    if (!ev.placed_start || !ev.placed_end) return;

    // Parse as JS Date so the browser converts from the stored UTC offset
    // back into local time. Avoids the off-by-one-hour bug in BST that
    // happened when we string-split the ISO datetime.
    var startDate = new Date(ev.placed_start);
    var endDate   = new Date(ev.placed_end);

    var eventDate = toISODate(startDate);
    var dayCol = dateToCol[eventDate];
    if (!dayCol) return;

    var startH = startDate.getHours();
    var startM = startDate.getMinutes();
    var endH   = endDate.getHours();
    var endM   = endDate.getMinutes();

    var startMins = startH * 60 + startM;
    var endMins = endH * 60 + endM;
    var durationMin = endMins - startMins;

    var top = HEADER_HEIGHT + (startMins / 60) * PX_PER_HOUR;
    var height = Math.max((durationMin / 60) * PX_PER_HOUR, 22);

    var startLabel = (startH < 10 ? '0' : '') + startH + ':' + (startM < 10 ? '0' : '') + startM;
    var endLabel = (endH < 10 ? '0' : '') + endH + ':' + (endM < 10 ? '0' : '') + endM;

    // Create a new card element for the event
    var card = document.createElement('div');
    card.className = 'card';
    // Greyed-out + strikethrough styling for done instances. Matches the
    // month-view chip classes so both views render completed/missed the
    // same way.
    if (ev.status === 3) card.classList.add('completed');
    if (ev.status === 4) card.classList.add('missed');
    card.draggable = true;

    // Store backend data for later reference / modal
    card.dataset.backend = 'true';
    // ScheduleEvent id + parent Event template id — used by the detail modal
    // so Edit/Remove can know which rows to act on
    card.dataset.id = ev.id != null ? String(ev.id) : '';
    card.dataset.eventId = ev.event_id != null ? String(ev.event_id) : '';
    card.dataset.title = ev.title || '';
    card.dataset.category = ev.category || '';
    card.dataset.importance = ev.importance || '';
    card.dataset.location = ev.location || '';
    card.dataset.description = ev.description || '';
    card.dataset.placedStart = ev.placed_start || '';
    card.dataset.placedEnd = ev.placed_end || '';
    card.dataset.duration = ev.duration != null ? String(ev.duration) : '';
    // hour/minute used by hasCollision + drag-to-move so already-placed cards
    // can block new drops that overlap them
    card.dataset.hour = String(startH);
    card.dataset.minute = String(startM);
    // Copy constraint fields from the matching template (global `events` array
    // from add-event.js) onto placed cards so moving them runs the same checks.
    // Without this, already-placed fixed/repeat-day cards can be dragged anywhere.
    if (typeof events !== 'undefined' && events) {
        const tmpl = events.find(t => t.id === ev.event_id);
        if (tmpl) {
            card.dataset.repeatDays = tmpl.repeat_days != null ? String(tmpl.repeat_days) : '0';
            const isFixed = !!(tmpl.start && tmpl.end);
            card.dataset.isFixed = isFixed ? 'true' : 'false';
            card.dataset.fixedStart = isFixed ? tmpl.start : '';
            card.dataset.fixedEnd = isFixed ? tmpl.end : '';
            card.dataset.constrainedHour = tmpl.constrained_hour != null ? tmpl.constrained_hour : '';
            card.dataset.constrainedMinute = tmpl.constrained_minute != null ? tmpl.constrained_minute : '';
        }
    }
    // Instance status — dragging back to sidebar is only allowed when the
    // instance is still SCHEDULED (not completed or missed)
    card.dataset.status = ev.status != null ? String(ev.status) : '';

    var bgColor = (ev.colour || '#888888') + '20'; // Transparent background
    var borderColor = importanceColors[ev.importance_num] || '#2b6cb0';

    card.style.cssText = [
      'position:absolute',
      'top:' + top + 'px',
      'height:' + height + 'px',
      'left:3px',
      'right:3px',
      'background:' + bgColor,
      'border-left:3px solid ' + borderColor,
      'border-radius:6px',
      'padding:3px 6px',
      'overflow:hidden',
      'box-sizing:border-box',
      'cursor:pointer',
      'z-index:10',
    ].join(';');

    // Show time only if the card is tall enough. Use a muted colour instead
    // of opacity so completed/missed cards (which also mute the text) don't
    // compound opacities and render the time invisible.
    var timeBlock = height >= 40
      ? `<div style="font-size:10px;color:#475467;white-space:nowrap;">${startLabel} – ${endLabel}</div>`
      : '';

    card.innerHTML =
      `<div style="font-size:12px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${ev.title}</div>` +
      timeBlock;

    // Drag handlers so the user can move the card to a different slot
    // or drop it back onto the sidebar to unplace it.
    card.addEventListener('dragstart', function(e) {
      window._draggedCalCard = card;
      if (typeof beingDragged !== 'undefined') beingDragged = card;
      if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move';
    });
    card.addEventListener('dragend', function() {
      window._draggedCalCard = null;
    });

    // Add click handler to open modal with event details
    card.addEventListener('click', function(e) {
      e.stopPropagation();
      if (typeof openDetailModal === 'function') {
        openDetailModal(card.dataset);
      }
    });

    // Append the card to the correct day column
    dayCol.appendChild(card);
  });
  // main branch alternative: if (typeof renderEvents === 'function') renderEvents();
}

/* ---- Event positioning ---- */

const HEADER_HEIGHT   = 72;
const EVENT_HEIGHT_PX = PX_PER_HOUR; // fixed 1-hour block for now

/* ---- Drop preview ---- */

let _preview = null;

const MAX_START_MINS = HOURS * 60 - (EVENT_HEIGHT_PX / PX_PER_HOUR * 60);

function snapMins(e, col) {
  const card = window._draggedCalCard;
  // If the card has a locked time of day, always snap to that regardless of mouse position
  if (card && card.dataset.constrainedHour !== undefined && card.dataset.constrainedHour !== '') {
    return parseInt(card.dataset.constrainedHour) * 60 + (parseInt(card.dataset.constrainedMinute) || 0);
  }
  const rect     = col.getBoundingClientRect();
  const gridY    = Math.max(e.clientY - rect.top - HEADER_HEIGHT, 0);
  const raw      = Math.round((gridY / PX_PER_HOUR * 60) / 15) * 15;
  const duration = card ? (parseInt(card.dataset.duration) || 60) : 60;
  const maxMins  = HOURS * 60 - duration;
  return Math.min(raw, maxMins);
}

function getSnapTop(e, col) {
  return HEADER_HEIGHT + snapMins(e, col) / 60 * PX_PER_HOUR;
}

function showPreview(e, col) {
  if (!window._draggedCalCard) return;

  if (!_preview) {
    _preview = document.createElement('div');
    _preview.id = 'gcal-drop-preview';
  }

  const duration = parseInt(window._draggedCalCard.dataset.duration) || 60;
  const top = getSnapTop(e, col);
  _preview.style.top    = top + 'px';
  _preview.style.height = (duration / 60 * PX_PER_HOUR) + 'px';

  if (_preview.parentElement !== col) {
    hidePreview();
    col.appendChild(_preview);
  }
}

function hidePreview() {
  if (_preview && _preview.parentElement) {
    _preview.parentElement.removeChild(_preview);
  }
}

/* ---- Collision detection ---- */

function hasCollision(col, startMins, durationMins, excludeCard) {
  const endMins = startMins + durationMins;
  for (const card of col.querySelectorAll('.card')) {
    if (card === excludeCard || card === _preview) continue;
    const cardStart    = (parseInt(card.dataset.hour) || 0) * 60 + (parseInt(card.dataset.minute) || 0);
    const cardDuration = parseInt(card.dataset.duration) || 60;
    const cardEnd      = cardStart + cardDuration;
    if (startMins < cardEnd && endMins > cardStart) return true;
  }
  return false;
}

/* ---- Drag & drop ---- */

function handleDrop(e, col) {
  e.preventDefault();
  const card = window._draggedCalCard || (typeof beingDragged !== 'undefined' ? beingDragged : null);
  if (!card) return;

  const totalMins = snapMins(e, col);
  const duration  = parseInt(card.dataset.duration) || 60;

  if (hasCollision(col, totalMins, duration, card)) {
    hidePreview();
    alert('Another event already occupies that time slot.');
    window._draggedCalCard = null;
    return;
  }

  // Sidebar template card drop — persist via the backend place endpoint
  // instead of moving DOM nodes around, so the placement survives page
  // reloads + week navigation.
  if (card.dataset.templateCard === 'true') {
    if (typeof window.placeTemplateAt === 'function') {
      window.placeTemplateAt(card, col.dataset.date, totalMins);
    }
    window._draggedCalCard = null;
    return;
  }

  // Already-placed card dragged to a different slot — persist the new
  // placement so refreshing / switching weeks doesn't snap it back.
  if (card.dataset.backend === 'true' && card.dataset.id) {
    if (typeof window.movePlacedInstance === 'function') {
      window.movePlacedInstance(card, col.dataset.date, totalMins);
    }
    window._draggedCalCard = null;
    return;
  }

  const h = Math.floor(totalMins / 60);
  const m = totalMins % 60;

  // Preserve the card's fixed state — don't overwrite it
  card.dataset.day    = col.dataset.day;
  card.dataset.date   = col.dataset.date;
  card.dataset.hour   = h;
  card.dataset.minute = m;

  col.appendChild(card);
  positionEvent(card);
  window._draggedCalCard = null;

  // Notify add-event.js that the drop was successful
  if (typeof window.onCardDropped === 'function') window.onCardDropped(card);
}

/* ---- Event positioning ---- */

function positionEvent(card) {
  const h        = parseInt(card.dataset.hour)      || 0;
  const m        = parseInt(card.dataset.minute)    || 0;
  const duration = parseInt(card.dataset.duration)  || 60;

  card.style.top    = (HEADER_HEIGHT + (h * 60 + m) / 60 * PX_PER_HOUR) + 'px';
  card.style.height = (duration / 60 * PX_PER_HOUR) + 'px';
}

function positionAllEvents() {
  document.querySelectorAll('.gcal-day-col .card').forEach(positionEvent);
}

/* ---- Sidebar toggle ---- */

function toggleSidebar() {
  const sidebar = document.getElementById('gcal-sidebar');
  const toggle  = document.getElementById('gcal-sidebar-toggle');
  if (!sidebar || !toggle) return;
  sidebar.classList.toggle('collapsed');
  const collapsed = sidebar.classList.contains('collapsed');
  toggle.innerHTML  = collapsed ? '&#8250;' : '&#8249;';
  toggle.style.left = collapsed ? '0' : '220px';
}

/* ---- Init ---- */

if (VIEW_TYPE !== 'month') {
  buildGrid();
  display(currentWeekDate);
  renderEventsFromData(); // initial render from embedded JSON

  (function scrollToMorning() {
    const body = document.getElementById('gcal-body');
    if (body) {
      body.scrollTop = 7 * PX_PER_HOUR;
    } else {
      window.addEventListener('DOMContentLoaded', function () {
        const b = document.getElementById('gcal-body');
        if (b) b.scrollTop = 7 * PX_PER_HOUR;
      });
    }
  })();
}
