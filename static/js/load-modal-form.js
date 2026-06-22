const modal = document.getElementById("eventModal");
const modalBody = document.getElementById("modalBody");
const button = document.getElementById("btn-create-event");

button.addEventListener("click", async function (e) {
    e.preventDefault();
    const currentPage = window.location.pathname + window.location.search;
    const response = await fetch(`/create_event/?next=${encodeURIComponent(currentPage)}`);
    const html = await response.text();
    modalBody.innerHTML = html;

    modal.classList.remove("hidden");

    initializeEventForm();
});

modal.addEventListener("click", function (e) {
    if (e.target === modal) {
        modal.classList.add("hidden");
    }
});