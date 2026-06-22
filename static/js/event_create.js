(function () {
  const modal = document.getElementById("createEventModal");
  const body = document.getElementById("createEventModalBody");
  const openBtn = document.getElementById("btn-create-event");
  const closeBtn = document.getElementById("closeCreateEvent");

  if (!modal || !body || !openBtn || !closeBtn) return;

  function openModal() {
    modal.style.display = "flex"; 
  }

  function closeModal() {
    modal.style.display = "none";
    body.innerHTML = "";
  }

  async function loadForm() {
    const res = await fetch(CREATE_EVENT_URL, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    body.innerHTML = await res.text();
    bindFormSubmit();
  }

  async function submitForm(form) {
    const res = await fetch(form.action, {
      method: "POST",
      headers: { "X-Requested-With": "XMLHttpRequest" },
      body: new FormData(form),
    });

    const html = await res.text();
    body.innerHTML = html;

   
    if (res.redirected) {
      closeModal();
      location.reload();
      return;
    }

    
    bindFormSubmit();
  }

  function bindFormSubmit() {
    const form = body.querySelector("form");
    if (!form || form.dataset.bound === "1") return;

    form.dataset.bound = "1";
    form.addEventListener("submit", (e) => {
        e.preventDefault();
        submitForm(form);
    });
  }

  openBtn.addEventListener("click", async () => {
    openModal();
    await loadForm();
  });

  closeBtn.addEventListener("click", closeModal);

 
  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });
})();