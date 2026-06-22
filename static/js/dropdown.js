function showDropdownOptions(dropdownId) {
    document.getElementById(dropdownId).classList.toggle("displayed")
}

window.addEventListener("click", function (e) {
    if (!e.target.classList.contains("dropdown-dont-close-on-click")) {
        document.querySelectorAll(".dropdown-options.displayed").forEach(d => d.classList.remove("displayed"));
    }
});
