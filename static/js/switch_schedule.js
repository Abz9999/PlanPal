// Created by Frankie

document.addEventListener('DOMContentLoaded', () => {
    loadSchedules();
    initNewScheduleModal();
});

document.getElementById('btn-switch-schedule').addEventListener('click', function(e) {
    e.stopPropagation();
    const dropdown = document.getElementById('schedule-dropdown');
    const isHidden = dropdown.style.display === 'none' || dropdown.style.display === '';
    dropdown.style.display = isHidden ? 'block' : 'none';
});

function loadSchedules() {
    fetch('/api/schedules/')
        .then(r => r.json())
        .then(data => {
            const list = document.getElementById('schedule-list');
            const currentId = new URL(window.location.href).searchParams.get('schedule');
            list.innerHTML = '';
            data.schedules.forEach(s => {
                const isSelected = currentId ? String(s.id) === currentId : s.is_active;
                if (isSelected) {
                    document.getElementById('active-schedule-name').textContent = s.title;
                }

                const row = document.createElement('div');
                row.className = 'schedule-row';

                const btn = document.createElement('button');
                btn.textContent = s.title;
                btn.className = 'schedule-item-btn';
                if (isSelected) btn.classList.add('active-schedule');
                btn.addEventListener('click', () => selectSchedule(s.id));

                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'schedule-delete-btn';
                deleteBtn.innerHTML = '&#128465;';
                deleteBtn.title = 'Delete schedule';
                deleteBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    document.getElementById('schedule-dropdown').style.display = 'none';
                    openDeleteConfirmModal(s.id, s.title);
                });

                row.appendChild(btn);
                row.appendChild(deleteBtn);
                list.appendChild(row);
            });

            const divider = document.createElement('div');
            divider.className = 'schedule-divider';
            list.appendChild(divider);

            const newBtn = document.createElement('button');
            newBtn.textContent = '+ New Schedule';
            newBtn.className = 'new-schedule-btn';
            newBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                document.getElementById('schedule-dropdown').style.display = 'none';
                openNewScheduleModal();
            });
            list.appendChild(newBtn);
        });
}

function selectSchedule(id) {
    const url = new URL(window.location.href);
    url.searchParams.set('schedule', id);
    window.location.href = url.toString();
}

function openNewScheduleModal() {
    const modal = document.getElementById('newScheduleModal');
    const input = document.getElementById('new-schedule-title');
    const error = document.getElementById('new-schedule-error');
    input.value = '';
    error.style.display = 'none';
    modal.classList.remove('hidden');
    input.focus();
}

function initNewScheduleModal() {
    const modal    = document.getElementById('newScheduleModal');
    const input    = document.getElementById('new-schedule-title');
    const errorEl  = document.getElementById('new-schedule-error');
    const submitBtn = document.getElementById('new-schedule-submit');
    const cancelBtn = document.getElementById('new-schedule-cancel');

    cancelBtn.addEventListener('click', () => modal.classList.add('hidden'));

    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.add('hidden');
    });

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') submitBtn.click();
    });

    submitBtn.addEventListener('click', () => {
        const title = input.value.trim();
        if (!title) {
            errorEl.textContent = 'Please enter a name for the schedule.';
            errorEl.style.display = 'block';
            return;
        }
        submitBtn.disabled = true;
        fetch('/api/schedules/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({ title }),
        })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                errorEl.textContent = data.error;
                errorEl.style.display = 'block';
                submitBtn.disabled = false;
                return;
            }
            modal.classList.add('hidden');
            selectSchedule(data.id);  // immediately switch to the new schedule
        })
        .catch(() => {
            errorEl.textContent = 'Something went wrong. Please try again.';
            errorEl.style.display = 'block';
            submitBtn.disabled = false;
        });
    });
}

function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? match[2] : '';
}

function openDeleteConfirmModal(id, title) {
    const modal = document.getElementById('deleteScheduleModal');
    document.getElementById('delete-schedule-message').textContent =
        `Are you sure you want to delete "${title}"? This cannot be undone.`;
    modal.classList.remove('hidden');

    const confirmBtn = document.getElementById('delete-schedule-confirm');
    const cancelBtn  = document.getElementById('delete-schedule-cancel');

    // Clone buttons to remove any previous listeners
    const newConfirm = confirmBtn.cloneNode(true);
    const newCancel  = cancelBtn.cloneNode(true);
    confirmBtn.replaceWith(newConfirm);
    cancelBtn.replaceWith(newCancel);

    newCancel.addEventListener('click', () => modal.classList.add('hidden'));
    modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.add('hidden'); }, { once: true });

    newConfirm.addEventListener('click', () => {
        newConfirm.disabled = true;
        fetch(`/api/schedules/${id}/`, {
            method: 'DELETE',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
        })
        .then(r => r.json())
        .then(() => {
            modal.classList.add('hidden');
            // If we were viewing the deleted schedule, reload without the param
            const url = new URL(window.location.href);
            if (url.searchParams.get('schedule') === String(id)) {
                url.searchParams.delete('schedule');
            }
            window.location.href = url.toString();
        });
    });
}

document.addEventListener('click', function() {
    document.getElementById('schedule-dropdown').style.display = 'none';
});
