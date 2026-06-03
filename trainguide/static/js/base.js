// ── Theme ──────────────────────────────────────────────────────────────────
function updateThemeUI(isDark) {
  // Desktop dropdown
  const label = document.getElementById('dd-theme-label');
  const icon  = document.getElementById('dd-theme-icon');
  if (label) label.textContent = isDark ? 'Тёмная тема' : 'Светлая тема';
  if (icon) {
    icon.innerHTML = isDark
      ? '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>'
      : '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>';
  }

  // Mobile toggle button
  const mobBtn   = document.getElementById('theme-toggle-mob');
  const mobThumb = mobBtn  ? mobBtn.querySelector('.mob-thumb')     : null;
  const mobSun   = mobBtn  ? mobBtn.querySelector('.mob-icon-sun')  : null;
  const mobMoon  = mobBtn  ? mobBtn.querySelector('.mob-icon-moon') : null;
  if (mobBtn) {
    mobBtn.style.background = isDark ? '#0088CC' : '#E2E8F0';
    if (mobThumb) mobThumb.style.transform = isDark ? 'translateX(20px)' : 'translateX(0)';
    if (mobSun)   mobSun.style.opacity  = isDark ? '0' : '1';
    if (mobMoon)  mobMoon.style.opacity = isDark ? '1' : '0';
  }
}

function toggleTheme() {
  const isDark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('tg-theme', isDark ? 'dark' : 'light');
  updateThemeUI(isDark);
}

(function initTheme() {
  const saved = localStorage.getItem('tg-theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const isDark = saved === 'dark' || (!saved && prefersDark);
  if (isDark) document.documentElement.classList.add('dark');
  updateThemeUI(isDark);
})();

// ── Profile dropdown ───────────────────────────────────────────────────────
function toggleProfile(e) {
  e.stopPropagation();
  document.getElementById('profile-dropdown').classList.toggle('open');
}
document.addEventListener('click', function () {
  document.getElementById('profile-dropdown').classList.remove('open');
});
document.getElementById('profile-dropdown').addEventListener('click', function (e) {
  e.stopPropagation();
});

// ── Mobile menu ────────────────────────────────────────────────────────────
function toggleMobileMenu() {
  document.getElementById('mobile-menu').classList.toggle('open');
  document.getElementById('icon-menu').classList.toggle('hidden');
  document.getElementById('icon-x').classList.toggle('hidden');
}
