/* month-calendar.js — Created by Wazna and Bliss, redesigned */

const MONTH_DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const MONTH_NAMES     = ['January','February','March','April','May','June',
                         'July','August','September','October','November','December'];

const _mcfg = window.WEEK_CAL_CONFIG || {};

let today = new Date();
today.setHours(0, 0, 0, 0);

let displayDate = (function () {
  if (_mcfg.weekStart) {
    const d = new Date(_mcfg.weekStart + 'T00:00:00');
    if (!isNaN(d)) return d;
  }
  return new Date();
})();

let _monthScheduleEvents = null;
let _monthEventTemplates = null;

// yyyy-mm-dd in the user's local timezone. Using toISOString() instead
// gives UTC, which drops a day in BST and breaks the grouping below.
function _localISODate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return y + '-' + m + '-' + dd;
}

function buildMonthView(date) {
  const header = document.getElementById('gcal-month-header');
  const grid   = document.getElementById('gcal-month-grid');
  if (!header || !grid) return;

  header.innerHTML = '';
  grid.innerHTML   = '';

  MONTH_DAY_NAMES.forEach(function (name) {
    const cell = document.createElement('div');
    cell.className   = 'gcal-month-day-name';
    cell.textContent = name;
    header.appendChild(cell);
  });

  const dateTextEl = document.getElementById('dateText');
  if (dateTextEl) {
    dateTextEl.innerText = MONTH_NAMES[date.getMonth()] + ' ' + date.getFullYear();
  }

  const year  = date.getFullYear();
  const month = date.getMonth();
  const todayMid = new Date(today);

  const firstDay      = new Date(year, month, 1);
  const firstDayIndex = firstDay.getDay() === 0 ? 6 : firstDay.getDay() - 1;
  const lastDay       = new Date(year, month + 1, 0).getDate();

  for (let i = 0; i < firstDayIndex; i++) {
    const d = new Date(year, month, 1 - (firstDayIndex - i));
    grid.appendChild(createCell(d, todayMid, true));
  }

  for (let d = 1; d <= lastDay; d++) {
    grid.appendChild(createCell(new Date(year, month, d), todayMid, false));
  }

  const totalCells = Math.ceil((firstDayIndex + lastDay) / 7) * 7;
  for (let i = 1; i <= totalCells - firstDayIndex - lastDay; i++) {
    grid.appendChild(createCell(new Date(year, month + 1, i), todayMid, true));
  }

  _loadMonthEvents();
}

function createCell(date, todayMid, otherMonth) {
  const cell = document.createElement('div');
  cell.className    = 'gcal-month-cell' + (otherMonth ? ' other-month' : '');
  // Local ISO date — toISOString() returns UTC which shifts by a day in BST
  cell.dataset.date = _localISODate(date);

  const numEl = document.createElement('div');
  const isToday = date.getTime() === todayMid.getTime();
  numEl.className   = 'gcal-month-cell-num' + (isToday ? ' today' : '');
  numEl.textContent = date.getDate();
  cell.appendChild(numEl);

  return cell;
}

/* ---- Event rendering ---- */

function _getTemplateById(id) {
  if (!_monthEventTemplates) return null;
  return _monthEventTemplates.find(function (e) { return e.id === id; }) || null;
}

async function _loadMonthEvents() {
  try {
    const [seData, tmplData] = await Promise.all([
      fetch('/api/schedule-events/').then(function (r) { return r.json(); }),
      fetch('/api/events/').then(function (r) { return r.json(); }),
    ]);
    _monthScheduleEvents = seData;
    _monthEventTemplates = tmplData;
    _renderMonthEvents();
  } catch (err) {
    console.error('Month view: could not load events', err);
  }
}

function _renderMonthEvents() {
  if (!_monthScheduleEvents) return;

  // Group placed events by date. CREATED instances are skipped (no
  // placement); SCHEDULED, COMPLETED and MISSED all show here — the
  // chip's CSS class (set in _createEventChip) greys out the done ones.
  const byDate = {};
  _monthScheduleEvents.forEach(function (se) {
    if (!se.placed_start) return;
    // Parse as JS Date then format as local ISO — the raw ISO string is in
    // UTC, which would map events to the wrong day in BST.
    const dateStr = _localISODate(new Date(se.placed_start));
    if (!byDate[dateStr]) byDate[dateStr] = [];
    byDate[dateStr].push(se);
  });

  const cells = document.querySelectorAll('.gcal-month-cell');
  cells.forEach(function (cell) {
    const dateStr = cell.dataset.date;
    const events  = byDate[dateStr];
    if (!events || events.length === 0) return;

    events.sort(function (a, b) { return a.placed_start.localeCompare(b.placed_start); });

    const MAX_VISIBLE = 3;
    const shown = events.slice(0, MAX_VISIBLE);
    const extra = events.length - MAX_VISIBLE;

    shown.forEach(function (se) {
      cell.appendChild(_createEventChip(se));
    });

    if (extra > 0) {
      const more = document.createElement('div');
      more.className   = 'gcal-month-event-more';
      more.textContent = '+' + extra + ' more';
      cell.appendChild(more);
    }
  });
}

function _createEventChip(se) {
  const tmpl = _getTemplateById(se.event_id);
  const title    = tmpl ? tmpl.title : 'Event';
  const catColor = (tmpl && tmpl.category_colour) ? tmpl.category_colour : '#888888';

  const d   = new Date(se.placed_start);
  const hh  = String(d.getHours()).padStart(2, '0');
  const mm  = String(d.getMinutes()).padStart(2, '0');

  const chip = document.createElement('div');
  chip.className = 'gcal-month-event-chip';
  if (se.status === 3) chip.classList.add('completed');
  if (se.status === 4) chip.classList.add('missed');
  chip.style.borderLeftColor = catColor;

  chip.innerHTML =
    '<span class="chip-time">' + hh + ':' + mm + '</span>' +
    '<span class="chip-title">' + _escapeHtml(title) + '</span>';

  chip.addEventListener('click', function (e) {
    e.stopPropagation();
    _openMonthDetail(se, tmpl);
  });

  return chip;
}

function _escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function _openMonthDetail(se, tmpl) {
  if (typeof openDetailModal !== 'function') return;
  openDetailModal({
    id:          String(se.id),
    title:       tmpl ? tmpl.title       : 'Event',
    category:    tmpl ? tmpl.category    : '',
    location:    tmpl ? tmpl.location    : '',
    description: tmpl ? tmpl.description : '',
    importance:  tmpl ? tmpl.importance  : '',
    duration:    String(tmpl ? tmpl.duration : 60),
    placedStart: se.placed_start || '',
    placedEnd:   se.placed_end   || '',
    status:      String(se.status),
  });
}

buildMonthView(displayDate);

window.changeMonth = function (diff) {
  displayDate.setMonth(displayDate.getMonth() + diff);
  buildMonthView(displayDate);
};
