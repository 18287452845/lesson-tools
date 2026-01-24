(function () {
  var PLUGIN_GUID = "asc.{F6C9D643-1F6B-4C1F-9B0C-9AD04E4B596E}";
  var state = {
    apiBaseUrl: "",
    templateId: "",
    fields: [],
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function setStatus(message, level) {
    var el = byId("status");
    if (!el) {
      return;
    }
    el.textContent = message || "";
    el.className = "plugin__status";
    if (level) {
      el.className += " plugin__status--" + level;
    }
  }

  function normalizeBaseUrl(url) {
    return (url || "").replace(/\/+$/, "");
  }

  function getOptions() {
    var info = window.Asc && window.Asc.plugin && window.Asc.plugin.info;
    var options = (info && info.options) || {};
    var merged = {};
    var all = options.all || {};
    var specific = options[PLUGIN_GUID] || {};

    Object.keys(all).forEach(function (key) {
      merged[key] = all[key];
    });
    Object.keys(specific).forEach(function (key) {
      merged[key] = specific[key];
    });

    return merged;
  }

  function fetchJson(url) {
    return fetch(url, { credentials: "omit" }).then(function (response) {
      if (!response.ok) {
        throw new Error("Request failed: " + response.status);
      }
      return response.json();
    });
  }

  function renderSelect(fields) {
    var select = byId("fieldSelect");
    if (!select) {
      return;
    }
    select.innerHTML = "";
    fields.forEach(function (field) {
      var option = document.createElement("option");
      option.value = field.name;
      option.textContent = field.display_name + " (" + field.name + ")";
      select.appendChild(option);
    });
  }

  function getSelectedFieldName() {
    var select = byId("fieldSelect");
    if (!select) {
      return "";
    }
    return select.value || "";
  }

  function buildPlaceholder(name) {
    return "{{ " + name + " }}";
  }

  function isPlaceholder(text) {
    return /^\{\{\s*[^{}]+\s*\}\}$/.test(text || "");
  }

  function loadFields() {
    var options = getOptions();
    state.templateId = options.templateId || "";
    state.apiBaseUrl = normalizeBaseUrl(options.apiBaseUrl || "");

    if (!state.templateId || !state.apiBaseUrl) {
      setStatus("Missing plugin options. Check OnlyOffice config.", "error");
      return Promise.reject(new Error("Missing plugin options"));
    }

    var templateUrl =
      state.apiBaseUrl +
      "/templates/" +
      encodeURIComponent(state.templateId) +
      "/fields";
    var standardUrl = state.apiBaseUrl + "/templates/standard-fields";

    setStatus("Loading fields...", "warn");

    return Promise.all([fetchJson(templateUrl), fetchJson(standardUrl)])
      .then(function (responses) {
        var templateFields = (responses[0] && responses[0].fields) || [];
        var standardFields = (responses[1] && responses[1].fields) || [];
        var byName = {};
        var merged = [];

        function addField(field) {
          if (!field || !field.name || byName[field.name]) {
            return;
          }
          byName[field.name] = true;
          merged.push({
            name: field.name,
            display_name: field.display_name || field.display || field.name,
          });
        }

        templateFields.forEach(addField);
        standardFields.forEach(addField);

        merged.sort(function (a, b) {
          return (a.display_name || "").localeCompare(b.display_name || "");
        });

        state.fields = merged;
        renderSelect(merged);

        setStatus("Fields loaded: " + merged.length, "ok");

        return merged;
      })
      .catch(function (error) {
        setStatus("Failed to load fields.", "error");
        throw error;
      });
  }

  function replaceSelected() {
    var name = getSelectedFieldName();
    if (!name) {
      setStatus("Select a field first.", "warn");
      return;
    }
    var placeholder = buildPlaceholder(name);

    window.Asc.plugin.executeMethod(
      "GetSelectedText",
      [
        {
          Numbering: false,
          Math: false,
          TableCellSeparator: "\t",
          TableRowSeparator: "\r\n",
          ParaSeparator: "\r\n",
          TabSymbol: "\t",
          NewLineSeparator: "\r",
        },
      ],
      function (selectedText) {
        var selection = (selectedText || "").trim();
        if (!selection) {
          setStatus("No selection. Select a placeholder.", "warn");
          return;
        }
        if (!isPlaceholder(selection)) {
          setStatus("Selection is not a placeholder.", "warn");
          return;
        }
        window.Asc.plugin.executeMethod("PasteText", [placeholder], function () {
          setStatus("Placeholder replaced.", "ok");
        });
      }
    );
  }

  function insertField() {
    var name = getSelectedFieldName();
    if (!name) {
      setStatus("Select a field first.", "warn");
      return;
    }
    var placeholder = buildPlaceholder(name);

    window.Asc.plugin.executeMethod("PasteText", [placeholder], function () {
      setStatus("Field inserted.", "ok");
    });
  }

  function bindUi() {
    var replaceBtn = byId("replaceBtn");
    var insertBtn = byId("insertBtn");

    if (replaceBtn) {
      replaceBtn.addEventListener("click", replaceSelected);
    }
    if (insertBtn) {
      insertBtn.addEventListener("click", insertField);
    }
  }

  window.Asc.plugin.init = function () {
    bindUi();

    loadFields().catch(function () {
      // status already set
    });
  };
})();
