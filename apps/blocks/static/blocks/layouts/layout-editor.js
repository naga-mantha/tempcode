(function () {
  const GRID_SELECTOR = '[data-layout-grid]';
  const RESIZER_SELECTOR = '[data-grid-resizer]';

  function parseColumnCount(container) {
    const direct =
      container.dataset.gridColumns ||
      container.style.getPropertyValue('--grid-columns') ||
      getComputedStyle(container).getPropertyValue('--grid-columns') ||
      '12';
    const parsed = parseInt(String(direct).trim(), 10);
    return Number.isNaN(parsed) || parsed <= 0 ? 12 : parsed;
  }

  function parseRowHeight(container) {
    const dataValue = container.dataset.gridRowHeight;
    const dataParsed = dataValue ? parseFloat(dataValue) : NaN;
    if (!Number.isNaN(dataParsed) && dataParsed > 0) {
      return dataParsed;
    }
    const computed = getComputedStyle(container).getPropertyValue(
      '--grid-row-height'
    );
    const parsed = parseFloat(computed);
    return Number.isNaN(parsed) || parsed <= 0 ? 200 : parsed;
  }

  function dispatchResize(item, width, height, { commit = false } = {}) {
    const detail = {};
    if (typeof width === 'number' && !Number.isNaN(width)) {
      detail.width = width;
    }
    if (typeof height === 'number' && !Number.isNaN(height)) {
      detail.height = height;
    }
    detail.commit = Boolean(commit);
    item.dispatchEvent(new CustomEvent('layout:resize', { detail }));
  }

  function bindResizeHandles(container) {
    container.querySelectorAll(RESIZER_SELECTOR).forEach((handle) => {
      if (handle.dataset.gridResizerBound === '1') {
        return;
      }
      handle.dataset.gridResizerBound = '1';

      handle.addEventListener('pointerdown', (event) => {
        const item = handle.closest('.grid-stack-item');
        if (!item) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();

        const pointerId = event.pointerId;
        if (handle.setPointerCapture) {
          try {
            handle.setPointerCapture(pointerId);
          } catch (err) {
            /* no-op */
          }
        }

        const wasDraggable = item.draggable;
        item.draggable = false;
        handle.classList.add('is-resizing');

        const startX = event.clientX;
        const startY = event.clientY;
        const startWidth =
          parseInt(
            item.dataset.gsWidth || container.dataset.defaultWidth || '1',
            10
          ) || 1;
        const startHeight =
          parseInt(
            item.dataset.gsHeight || container.dataset.defaultHeight || '1',
            10
          ) || 1;
        const columns = parseColumnCount(container);
        const rowHeight = parseRowHeight(container);
        const bounds = container.getBoundingClientRect();
        const columnWidth = bounds.width / columns;
        let hasResized = false;

        const onPointerMove = (moveEvent) => {
          moveEvent.preventDefault();
          moveEvent.stopPropagation();
          if (!Number.isFinite(columnWidth) || columnWidth <= 0) {
            return;
          }
          const deltaX = moveEvent.clientX - startX;
          const deltaY = moveEvent.clientY - startY;
          let nextWidth = startWidth + deltaX / columnWidth;
          let nextHeight = startHeight + deltaY / rowHeight;
          nextWidth = Math.round(nextWidth);
          nextHeight = Math.round(nextHeight);
          nextWidth = Math.max(1, Math.min(nextWidth, columns));
          nextHeight = Math.max(1, nextHeight);
          const currentWidth =
            parseInt(item.dataset.gsWidth || '1', 10) || startWidth;
          const currentHeight =
            parseInt(item.dataset.gsHeight || '1', 10) || startHeight;
          if (nextWidth === currentWidth && nextHeight === currentHeight) {
            return;
          }
          hasResized = true;
          dispatchResize(item, nextWidth, nextHeight, { commit: false });
        };

        const finishResize = (endEvent, shouldCommit) => {
          endEvent.preventDefault();
          endEvent.stopPropagation();
          window.removeEventListener('pointermove', onPointerMove);
          window.removeEventListener('pointerup', onPointerUp);
          window.removeEventListener('pointercancel', onPointerCancel);
          if (handle.releasePointerCapture) {
            try {
              handle.releasePointerCapture(pointerId);
            } catch (err) {
              /* no-op */
            }
          }
          handle.classList.remove('is-resizing');
          item.draggable = wasDraggable;
          if (!hasResized) {
            return;
          }
          const width = parseInt(item.dataset.gsWidth || '1', 10) || startWidth;
          const height =
            parseInt(item.dataset.gsHeight || '1', 10) || startHeight;
          dispatchResize(item, width, height, { commit: shouldCommit });
        };

        const onPointerUp = (upEvent) => finishResize(upEvent, true);
        const onPointerCancel = (cancelEvent) => finishResize(cancelEvent, true);

        window.addEventListener('pointermove', onPointerMove);
        window.addEventListener('pointerup', onPointerUp);
        window.addEventListener('pointercancel', onPointerCancel);
      });

      handle.addEventListener('keydown', (event) => {
        const item = handle.closest('.grid-stack-item');
        if (!item) {
          return;
        }
        const key = event.key;
        if (!['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(key)) {
          return;
        }
        event.preventDefault();
        const columns = parseColumnCount(container);
        const deltaMap = {
          ArrowRight: { w: 1, h: 0 },
          ArrowLeft: { w: -1, h: 0 },
          ArrowDown: { w: 0, h: 1 },
          ArrowUp: { w: 0, h: -1 },
        };
        const delta = deltaMap[key];
        const currentWidth = parseInt(item.dataset.gsWidth || '1', 10) || 1;
        const currentHeight = parseInt(item.dataset.gsHeight || '1', 10) || 1;
        let nextWidth = currentWidth + delta.w;
        let nextHeight = currentHeight + delta.h;
        nextWidth = Math.max(1, Math.min(nextWidth, columns));
        nextHeight = Math.max(1, nextHeight);
        if (nextWidth === currentWidth && nextHeight === currentHeight) {
          return;
        }
        dispatchResize(item, nextWidth, nextHeight, { commit: true });
      });
    });
  }

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
      bindResizeHandles(container);
      toggleEmptyState(container);
      return;
    }

    bindResizeHandles(container);

    const schedule =
      typeof window.requestAnimationFrame === 'function'
        ? window.requestAnimationFrame.bind(window)
        : (callback) => setTimeout(callback, 0);
    let updatePending = false;

    const scheduleUpdate = () => {
      if (updatePending) {
        return;
      }
      updatePending = true;
      schedule(() => {
        updatePending = false;
        toggleEmptyState(container);
        postUpdate(container);
      });
    };

    grid.on('change', scheduleUpdate);
    grid.on('resizestop', scheduleUpdate);
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
