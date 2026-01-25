// Build a compact "Nesta página" TOC inside a Bootstrap offcanvas.
document.addEventListener('DOMContentLoaded', () => {
  const main = document.querySelector('main.content');
  if (!main) return;

  const headings = Array.from(main.querySelectorAll('h1, h2, h3'))
    .filter((el) => {
      if (el.textContent.trim().length === 0) return false;
      // Exclude headings generated inside the individual profiles cards.
      if (el.closest('#individual-profiles')) return false;
      return true;
    });

  if (!headings.length) return;

  const list = document.createElement('ul');
  list.className = 'toc-offcanvas-list';

  const seen = new Set();

  headings.forEach((heading) => {
    const dataAnchor = heading.getAttribute('data-anchor-id');
    const sectionAnchor = heading.closest('section[id]')?.id || '';
    const anchorId = heading.id || dataAnchor || sectionAnchor;
    if (!anchorId || seen.has(anchorId)) return;
    seen.add(anchorId);

    const li = document.createElement('li');
    li.className = `toc-level-${heading.tagName.toLowerCase()}`;

    const link = document.createElement('a');
    link.className = 'toc-offcanvas-link';
    link.href = `#${anchorId}`;
    link.textContent = heading.textContent.trim();

    li.appendChild(link);
    list.appendChild(li);
  });

  const offcanvas = document.createElement('div');
  offcanvas.className = 'offcanvas offcanvas-start toc-offcanvas';
  offcanvas.id = 'toc-offcanvas';
  offcanvas.tabIndex = -1;
  offcanvas.setAttribute('aria-labelledby', 'toc-offcanvas-label');
  offcanvas.innerHTML = `
    <div class="offcanvas-header">
      <h5 class="offcanvas-title" id="toc-offcanvas-label">Nesta página</h5>
      <button type="button" class="btn-close btn-close-white" data-bs-dismiss="offcanvas" aria-label="Fechar"></button>
    </div>
    <div class="offcanvas-body"></div>
  `;

  offcanvas.querySelector('.offcanvas-body').appendChild(list);
  document.body.appendChild(offcanvas);

  const tools = document.querySelector('.quarto-navbar-tools');
  const nav = document.querySelector('.navbar-nav');
  const target = tools || nav;

  if (target) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-sm btn-outline-light toc-toggle-btn';
    button.setAttribute('data-bs-toggle', 'offcanvas');
    button.setAttribute('data-bs-target', '#toc-offcanvas');
    button.setAttribute('aria-controls', 'toc-offcanvas');
    button.textContent = 'Nesta página';

    if (tools) {
      tools.prepend(button);
    } else {
      const item = document.createElement('li');
      item.className = 'nav-item';
      item.appendChild(button);
      target.appendChild(item);
    }
  }

  offcanvas.addEventListener('click', (event) => {
    if (event.target instanceof HTMLAnchorElement && window.bootstrap) {
      const instance = window.bootstrap.Offcanvas.getInstance(offcanvas);
      if (instance) instance.hide();
    }
  });
});
