// Shared navigation component
const pages = [
  { href: 'index.html', label: 'Overview' },
  { href: 'pattern1.html', label: 'P1: Direct SDK' },
  { href: 'pattern2.html', label: 'P2: Access Control' },
  { href: 'pattern3.html', label: 'P3: Gateway' },
  { href: 'pattern4.html', label: 'P4: Cedar' },
  { href: 'pattern5.html', label: 'P5: JWT' },
  { href: 'pattern6.html', label: 'P6: JWT+Cedar' },
  { href: 'pattern7.html', label: 'P7: Interceptor' },
  { href: 'pattern8.html', label: 'P8: Full Stack' },
];

function renderNav() {
  const current = location.pathname.split('/').pop() || 'index.html';
  const nav = document.getElementById('main-nav');
  if (!nav) return;
  const links = pages.map(p =>
    `<a href="${p.href}" class="${current === p.href ? 'active' : ''}">${p.label}</a>`
  ).join('');
  nav.innerHTML = `<div class="nav-inner"><a href="index.html" class="logo">🔒 <span>FMKB Security Patterns</span></a><div class="nav-links">${links}</div></div>`;
}

document.addEventListener('DOMContentLoaded', renderNav);
