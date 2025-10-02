(function (window) {
  if (!window) {
    return;
  }

  const ns = window.v2TableFilters || (window.v2TableFilters = {});
  const IGNORED_FIELDS = new Set(["config_id", "filter_config_id"]);

  ns._filterKeys = ns._filterKeys || {};
  ns._exportTemplates = ns._exportTemplates || {};
  ns._activeConfigs = ns._activeConfigs || {};
  ns._htmxHandlers = ns._htmxHandlers || new Map();
  ns.tables = ns.tables || {};
  ns.handlesFilterFields = true;

  function parseFilterKeys(value) {
    if (Array.isArray(value)) {
      return value;
    }
    if (typeof value === "string" && value.length) {
      try {
        const parsed = JSON.parse(value);
        if (Array.isArray(parsed)) {
          return parsed;
        }
      } catch (err) {
        // ignore
      }
    }
    return [];
  }

  function createBaseParams(filterKeys) {
    const params = new URLSearchParams(window.location.search || "");
    (filterKeys || []).forEach((key) => {
      if (!key) {
        return;
      }
      params.delete(key);
      params.delete(`filters.${key}`);
    });
    return params;
  }

  function appendFormValues(params, form) {
    if (!form) {
      return;
    }
    const formData = new FormData(form);
    const seen = new Set();
    for (const [key, value] of formData.entries()) {
      if (IGNORED_FIELDS.has(key)) {
        continue;
      }
      if (!seen.has(key)) {
        params.delete(key);
        seen.add(key);
      }
      if (value === "") {
        continue;
      }
      params.append(key, value);
    }
  }

  function hasValue(value) {
    return value !== undefined && value !== null && String(value).trim() !== '';
  }

  function getFormByDomId(domId) {
    if (!domId) {
      return null;
    }
    return document.getElementById(`v2TableFilterForm-${domId}`);
  }

  function getSelectValues(select) {
    if (!select) {
      return [];
    }
    const ts = select.tomselect;
    if (ts && Array.isArray(ts.items)) {
      return ts.items.slice();
    }
    if (select.multiple) {
      return Array.from(select.options || [])
        .filter((option) => option.selected && hasValue(option.value))
        .map((option) => option.value);
    }
    const value = select.value;
    return hasValue(value) ? [value] : [];
  }

  function buildFilterParams(form, excludeName, queryValue) {
    const params = new URLSearchParams();
    if (!form) {
      if (typeof queryValue === 'string') {
        params.set('q', queryValue);
      }
      return params;
    }
    const formData = new FormData(form);
    const skip = new Set([excludeName, ...IGNORED_FIELDS]);
    for (const [key, value] of formData.entries()) {
      if (skip.has(key)) {
        continue;
      }
      if (value === '') {
        continue;
      }
      params.append(key, value);
    }
    const selects = form.querySelectorAll('select.filter-field-select');
    selects.forEach((sel) => {
      const nameAttr = sel.getAttribute('name') || '';
      if (!nameAttr || skip.has(nameAttr)) {
        return;
      }
      const values = getSelectValues(sel);
      values.forEach((val) => {
        if (hasValue(val)) {
          params.append(nameAttr, val);
        }
      });
    });
    if (typeof queryValue === 'string' && queryValue.length) {
      params.set('q', queryValue);
    } else if (!params.has('q')) {
      params.set('q', '');
    }
    return params;
  }

  function fetchOptionsForSelect(select, form, { query = '', selectedOnly = false } = {}) {
    const ajaxUrl = select && select.getAttribute ? select.getAttribute('data-ajax-url') : null;
    if (!ajaxUrl) {
      return Promise.resolve([]);
    }
    if (selectedOnly) {
      const values = getSelectValues(select);
      if (!values.length) {
        return Promise.resolve([]);
      }
      const url = `${ajaxUrl}?ids=${encodeURIComponent(values.join(','))}`;
      return fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then((response) => (response.ok ? response.json() : []))
        .then((payload) => (payload && payload.results ? payload.results : payload || []))
        .catch(() => []);
    }

    const params = buildFilterParams(form, select ? select.getAttribute('name') : null, query);
    const url = `${ajaxUrl}${params.toString() ? `?${params.toString()}` : ''}`;
    return fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then((response) => (response.ok ? response.json() : []))
      .then((payload) => (payload && payload.results ? payload.results : payload || []))
      .catch(() => []);
  }

  function applyOptionListToTomSelect(select, optionList) {
    if (!select || !select.tomselect) {
      return;
    }
    const ts = select.tomselect;
    const list = Array.isArray(optionList) ? optionList : [];
    const allowed = new Set(list.map((entry) => String(entry.value)));
    const selectedBefore = Array.isArray(ts.items) ? ts.items.slice() : [];

    ts.clearOptions();
    list.forEach((entry) => {
      try {
        ts.addOption(entry);
      } catch (err) {
        /* ignore duplicate option */
      }
    });
    ts.refreshOptions(false);

    let changed = false;
    selectedBefore.forEach((value) => {
      if (!allowed.has(String(value))) {
        try {
          ts.removeItem(value, true);
          changed = true;
        } catch (err) {
          /* ignore */
        }
      }
    });
    if (changed) {
      ts.refreshItems();
    }
    selectedBefore.forEach((value) => {
      if (allowed.has(String(value))) {
        try {
          if (!ts.items.includes(value)) {
            ts.addItem(value, true);
          }
        } catch (err) {
          /* ignore */
        }
      }
    });
  }

  function ensureTomSelect(select, form) {
    if (!select || !window.TomSelect) {
      return null;
    }
    if (select.tomselect) {
      return select.tomselect;
    }
    let options = {};
    try {
      const raw = select.getAttribute('data-tom-select-options');
      if (raw) {
        options = JSON.parse(raw);
      }
    } catch (err) {
      options = {};
    }
    const ajaxUrl = select.getAttribute('data-ajax-url');
    const minLenAttr = select.getAttribute('data-min-query-length');
    const minLen = Number.isFinite(Number(minLenAttr)) ? Number(minLenAttr) : 0;

    const ts = new TomSelect(select, Object.assign({
      valueField: 'value',
      labelField: 'label',
      searchField: 'label',
      persist: false,
      closeAfterSelect: true,
      preload: ajaxUrl ? 'focus' : null,
      openOnFocus: true,
      load(query, callback) {
        if (!ajaxUrl) {
          callback();
          return;
        }
        const search = (query || '').trim();
        if (minLen > 0 && search.length < minLen) {
          callback();
          return;
        }
        fetchOptionsForSelect(select, form, { query: search })
          .then((items) => callback(items || []))
          .catch(() => callback());
      },
    }, options));

    if (ajaxUrl) {
      fetchOptionsForSelect(select, form, { selectedOnly: true })
        .then((items) => applyOptionListToTomSelect(select, items))
        .catch(() => {});
    }

    ts.on('change', () => {
      refreshDependentSelects(form, select);
    });
    ts.on('clear', () => {
      refreshDependentSelects(form, select);
    });
    ts.on('item_remove', () => {
      refreshDependentSelects(form, select);
    });

    return ts;
  }

  function refreshDependentSelects(form, changedSelect) {
    if (!form) {
      return;
    }
    const selects = form.querySelectorAll('select.filter-field-select');
    selects.forEach((sel) => {
      if (sel === changedSelect) {
        return;
      }
      if (!sel || !sel.getAttribute('data-ajax-url')) {
        return;
      }
      fetchOptionsForSelect(sel, form)
        .then((items) => applyOptionListToTomSelect(sel, items))
        .catch(() => {});
    });
  }

  function bootstrapFilterForm(domId, form) {
    if (!form) {
      form = getFormByDomId(domId);
    }
    if (!form) {
      return;
    }
    if (form.dataset.v2FiltersBootstrapped === '1') {
      return;
    }
    form.dataset.v2FiltersBootstrapped = '1';
    const selects = form.querySelectorAll('select.filter-field-select');
    selects.forEach((select) => {
      ensureTomSelect(select, form);
      if (!select._v2FilterChangeBound) {
        select.addEventListener('change', function () {
          refreshDependentSelects(form, select);
        });
        select._v2FilterChangeBound = true;
      }
    });
  }

  function getFilterKeys(domId) {
    return ns._filterKeys[domId] || [];
  }

  ns.submitFilters = function submitFilters(domId) {
    const form = document.getElementById(`v2TableFilterForm-${domId}`);
    if (!form) {
      return false;
    }
    const filterKeys = getFilterKeys(domId);
    const params = createBaseParams(filterKeys);

    const cfgInput = form.querySelector('input[name="config_id"]');
    const cfgVal = cfgInput && cfgInput.value ? cfgInput.value.trim() : "";
    if (hasValue(cfgVal)) {
      params.set("config_id", cfgVal);
      ns._activeConfigs[domId] = cfgVal;
    } else {
      params.delete("config_id");
      delete ns._activeConfigs[domId];
    }

    const filterCfgInput = form.querySelector('input[name="filter_config_id"]');
    const filterCfgVal = filterCfgInput && filterCfgInput.value ? filterCfgInput.value.trim() : "";
    if (hasValue(filterCfgVal)) {
      params.set("filter_config_id", filterCfgVal);
    } else {
      params.delete("filter_config_id");
    }

    appendFormValues(params, form);

    const dest = window.location.pathname + (params.toString() ? `?${params.toString()}` : "");
    window.location.assign(dest);
    return false;
  };

  ns.bootstrapFilterForm = function bootstrapFilterFormPublic(domId, form) {
    bootstrapFilterForm(domId, form || null);
  };

  ns.changeSavedFilter = function changeSavedFilter(domId) {
    const select = document.getElementById(`filterCfgSelect-${domId}`);
    if (!select) {
      return false;
    }
    const filterKeys = getFilterKeys(domId);
    const params = createBaseParams(filterKeys);
    if (hasValue(select.value)) {
      params.set("filter_config_id", select.value);
    } else {
      params.delete("filter_config_id");
    }

    const form = document.getElementById(`v2TableFilterForm-${domId}`);
    if (form) {
      const hidden = form.querySelector('input[name="filter_config_id"]');
      if (hidden) {
        hidden.value = select.value || "";
      }
    }

    const dest = window.location.pathname + (params.toString() ? `?${params.toString()}` : "");
    window.location.assign(dest);
    return false;
  };

  ns.buildAjaxUrl = function buildAjaxUrl(config) {
    const domId = config && config.domId;
    if (!domId) {
      return config && config.url ? config.url : "";
    }
    const filterKeys = getFilterKeys(domId);
    const params = createBaseParams(filterKeys);
    const size = (config && config.params && config.params.size) || (config && config.tableOptions && config.tableOptions.paginationSize) || 10;
    const page = (config && config.params && config.params.page) || 1;
    params.set("page", page);
    params.set("size", size);

    if (config && Array.isArray(config.params && config.params.sorters) && config.params.sorters.length) {
      const sorter = config.params.sorters[0];
      if (sorter && sorter.field) {
        params.set("sort", sorter.field);
        params.set("dir", sorter.dir || "asc");
      }
    } else {
      params.delete("sort");
      params.delete("dir");
    }

    const form = document.getElementById(`v2TableFilterForm-${domId}`);
    appendFormValues(params, form);

    const select = document.getElementById(`filterCfgSelect-${domId}`);
    if (select && hasValue(select.value)) {
      params.set("filter_config_id", select.value);
    }

    const cfgInput = form ? form.querySelector('input[name="config_id"]') : null;
    const cfgVal = cfgInput && cfgInput.value ? cfgInput.value.trim() : "";
    if (hasValue(cfgVal)) {
      params.set("config_id", cfgVal);
    }

    const query = params.toString();
    return (config && config.url ? config.url : "") + (query ? `?${query}` : "");
  };

  ns.exportServer = function exportServer(options) {
    const domId = options && options.domId;
    if (!domId) {
      return false;
    }
    const template = ns._exportTemplates[domId];
    if (!template) {
      return false;
    }
    const filterKeys = getFilterKeys(domId);
    const params = createBaseParams(filterKeys);

    const activeCfg = ns._activeConfigs[domId];
    if (hasValue(activeCfg)) {
      params.set("config_id", activeCfg);
    }

    const select = document.getElementById(`filterCfgSelect-${domId}`);
    if (select && hasValue(select.value)) {
      params.set("filter_config_id", select.value);
    }

    const form = document.getElementById(`v2TableFilterForm-${domId}`);
    appendFormValues(params, form);

    const format = (options && options.format) || "csv";
    const base = template.replace(/csv(?=[^/]*$)/, format);
    const query = params.toString();
    window.location.href = base + (query ? `?${query}` : "");
    return false;
  };

  ns.init = function init(config) {
    if (!config || !config.domId) {
      return;
    }
    const domId = config.domId;
    ns._filterKeys[domId] = parseFilterKeys(config.filterKeys);

    if (hasValue(config.activeTableConfigId)) {
      ns._activeConfigs[domId] = config.activeTableConfigId;
    } else {
      delete ns._activeConfigs[domId];
    }

    if (config.exportUrlTemplate) {
      ns._exportTemplates[domId] = config.exportUrlTemplate;
    }

    const form = document.getElementById(`v2TableFilterForm-${domId}`);
    if (form) {
      form.addEventListener("submit", function onSubmit(ev) {
        ev.preventDefault();
        ns.submitFilters(domId);
      });
      const cfgInput = form.querySelector('input[name="config_id"]');
      if (cfgInput && hasValue(cfgInput.value)) {
        ns._activeConfigs[domId] = cfgInput.value;
      }
      bootstrapFilterForm(domId, form);
    } else {
      bootstrapFilterForm(domId, null);
    }

    const filterSelect = document.getElementById(`filterCfgSelect-${domId}`);
    if (filterSelect) {
      filterSelect.addEventListener("change", function onChange(ev) {
        ev.preventDefault();
        ns.changeSavedFilter(domId);
      });
      if (form) {
        const hidden = form.querySelector('input[name="filter_config_id"]');
        if (hidden) {
          hidden.value = filterSelect.value || "";
        }
      }
    }

    if (config.wrapperId) {
      const wrapperId = config.wrapperId;
      const wrapper = document.getElementById(wrapperId);
      if (wrapper) {
        wrapper.querySelectorAll("[data-v2-export]").forEach(function attach(link) {
          link.addEventListener("click", function onExport(ev) {
            ev.preventDefault();
            ns.exportServer({ domId, format: link.dataset.format });
          });
        });
      }
      if (!ns._htmxHandlers.has(wrapperId)) {
        const handler = function handleHtmxError() {
          try {
            const card = document.getElementById(wrapperId);
            if (!card) {
              return;
            }
            const body = card.querySelector(".card-body");
            if (!body) {
              return;
            }
            const note = document.createElement("div");
            note.className = "alert alert-danger mt-2";
            note.textContent = "Error refreshing block.";
            body.prepend(note);
            window.setTimeout(function remove() {
              try {
                note.remove();
              } catch (err) {
                // ignore
              }
            }, 3000);
          } catch (err) {
            // ignore
          }
        };
        document.addEventListener("htmx:responseError", handler);
        ns._htmxHandlers.set(wrapperId, handler);
      }
    }

    if (window.Tabulator && config.tableElementId) {
      const tableEl = document.getElementById(config.tableElementId);
      if (tableEl) {
        const sourceColumns = Array.isArray(config.columns) ? config.columns : [];
        const tabColumns = sourceColumns.map(function mapColumns(col) {
          return {
            title: col.label || col.key || "",
            field: col.key,
            headerFilter: true,
          };
        });

        const defaultOptions = {
          columns: tabColumns,
          layout: "fitColumns",
          placeholder: "No data",
          ajaxURL: config.dataUrl,
          ajaxURLGenerator: function ajaxURLGenerator(url, requestConfig, params) {
            return ns.buildAjaxUrl({
              url,
              params,
              domId,
              tableOptions: config.tableOptions || {},
            });
          },
        };

        if (Array.isArray(config.rows) && config.rows.length && !defaultOptions.ajaxURL) {
          defaultOptions.data = config.rows;
        }

        const options = Object.assign({}, defaultOptions, config.tableOptions || {});

        if (Array.isArray(config.rows) && config.rows.length) {
          options.data = config.rows;
        }

        const table = new Tabulator(tableEl, options);
        ns.tables[domId] = table;
        window[domId] = table;
      }
    }
  };

  ns.teardown = function teardown(wrapperId) {
    if (!wrapperId) {
      return;
    }
    if (ns._htmxHandlers.has(wrapperId)) {
      const handler = ns._htmxHandlers.get(wrapperId);
      document.removeEventListener("htmx:responseError", handler);
      ns._htmxHandlers.delete(wrapperId);
    }
  };
})(window);

