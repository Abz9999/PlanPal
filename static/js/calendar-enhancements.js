
var ENH_PX_PER_HOUR = 60;  // matches .hour-slot height in CSS
var ENH_PX_PER_SLOT = 15;  // each .item is 15px (60/4)
var ENH_VIEW_TYPE = (window.WEEK_CAL_CONFIG || {}).viewType || 'week';
var ENH_IS_DAY_VIEW = (ENH_VIEW_TYPE === 'day');


(function setupDayView() {
    if (!ENH_IS_DAY_VIEW) return;

    var weekJs = document.getElementById('week-js');
    if (!weekJs) return;
    var chosenDay = new Date(weekJs.dataset.week + 'T00:00:00');
    var jsDay = chosenDay.getDay();
    var monStartIdx = (jsDay === 0) ? 6 : jsDay - 1;

    var gridEl = document.getElementById('grid-container');
    if (gridEl) {
        gridEl.style.gridTemplateColumns = '60px 1fr';
    }

    document.querySelectorAll('.dayOfTheWeek').forEach(function(el) {
        if (parseInt(el.dataset.day) !== 0) {
            el.style.display = 'none';
        }
    });

    document.querySelectorAll('.hour-slot').forEach(function(slot) {
        var firstItem = slot.querySelector('.item');
        if (firstItem && parseInt(firstItem.dataset.day) !== 0) {
            slot.style.display = 'none';
        }
    });

    document.querySelectorAll('.item[data-day="0"]').forEach(function(item) {
        item.dataset.day = String(monStartIdx);
    });

    var visibleHeader = document.querySelector('.dayOfTheWeek[data-day="0"]');
    if (visibleHeader) {
        visibleHeader.dataset.day = String(monStartIdx);
    }

    var dateTextEl = document.getElementById('dateText');
    if (dateTextEl) {
        var DAYS_LONG = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        var MONTHS_LONG = ['January', 'February', 'March', 'April', 'May', 'June',
                           'July', 'August', 'September', 'October', 'November', 'December'];
        dateTextEl.innerText =
            DAYS_LONG[chosenDay.getDay()] + ', ' +
            chosenDay.getDate() + ' ' +
            MONTHS_LONG[chosenDay.getMonth()] + ' ' +
            chosenDay.getFullYear();
    }
})();


(function reformatTimeLabels() {
    document.querySelectorAll('.time-label').forEach(function(el) {
        var text = el.textContent.trim();
        var hour = parseInt(text);
        if (isNaN(hour)) return;
        if (hour === 0) {
            el.textContent = '12 AM';
        } else if (hour < 12) {
            el.textContent = hour + ' AM';
        } else if (hour === 12) {
            el.textContent = '12 PM';
        } else {
            el.textContent = (hour - 12) + ' PM';
        }
    });
})();


function getCsrfToken() {
    if (typeof CSRF_TOKEN !== 'undefined' && CSRF_TOKEN) return CSRF_TOKEN;
    var cookie = document.cookie.split(';').find(function(c) {
        return c.trim().startsWith('csrftoken=');
    });
    return cookie ? cookie.trim().split('=')[1] : '';
}


function toggleSidebar() {
    var sidebar = document.getElementById('gcal-sidebar');
    var toggle  = document.getElementById('gcal-sidebar-toggle');
    if (!sidebar || !toggle) return;
    sidebar.classList.toggle('collapsed');
    var collapsed = sidebar.classList.contains('collapsed');
    toggle.innerHTML  = collapsed ? '&#8250;' : '&#8249;';
    toggle.style.left = collapsed ? '0' : '220px';
}


var ENH_DAY_ABBR = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];

function reformatDayHeaders() {
    var today = new Date();
    today.setHours(0, 0, 0, 0);

    document.querySelectorAll('.dayOfTheWeek').forEach(function(el) {
        if (el.style.display === 'none') return;

        var dayIdx = parseInt(el.dataset.day);
        var abbr = ENH_DAY_ABBR[dayIdx] || '';

        var parts = el.textContent.split('\n');
        var dateNum = parts.length > 1 ? parts[1].trim() : '';
        var isToday = false;
        if (el.dataset.date) {
            var cellDate = new Date(el.dataset.date);
            cellDate.setHours(0, 0, 0, 0);
            isToday = (cellDate.getTime() === today.getTime());
        }

        el.innerHTML =
            '<span class="day-name">' + abbr + '</span>' +
            '<span class="day-num' + (isToday ? ' today' : '') + '">' + dateNum + '</span>';

        el.style.backgroundColor = '';

        if (isToday) {
            el.classList.add('is-today');
        } else {
            el.classList.remove('is-today');
        }
    });
}


function stretchCard(card) {
    if (!card.closest('.item')) return;

    var duration = 60;
    if (card.dataset.duration) {
        duration = parseInt(card.dataset.duration);
    } else if (typeof events !== 'undefined' && events && card.dataset.eventId) {
        var evt = events.find(function(e) { return e.id === parseInt(card.dataset.eventId); });
        if (evt && evt.duration) duration = evt.duration;
    }

    var heightPx = (duration / 60) * ENH_PX_PER_HOUR;
    card.style.height = heightPx + 'px';
    card.style.minHeight = heightPx + 'px';
    card.style.zIndex = '3';
    if (duration > 30) {
        card.style.whiteSpace = 'normal';
        card.style.alignItems = 'flex-start';
        card.style.paddingTop = '4px';
    }
}

function stretchAllCards() {
    document.querySelectorAll('.item .card').forEach(stretchCard);
}


var _dropPreview = null;

function getOrCreatePreview() {
    if (!_dropPreview) {
        _dropPreview = document.createElement('div');
        _dropPreview.id = 'enh-drop-preview';
    }
    return _dropPreview;
}

function showDropPreview(itemSlot) {
    var card = (typeof beingDragged !== 'undefined') ? beingDragged : null;
    if (!card) return;

    var duration = 60;
    if (card.dataset.duration) {
        duration = parseInt(card.dataset.duration);
    } else if (typeof events !== 'undefined' && events && card.dataset.eventId) {
        var evt = events.find(function(e) { return e.id === parseInt(card.dataset.eventId); });
        if (evt && evt.duration) duration = evt.duration;
    }

    var preview = getOrCreatePreview();
    var heightPx = (duration / 60) * ENH_PX_PER_HOUR;
    preview.style.height = heightPx + 'px';

    if (preview.parentElement !== itemSlot) {
        hideDropPreview();
        itemSlot.appendChild(preview);
    }
}

function hideDropPreview() {
    if (_dropPreview && _dropPreview.parentElement) {
        _dropPreview.parentElement.removeChild(_dropPreview);
    }
}

function attachDropPreviewListeners() {
    document.querySelectorAll('.item').forEach(function(slot) {
        if (slot.closest('.hour-slot') && slot.closest('.hour-slot').style.display === 'none') return;

        slot.addEventListener('dragover', function(e) {
            showDropPreview(slot);
        });
        slot.addEventListener('dragleave', function(e) {
            if (!slot.contains(e.relatedTarget)) {
                hideDropPreview();
            }
        });
        slot.addEventListener('drop', function() {
            hideDropPreview();
        });
    });
}


function updateNowLine() {
    var now = new Date();
    var today = new Date(now);
    today.setHours(0, 0, 0, 0);

    if (typeof currentWeek === 'undefined') return;
    var weekStart = new Date(currentWeek);
    weekStart.setHours(0, 0, 0, 0);
    var numDays = ENH_IS_DAY_VIEW ? 1 : 7;
    var weekEnd = new Date(weekStart);
    weekEnd.setDate(weekEnd.getDate() + numDays - 1);
    weekEnd.setHours(23, 59, 59);

    var nowLine = document.getElementById('gcal-now-line');

    if (today < weekStart || today > weekEnd) {
        if (nowLine) nowLine.style.display = 'none';
        return;
    }

    var dayIndex = (now.getDay() === 0) ? 6 : now.getDay() - 1;
    var hour = now.getHours();
    var minute = now.getMinutes();
    var quarterSlot = Math.floor(minute / 15);

    var selector = '.item[data-day="' + dayIndex + '"][data-hour="' + hour + '"][data-minute="' + (quarterSlot * 15) + '"]';
    var targetItem = document.querySelector(selector);
    if (!targetItem) return;

    var hourSlot = targetItem.closest('.hour-slot');
    if (!hourSlot) return;

    if (!nowLine) {
        nowLine = document.createElement('div');
        nowLine.id = 'gcal-now-line';
    }

    var minuteOffset = minute % 15;
    var topInSlot = (minuteOffset / 15) * ENH_PX_PER_SLOT;
    var topInHourSlot = (quarterSlot * ENH_PX_PER_SLOT) + topInSlot;

    nowLine.style.display = 'block';
    nowLine.style.top = topInHourSlot + 'px';

    if (nowLine.parentElement !== hourSlot) {
        hourSlot.appendChild(nowLine);
    }
}


var _currentDetailCardId = null;
var _currentDetailEventId = null;

function openDetailModal(data) {
    var modal = document.getElementById('detailModal');
    if (!modal) return;

    _currentDetailCardId = data.id || null;
    _currentDetailEventId = data.eventId || null;

    document.getElementById('detail-title').textContent = data.title || 'Event';

    var completedEl = document.getElementById('detail-completed');
    if (completedEl) completedEl.checked = (data.status === '3');

    _setDetailValue('detail-category',    'detail-category-row',    data.category    || '');
    _setDetailValue('detail-importance',  'detail-importance-row',  data.importance  || '');
    _setDetailValue('detail-location',    'detail-location-row',    data.location    || '');
    _setDetailValue('detail-description', 'detail-description-row', data.description || '');

    if (data.duration) {
        var dur  = parseInt(data.duration);
        var hrs  = Math.floor(dur / 60);
        var mins = dur % 60;
        var parts = [];
        if (hrs)  parts.push(hrs  + ' hr'  + (hrs  !== 1 ? 's' : ''));
        if (mins) parts.push(mins + ' min' + (mins !== 1 ? 's' : ''));
        _setDetailValue('detail-duration', 'detail-duration-row', parts.join(' ') || dur + ' min');
    } else {
        _setDetailValue('detail-duration', 'detail-duration-row', '1 hr');
    }

    if (data.placedStart) {
        var start  = new Date(data.placedStart);
        var end    = data.placedEnd ? new Date(data.placedEnd) : null;
        var fmt    = { hour: '2-digit', minute: '2-digit' };
        var timeStr = end
            ? start.toLocaleTimeString([], fmt) + ' – ' + end.toLocaleTimeString([], fmt)
            : start.toLocaleTimeString([], fmt);
        _setDetailValue('detail-time', 'detail-time-row', timeStr);
    } else {
        _setDetailValue('detail-time', 'detail-time-row', 'Not scheduled');
    }

    var menu = document.getElementById('detail-options-menu');
    if (menu) menu.classList.add('hidden');

    var isReadOnly = (data.status === '1');
    var optionsWrap = document.getElementById('detail-options-btn')
        ? document.getElementById('detail-options-btn').closest('.detail-options-wrap')
        : null;
    var footer = modal.querySelector('.detail-footer');
    if (optionsWrap) optionsWrap.style.display = isReadOnly ? 'none' : '';
    if (footer)      footer.style.display      = isReadOnly ? 'none' : '';

    modal.classList.remove('hidden');
}

function _setDetailValue(elId, rowId, value) {
    var el  = document.getElementById(elId);
    var row = document.getElementById(rowId);
    if (!el || !row) return;
    el.textContent    = value || '';
    row.style.display = value ? '' : 'none';
}


function enhanceCard(card) {
    if (card._enhanced) return;
    card._enhanced = true;

    if (typeof events !== 'undefined' && events) {
        var eventId = parseInt(card.dataset.eventId);
        var event = events.find(function(e) { return e.id === eventId; });
        if (event) {
            card.dataset.title       = event.title       || '';
            card.dataset.category    = event.category     || '';
            card.dataset.location    = event.location     || '';
            card.dataset.description = event.description  || '';
            card.dataset.importance  = event.importance   || '';
            card.dataset.duration    = event.duration     || '60';
        }
    }

    if (typeof schedule_events !== 'undefined' && schedule_events) {
        var seId = parseInt(card.dataset.id);
        var se = schedule_events.find(function(s) { return s.id === seId; });
        if (se) {
            card.dataset.placedStart = se.placed_start || '';
            card.dataset.placedEnd   = se.placed_end   || '';
        }
    }

    card.addEventListener('click', function(e) {
        e.stopPropagation();
        openDetailModal(card.dataset);
    });

    stretchCard(card);
}

function enhanceAllCards() {
    document.querySelectorAll('.card').forEach(enhanceCard);
}

async function unplaceInstance(currentCardId){
    if (!currentCardId) return false;

    try {
        var res = await fetch('/schedule-event/' + currentCardId + '/unplace/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
        });
        if (res.ok) {
            var card = document.querySelector('.card[data-id="' + currentCardId + '"]');
            if (card) {
                card.dataset.status = '1';
                card.style.height = '';
                card.style.minHeight = '';
                card.style.whiteSpace = '';
                card.style.alignItems = '';
                card.style.paddingTop = '';
                var container = document.getElementById('event-container');
                if (container) container.appendChild(card);
            }
            return true;
        }
        // Backend refused — surface the reason (e.g. instance is completed)
        var body = {};
        try { body = await res.json(); } catch (e) {}
        alert(body.error || 'Could not remove this event from the calendar.');
        return false;
    } catch (err) {
        console.error('Failed to unplace instance:', err);
        return false;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    var modal      = document.getElementById('detailModal');
    var closeBtn   = document.getElementById('detail-close');
    var optionsBtn = document.getElementById('detail-options-btn');
    var optionsMenu = document.getElementById('detail-options-menu');
    var deleteBtn  = document.getElementById('detail-delete');

    if (closeBtn) closeBtn.addEventListener('click', function() {
        modal.classList.add('hidden');
    });

    if (modal) modal.addEventListener('click', function(e) {
        if (e.target === modal) modal.classList.add('hidden');
    });

    if (optionsBtn && optionsMenu) {
        optionsBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            optionsMenu.classList.toggle('hidden');
        });
        document.addEventListener('click', function() {
            optionsMenu.classList.add('hidden');
        });
        optionsMenu.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }

    if (deleteBtn) deleteBtn.addEventListener('click', async function() {
        if (optionsMenu) optionsMenu.classList.add('hidden');
        if (modal) modal.classList.add('hidden');
        if (!_currentDetailCardId) return;
        var ok = await unplaceInstance(_currentDetailCardId);
        // Only reload on success — on 400 the user has seen an alert
        // explaining they need to unmark completion first.
        if (ok) window.location.reload();
    });

    var completedEl = document.getElementById('detail-completed');
    if (completedEl) {
        completedEl.addEventListener('change', async function() {
            if (!_currentDetailCardId) return;
            var newStatus = this.checked ? 3 : 2;
            try {
                var res = await fetch('/schedule-event/' + _currentDetailCardId + '/status/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken(),
                    },
                    body: JSON.stringify({ status: newStatus }),
                });
                if (res.ok) {
                    var card = document.querySelector('.card[data-id="' + _currentDetailCardId + '"]');
                    if (card) card.dataset.status = String(newStatus);
                } else {
                    this.checked = !this.checked;
                }
            } catch (err) {
                console.error('Failed to update status:', err);
                this.checked = !this.checked;
            }
        });
    }

    attachDropPreviewListeners();

    updateNowLine();
    setInterval(updateNowLine, 60000);

    reformatDayHeaders();
    var body = document.getElementById('gcal-body');
    if (body) {
        body.scrollTop = 7 * ENH_PX_PER_HOUR;
    }

    var observer = new MutationObserver(function(mutations) {
        for (var i = 0; i < mutations.length; i++) {
            var added = mutations[i].addedNodes;
            for (var j = 0; j < added.length; j++) {
                var node = added[j];
                if (node.nodeType === 1 && node.classList && node.classList.contains('card')) {
                    enhanceCard(node);
                }
            }
        }
    });

    var gridContainer = document.getElementById('grid-container');
    var eventContainer = document.getElementById('event-container');
    var observerConfig = { childList: true, subtree: true };

    if (gridContainer) observer.observe(gridContainer, observerConfig);
    if (eventContainer) observer.observe(eventContainer, observerConfig);

    setTimeout(enhanceAllCards, 500);
});
