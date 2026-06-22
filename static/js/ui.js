
/* -----------------------------------------
   Profile dropdown toggle
   ----------------------------------------- */
(function () {
  const profileBtn = document.getElementById('profile-btn');
  const profileMenu = document.getElementById('profile-menu');
  if (!profileBtn || !profileMenu) return;

  profileBtn.addEventListener('click', function (e) {
    e.stopPropagation();
    profileMenu.classList.toggle('open');
  });
  document.addEventListener('click', function () {
    profileMenu.classList.remove('open');
  });
})();

/* -----------------------------------------
   Mini calendar picker
   Reads config from window.MINI_CAL_CONFIG,
   set as an inline script in main_page.html
   ----------------------------------------- */
(function () {
  const btn = document.getElementById('mini-cal-btn');
  const cal = document.getElementById('mini-cal');
  const title = document.getElementById('mini-cal-title');
  const daysEl = document.getElementById('mini-cal-days');
  if (!btn || !cal) return;

  const config = window.MINI_CAL_CONFIG || {};
  const mainPageUrl = config.mainPageUrl || '/';
  const currentType = config.currentType || 'week';

  let viewDate = new Date();

  function getMondayOf(date) {
    const d = new Date(date);
    const day = d.getDay();
    const diff = day === 0 ? -6 : 1 - day;
    d.setDate(d.getDate() + diff);
    return d;
  }

  function formatDate(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return y + '-' + m + '-' + dd;
  }

  function render() {
    const months = ['January','February','March','April','May','June','July','August','September','October','November','December'];
    title.textContent = months[viewDate.getMonth()] + ' ' + viewDate.getFullYear();
    daysEl.innerHTML = '';

    const year = viewDate.getFullYear();
    const month = viewDate.getMonth();
    const first = new Date(year, month, 1);
    let startDow = first.getDay();
    startDow = startDow === 0 ? 6 : startDow - 1;
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const today = new Date();

    for (let i = 0; i < startDow; i++) {
      daysEl.appendChild(document.createElement('div'));
    }

    for (let d = 1; d <= daysInMonth; d++) {
      const dayBtn = document.createElement('button');
      dayBtn.textContent = d;
      const isToday = new Date(year, month, d).toDateString() === today.toDateString();
      dayBtn.style.cssText = 'background:' + (isToday ? '#111' : 'none') + '; color:' + (isToday ? '#fff' : '#111') + '; border:none; cursor:pointer; padding:0; border-radius:50%; font-size:12px; width:28px; height:28px; display:flex; align-items:center; justify-content:center; margin:auto;';

      dayBtn.addEventListener('mouseover', function () {
        if (!isToday) this.style.background = '#f0f0f0';
      });
      dayBtn.addEventListener('mouseout', function () {
        if (!isToday) this.style.background = 'none';
      });
      dayBtn.addEventListener('click', function () {
        const clicked = new Date(year, month, d);
        const navDate = currentType === 'day' ? clicked : getMondayOf(clicked);
        // Preserve existing URL params (filter, schedule, etc.) verbatim and
        // only override type + week. Building the filter from a Django-rendered
        // list repr corrupts it into "['all']" and empties the queryset server-side.
        const params = new URLSearchParams(window.location.search);
        params.set('type', currentType);
        params.set('week', formatDate(navDate));
        window.location.href = mainPageUrl + '?' + params.toString();
      });

      daysEl.appendChild(dayBtn);
    }
  }

  btn.addEventListener('click', function (e) {
    e.stopPropagation();
    const isOpen = cal.style.display !== 'none';
    cal.style.display = isOpen ? 'none' : 'block';
    if (!isOpen) render();
  });

  document.getElementById('mini-cal-prev').addEventListener('click', function (e) {
    e.stopPropagation();
    viewDate.setMonth(viewDate.getMonth() - 1);
    render();
  });
  document.getElementById('mini-cal-next').addEventListener('click', function (e) {
    e.stopPropagation();
    viewDate.setMonth(viewDate.getMonth() + 1);
    render();
  });

  document.addEventListener('click', function () { cal.style.display = 'none'; });
  cal.addEventListener('click', function (e) { e.stopPropagation(); });
})();
