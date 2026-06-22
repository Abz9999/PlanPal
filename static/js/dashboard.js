// Khan - Fix 1
// Sort dropdown
function showSortOptions() {
    document.getElementById("sort-dropdown").classList.toggle("show");
}

function showFilterOptions() {
    document.getElementById("filter-dropdown").classList.toggle("show");
}

window.addEventListener("click", function (e) {
    if (!(e.target.matches(".dropdown-button") || e.target.matches(".dropdown-checkbox-element"))) {
        document.querySelectorAll(".dropdown-options.show").forEach(d => d.classList.remove("show"));
    }
});

// ========================
// Event detail overlay

const IMPORTANCE_COLOURS = { 5: '#c53030', 4: '#c05621', 3: '#b7791f', 2: '#276749', 1: '#2b6cb0' };

function openEventDetail(card) {
    // Guard: if the click came from the 3-dot menu or its dropdown items,
    // don't open the overlay. Use window.event defensively — on some paths
    // (e.g. DOMContentLoaded auto-open, programmatic card.click()) target
    // may be a Document which has no .closest().
    var ev = window.event;
    if (ev && ev.target && typeof ev.target.closest === 'function'
        && ev.target.closest('.card-dots-btn, .card-dropdown')) return;

    const d = card.dataset;
    const overlay = document.getElementById('eventDetailOverlay');
    const dialog  = document.getElementById('eventDetailDialog');

    document.getElementById('edTitle').textContent = d.title;

    const catBadge = document.getElementById('edCategoryBadge');
    if (d.category) {
        catBadge.textContent = d.category;
        catBadge.style.background = d.categoryColour + '30';
        catBadge.style.color      = d.categoryColour;
        catBadge.style.display    = '';
    } else {
        catBadge.style.display = 'none';
    }

    const impBadge = document.getElementById('edImportanceBadge');
    const impColour = IMPORTANCE_COLOURS[d.importanceLevel] || '#888';
    impBadge.textContent       = d.importance;
    impBadge.style.background  = impColour + '20';
    impBadge.style.color       = impColour;
    dialog.style.borderTopColor = impColour;

    // Time display: time-only (Case 5), dated, or duration-only
    if (d.timeOnly === 'true') {
        document.getElementById('edTime').textContent = d.constrainedTime || d.duration;
    } else if (d.hasTimes === 'true') {
        document.getElementById('edTime').textContent = d.start + ' – ' + d.end;
    } else {
        document.getElementById('edTime').textContent = d.duration;
    }

    const repeatRow = document.getElementById('edRepeatRow');
    if (d.repeatDays) {
        const weeks = d.repeatWeeks > 1 ? ` · ${d.repeatWeeks} weeks` : '';
        document.getElementById('edRepeat').textContent = d.repeatDays + weeks;
        repeatRow.style.display = '';
    } else {
        repeatRow.style.display = 'none';
    }

    const locRow = document.getElementById('edLocationRow');
    if (d.location) {
        document.getElementById('edLocation').textContent = d.location;
        locRow.style.display = '';
    } else {
        locRow.style.display = 'none';
    }

    const descRow = document.getElementById('edDescRow');
    if (d.description) {
        document.getElementById('edDescription').textContent = d.description;
        descRow.style.display = '';
    } else {
        descRow.style.display = 'none';
    }

    const mapSection = document.getElementById('edMapSection');
    const mapFrame   = document.getElementById('edMap');
    if (d.location) {
        mapFrame.src = 'https://www.google.com/maps?q=' + encodeURIComponent(d.location) + '&output=embed';
        mapSection.style.display = '';
    } else {
        mapFrame.src = '';
        mapSection.style.display = 'none';
    }

    const progressSection = document.getElementById('edProgressSection');
    const max = parseInt(d.max) || 0;
    if (max > 0) {
        const completed = parseInt(d.completed) || 0;
        const pct = Math.round((completed / max) * 100);
        document.getElementById('edProgressText').textContent = `${completed} of ${max} completed (${pct}%)`;
        document.getElementById('edProgressFill').style.width = pct + '%';
        progressSection.style.display = '';
    } else {
        progressSection.style.display = 'none';
    }

    document.getElementById('edDeleteForm').action = d.deleteUrl;
    document.getElementById('edCsrfToken').value = getCsrfToken();
    overlay.dataset.editUrl = d.editUrl;

    _showDetailView();
    document.getElementById('edFooterConfirm').classList.add('hidden');

    // Show overlay, then load instances
    overlay.classList.add('open');
    // overlay.classList.remove('hidden');  // main branch alternative approach
    overlay.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';

    _loadInstances(d.eventId, d);
}

function _loadInstances(eventId, eventData) {
    const list = document.getElementById('edInstancesList');
    list.innerHTML = '<span class="ed-loading">Loading instances…</span>';

    fetch(`/event/${eventId}/instances/`)
        .then(r => r.json())
        .then(data => {
            list.innerHTML = '';
            if (!data.instances || data.instances.length === 0) {
                list.innerHTML = '<span class="ed-empty">No instances yet.</span>';
                return;
            }
            data.instances.forEach(inst => {
                list.appendChild(_buildInstanceCard(inst, eventData));
            });
        })
        .catch(() => {
            list.innerHTML = '<span class="ed-empty">Could not load instances.</span>';
        });
}

function _buildInstanceCard(inst, eventData) {
    const completedActive = inst.status === 3;
    const missedActive    = inst.status === 4;
    const borderColour = IMPORTANCE_COLOURS[eventData.importanceLevel] || '#2b6cb0';
    const bgColour = eventData.categoryColour || '#888888';

    const startStr = inst.placed_start
        ? (() => {
            const s = new Date(inst.placed_start);
            const e = inst.placed_end ? new Date(inst.placed_end) : null;
            const timeFmt = { hour: '2-digit', minute: '2-digit' };
            if (eventData.hasTimes === 'true') {
                return s.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
            }
            return e
                ? s.toLocaleTimeString([], timeFmt) + ' – ' + e.toLocaleTimeString([], timeFmt)
                : s.toLocaleTimeString([], timeFmt);
        })()
        : eventData.duration;

    const card = document.createElement('div');
    card.className = 'instance-card';
    card.dataset.instanceId = inst.id;
    card.style.backgroundColor = bgColour + '20';
    card.style.border = `3px solid ${borderColour}`;

    card.innerHTML = `
        <div class="card-layout">
            <div class="slot-tl">
                <div class="status-circles">
                    <button class="status-btn complete-btn ${completedActive ? 'active' : ''}"
                            onclick="setInstanceStatus(${inst.id}, 3, this)" title="Mark completed">&#10003;</button>
                    <button class="status-btn missed-btn ${missedActive ? 'active' : ''}"
                            onclick="setInstanceStatus(${inst.id}, 4, this)" title="Mark missed">&#10007;</button>
                </div>
            </div>
            <div class="slot-tr"><span class="instance-num">#${inst.occurrence_index}</span></div>
            <div class="slot-mid"><h6 class="card-title">${eventData.title}</h6></div>
            <div class="slot-bl"><span class="card-duration">${startStr}</span></div>
            <div class="slot-br"><span class="card-counter">${eventData.scheduled || 0} / ${eventData.max || 0}</span></div>
        </div>
    `;
    return card;
}

function _showDetailView() {
    document.getElementById('edBody').style.display = '';
    document.getElementById('edEditBody').style.display = 'none';
    document.getElementById('edFooterMain').classList.remove('hidden');
    document.getElementById('edFooterEdit').classList.add('hidden');
}

function _showEditView(editUrl) {
    const editBody = document.getElementById('edEditBody');
    editBody.innerHTML = '<span class="ed-loading">Loading form…</span>';
    document.getElementById('edBody').style.display = 'none';
    editBody.style.display = '';
    document.getElementById('edFooterMain').classList.add('hidden');
    document.getElementById('edFooterEdit').classList.remove('hidden');

    fetch(editUrl)
        .then(r => r.text())
        .then(html => {
            editBody.innerHTML = html;
            _bindEditDayLimit(editBody);
        })
        .catch(() => { editBody.innerHTML = '<span class="ed-empty">Could not load form.</span>'; });
}

function _bindEditDayLimit(container) {
    const numDaysInput = container.querySelector("[name='number_of_days']");
    if (!numDaysInput) return;

    function enforce() {
        const limit = parseInt(numDaysInput.value) || 0;
        const allBoxes = container.querySelectorAll("[name='repeat_days']");
        const checkedCount = [...allBoxes].filter(cb => cb.checked).length;
        allBoxes.forEach(cb => {
            if (!cb.checked) {
                cb.disabled = limit > 0 && checkedCount >= limit;
            }
        });
    }

    // Case 1 — all four date/time fields set — is a one-off, so lock out
    // the repeat fields. Called on load + whenever date/time inputs change.
    function enforceCase1Lockout() {
        const sd = container.querySelector("[name='start_date']")?.value;
        const st = container.querySelector("[name='start_time']")?.value;
        const ed = container.querySelector("[name='end_date']")?.value;
        const et = container.querySelector("[name='end_time']")?.value;
        const isCase1 = !!(sd && st && ed && et);
        const weeksInput = container.querySelector("[name='repeat_weeks']");

        numDaysInput.disabled = isCase1;
        if (weeksInput) weeksInput.disabled = isCase1;
        container.querySelectorAll("[name='repeat_days']").forEach(cb => {
            if (isCase1) {
                cb.checked = false;
                cb.disabled = true;
            }
        });
        if (isCase1) {
            numDaysInput.value = 1;
            if (weeksInput) weeksInput.value = 1;
        }
    }

    numDaysInput.addEventListener("input", () => {
        container.querySelectorAll("[name='repeat_days']").forEach(cb => {
            cb.checked = false;
            cb.disabled = false;
        });
        enforce();
    });

    container.querySelectorAll("[name='repeat_days']").forEach(cb => {
        cb.addEventListener("change", enforce);
    });

    // Re-run the Case 1 check whenever any of the four date/time fields change
    ["start_date", "start_time", "end_date", "end_time"].forEach(name => {
        const el = container.querySelector(`[name='${name}']`);
        if (el) el.addEventListener("input", enforceCase1Lockout);
    });

    enforce();
    enforceCase1Lockout();
}


function closeEventDetail() {
    const overlay = document.getElementById('eventDetailOverlay');
    overlay.classList.remove('open');
    overlay.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    document.getElementById('edMap').src = '';
}

document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('edClose').addEventListener('click', closeEventDetail);
    document.getElementById('eventDetailOverlay').addEventListener('click', function (e) {
        if (e.target === this) closeEventDetail();
    });
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closeEventDetail();
    });

    document.getElementById('edDeleteBtn').addEventListener('click', function () {
        document.getElementById('edFooterMain').classList.add('hidden');
        document.getElementById('edFooterConfirm').classList.remove('hidden');
    });
    document.getElementById('edCancelDelete').addEventListener('click', function () {
        document.getElementById('edFooterConfirm').classList.add('hidden');
        document.getElementById('edFooterMain').classList.remove('hidden');
    });

    document.getElementById('edEditBtn').addEventListener('click', function () {
        _showEditView(document.getElementById('eventDetailOverlay').dataset.editUrl);
    });
    document.getElementById('edCancelEdit').addEventListener('click', _showDetailView);

    // Save edit via AJAX — with client-side date validation
    document.getElementById('edSaveEdit').addEventListener('click', function () {
        const form = document.getElementById('edEditForm');
        if (!form) return;

        // Client-side date validation before submitting
        const errEl = document.getElementById('edEditErrors');
        errEl.textContent = '';
        errEl.classList.add('hidden');

        const sd = form.querySelector('[name="start_date"]')?.value || '';
        const st = form.querySelector('[name="start_time"]')?.value || '';
        const ed = form.querySelector('[name="end_date"]')?.value || '';
        const et = form.querySelector('[name="end_time"]')?.value || '';
        const hrs = parseInt(form.querySelector('[name="hours"]')?.value) || 0;
        const mins = parseInt(form.querySelector('[name="minutes"]')?.value) || 0;
        const hasDuration = hrs > 0 || mins > 0;

        // Validate date combinations match the 5 valid cases
        const hasSD = !!sd, hasST = !!st, hasED = !!ed, hasET = !!et;

        let dateError = '';
        if (hasSD && hasST && hasED && hasET) {
            // Case 1: full start + end — check end > start
            const startDT = new Date(sd + 'T' + st);
            const endDT = new Date(ed + 'T' + et);
            if (endDT <= startDT) dateError = 'End date/time must be after start date/time.';
        } else if (hasSD && hasST && !hasED && !hasET) {
            // Case 2: start only — need duration
            if (!hasDuration) dateError = 'Duration is required when no end time is provided.';
        } else if (hasSD && !hasST && !hasED && !hasET) {
            // Case 4: date only — need duration
            if (!hasDuration) dateError = 'Duration is required when only a date is provided.';
        } else if (!hasSD && hasST && !hasED && hasET) {
            // Case 5: times only
            const [sh, sm] = st.split(':').map(Number);
            const [eh, em] = et.split(':').map(Number);
            if (eh * 60 + em <= sh * 60 + sm) dateError = 'End time must be after start time.';
        } else if (!hasSD && !hasST && !hasED && !hasET) {
            // Case 3: no dates — need duration
            if (!hasDuration) dateError = 'You must provide a duration if no dates are set.';
        } else {
            // Invalid partial combination
            if (hasSD && !hasST) dateError = 'Please provide a start time with the start date, or remove the date.';
            else if (hasED && !hasET) dateError = 'Please provide an end time with the end date.';
            else if (hasET && !hasST && !hasSD) dateError = 'Please provide a start time or date.';
            else dateError = 'Invalid date combination. Fill in both start and end, or leave all date fields empty.';
        }

        if (dateError) {
            errEl.textContent = dateError;
            errEl.classList.remove('hidden');
            return;
        }

        // Re-enable Case 1 locked fields so their values get serialised into
        // FormData — disabled inputs are silently dropped by the browser.
        // Same issue as the Create wizard; we re-disable right after so the
        // UI state doesn't change.
        const lockedFields = form.querySelectorAll('[disabled]');
        lockedFields.forEach(f => { f.disabled = false; });

        const data = new FormData(form);

        lockedFields.forEach(f => { f.disabled = true; });

        fetch(form.dataset.eventId ? `/event/${form.dataset.eventId}/edit/` : form.action, {
            method: 'POST',
            body: data,
            headers: { 'X-CSRFToken': getCsrfToken() }
        })
        .then(r => r.json())
        .then(resp => {
            if (resp.ok) {
                closeEventDetail();
                location.reload();
            } else {
                errEl.textContent = Object.values(resp.errors).flat().join(' ');
                errEl.classList.remove('hidden');
            }
        })
        .catch(() => alert('Save failed. Please try again.'));
    });
});

// Instance status update
function getCsrfToken() {
    const match = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
    return match ? match.split('=')[1] : '';
}

function setInstanceStatus(instanceId, status, clickedBtn) {
    fetch(`/schedule-event/${instanceId}/status/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
        body: JSON.stringify({ status: status })
    })
    .then(r => r.json())
    .then(data => {
        if (data.ok) {
            const card = clickedBtn.closest('.instance-card');
            card.querySelectorAll('.status-btn').forEach(b => b.classList.remove('active'));
            clickedBtn.classList.add('active');
        }
    })
    .catch(err => console.error('Status update failed:', err));
}

// 3-dots card dropdown
function toggleDropdown(e, eventId) {
    e.stopPropagation();
    const dropdown = document.getElementById(`dropdown-${eventId}`);
    document.querySelectorAll('.card-dropdown.open').forEach(d => {
        if (d !== dropdown) d.classList.remove('open');
    });
    dropdown.classList.toggle('open');
}

document.addEventListener('click', () => {
    document.querySelectorAll('.card-dropdown.open').forEach(d => d.classList.remove('open'));
});

function editEvent(e, eventId) {
    e.stopPropagation();
    // close any open 3-dot dropdown
    document.querySelectorAll('.card-dropdown.open').forEach(d => d.classList.remove('open'));
    const card = document.querySelector('.event-card[data-event-id="' + eventId + '"]');
    if (!card) return;
    // Fire a fresh click on the card after this one settles. This avoids the
    // openEventDetail guard seeing the dropdown button as window.event.target.
    setTimeout(function () {
        card.click();
        setTimeout(function () {
            var btn = document.getElementById('edEditBtn');
            if (btn) btn.click();
        }, 50);
    }, 0);
}

// Auto-open the edit overlay when the URL has ?edit=<event_id>.
// Used by the main page calendar's detail modal to send users here for
// editing without duplicating the edit form UI in that modal.
document.addEventListener('DOMContentLoaded', function () {
    var params = new URLSearchParams(window.location.search);
    var editId = params.get('edit');
    if (!editId) return;
    var card = document.querySelector('.event-card[data-event-id="' + editId + '"]');
    if (!card) return;
    setTimeout(function () {
        card.click();
        setTimeout(function () {
            var btn = document.getElementById('edEditBtn');
            if (btn) btn.click();
        }, 100);
    }, 50);
});

function confirmDelete(title) {
    return confirm(`Delete "${title}" and all its instances? This cannot be undone.`);
}
