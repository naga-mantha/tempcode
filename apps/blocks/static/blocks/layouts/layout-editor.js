(function () {
  const GRID_SELECTOR = '[data-layout-grid]';

  function collectNodes(container) {
    const items = Array.from(container.querySelectorAll('.grid-stack-item'));
    return items.map((item, index) => {
      const width = parseInt(item.dataset.gsWidth || container.dataset.defaultWidth || '1', 10) || 1;
      const height = parseInt(item.dataset.gsHeight || container.dataset.defaultHeight || '1', 10) || 1;
      const x = parseInt(item.dataset.gsX || '0', 10) || 0;
      const y = parseInt(item.dataset.gsY || String(index), 10) || index;
      item.dataset.order = String(index);
      return {
        slug: item.dataset.slug,
        x,
        y,
        width,
        height,
        order: index,
      };
    });
  }

  function postUpdate(container) {
    const url = container.dataset.updateUrl;
    if (!url || typeof window.htmx === 'undefined') {
      return;
    }
    const nodes = collectNodes(container);
    if (!nodes.length) {
      return;
    }
    const payload = {
      blocks: nodes,
    };
    window.htmx.ajax('POST', url, {
      headers: { 'Content-Type': 'application/json' },
      swap: 'none',
      values: {},
      body: JSON.stringify(payload),
    });
  }

  function toggleEmptyState(container) {
    const indicatorSelector = container.dataset.emptyIndicator;
    if (!indicatorSelector) {
      return;
    }
    const indicator = document.querySelector(indicatorSelector);
    if (!indicator) {
      return;
    }
    const hasBlocks = Boolean(container.querySelector('.grid-stack-item'));
    indicator.classList.toggle('d-none', hasBlocks);
  }

  function bindGrid(container, { refreshOnly = false } = {}) {
    if (!container) {
      return;
    }
    if (typeof window.GridStack === 'undefined') {
      return;
    }
    const margin = parseInt(container.dataset.gridGap || '15', 10) || 15;
    const grid = window.GridStack.init({ margin }, container);
    container.dataset.layoutGridBound = '1';

    if (refreshOnly) {
      grid.refresh();
      toggleEmptyState(container);
      return;
    }

    const handler = () => {
      toggleEmptyState(container);
      postUpdate(container);
    };

    grid.on('change', handler);
    grid.on('resizestop', handler);
    toggleEmptyState(container);
  }

  function resetAddForm() {
    const form = document.getElementById('layoutAddBlockForm');
    if (form) {
      form.reset();
    }
  }

  function initAllGrids() {
    document.querySelectorAll(GRID_SELECTOR).forEach((container) => {
      if (container.dataset.layoutGridBound === '1') {
        bindGrid(container, { refreshOnly: true });
      } else {
        bindGrid(container);
      }
    });
  }

  document.addEventListener('DOMContentLoaded', initAllGrids);

  document.addEventListener('htmx:afterSwap', (event) => {
    const target = event.target;
    if (!target) {
      return;
    }
    let container = null;
    if (target.matches(GRID_SELECTOR)) {
      container = target;
      bindGrid(target, { refreshOnly: true });
      resetAddForm();
    } else {
      container = target.closest(GRID_SELECTOR);
      if (container) {
        bindGrid(container, { refreshOnly: true });
      }
    }
    initAllGrids();
    if (container) {
      postUpdate(container);
    }
  });

  document.addEventListener('htmx:afterRequest', () => {
    document.querySelectorAll(GRID_SELECTOR).forEach(toggleEmptyState);
  });
})();
