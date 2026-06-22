function openModal(id) {
    document.getElementById(id).classList.add('open');
}

function closeModal(overlay) {
    overlay.classList.remove('open');
    // Reset any open detail panels back to the list view
    overlay.querySelectorAll('.instance-detail').forEach(function (d) {
        d.style.display = 'none';
    });
    overlay.querySelectorAll('.instance-list-view').forEach(function (l) {
        l.style.display = 'block';
    });
}

function showInstanceDetail(detailId, listId) {
    document.getElementById(listId).style.display = 'none';
    document.getElementById(detailId).style.display = 'block';
}

function showInstanceList(detailId, listId) {
    document.getElementById(detailId).style.display = 'none';
    document.getElementById(listId).style.display = 'block';
}

function toggleDropdown(e, eventId) {
    e.stopPropagation();
    const dropdown = document.getElementById(`dropdown-${eventId}`);
    document.querySelectorAll('.card-dropdown.open').forEach(function (d) {
        if (d !== dropdown) d.classList.remove('open');
    });
    dropdown.classList.toggle('open');
}

function editEvent(e) {
    e.stopPropagation();
    alert('Edit event - coming soon');
}

function confirmDelete(title) {
    return confirm(`Delete "${title}" and all its instances? This cannot be undone.`);
}

document.addEventListener('click', function () {
    document.querySelectorAll('.card-dropdown.open').forEach(function (d) {
        d.classList.remove('open');
    });
});

document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal-overlay.open').forEach(function (m) {
            closeModal(m);
        });
    }
});
