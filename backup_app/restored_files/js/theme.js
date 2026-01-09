/* Theme Toggle Script*/
(function () {
  const KEY = 'theme-preference';

  function getPreference() {
    const saved = localStorage.getItem(KEY);
    if (saved === 'dark' || saved === 'light') return saved;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function applyPreference(pref) {
    if (pref === 'dark') document.body.classList.add('dark');
    else document.body.classList.remove('dark');
    updateIcon();
  }

  function toggleTheme() {
    const isDark = document.body.classList.toggle('dark');
    localStorage.setItem(KEY, isDark ? 'dark' : 'light');
    updateIcon();
  }

  function updateIcon() {
    const btn = document.querySelector('.header .icon-btn[title="Toggle dark mode"]');
    if (!btn) return;
    btn.textContent = document.body.classList.contains('dark') ? '☀️' : '🌙';
  }

  document.addEventListener('DOMContentLoaded', function () {
    applyPreference(getPreference());
    const btn = document.querySelector('.header .icon-btn[title="Toggle dark mode"]');
    if (btn) btn.addEventListener('click', toggleTheme);
    window.toggleTheme = toggleTheme;
  });
})();
