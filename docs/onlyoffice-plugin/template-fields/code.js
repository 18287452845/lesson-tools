(function () {
  var PLUGIN_GUID = "asc.{F6C9D643-1F6B-4C1F-9B0C-9AD04E4B596E}";
  var state = {
    apiBaseUrl: "",
    templateId: "",
    fields: [],
    placeholders: [],
    highlightEnabled: true,
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

  function buildPlaceholderVariants(fieldName) {
    return [
      "{{" + fieldName + "}}",
      "{{ " + fieldName + "}}",
      "{{" + fieldName + " }}",
      "{{ " + fieldName + " }}",
    ];
  }

  function buildPlaceholders(fields) {
    var set = {};
    fields.forEach(function (field) {
      if (!field || !field.name) {
        return;
      }
      var variants = buildPlaceholderVariants(field.name);
      variants.forEach(function (variant) {
        set[variant] = true;
      });
    });
    return Object.keys(set);
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

  function applyHighlights() {
    if (!state.highlightEnabled || !state.placeholders.length) {
      return;
    }
    window.Asc.plugin.callCommand(
      function () {
        var doc = Api.GetDocument();
        var placeholders = window.Asc.plugin.info.data || [];
        for (var i = 0; i < placeholders.length; i += 1) {
          var ranges = doc.Search(placeholders[i], false);
          for (var j = 0; j < ranges.length; j += 1) {
            ranges[j].SetHighlight("yellow");
          }
        }
      },
      false,
      state.placeholders
    );
  }

  function clearHighlights() {
    if (!state.placeholders.length) {
      return;
    }
    window.Asc.plugin.callCommand(
      function () {
        var doc = Api.GetDocument();
        var placeholders = window.Asc.plugin.info.data || [];
        for (var i = 0; i < placeholders.length; i += 1) {
          var ranges = doc.Search(placeholders[i], false);
          for (var j = 0; j < ranges.length; j += 1) {
            ranges[j].SetHighlight("none");
          }
        }
      },
      false,
      state.placeholders
    );
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
        state.placeholders = buildPlaceholders(merged);
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
          if (state.highlightEnabled) {
            applyHighlights();
          }
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
      if (state.highlightEnabled) {
        applyHighlights();
      }
    });
  }

  function bindUi() {
    var replaceBtn = byId("replaceBtn");
    var insertBtn = byId("insertBtn");
    var refreshBtn = byId("refreshBtn");
    var clearBtn = byId("clearBtn");
    var highlightToggle = byId("highlightToggle");

    if (replaceBtn) {
      replaceBtn.addEventListener("click", replaceSelected);
    }
    if (insertBtn) {
      insertBtn.addEventListener("click", insertField);
    }
    if (refreshBtn) {
      refreshBtn.addEventListener("click", function () {
        if (state.highlightEnabled) {
          applyHighlights();
          setStatus("Highlights refreshed.", "ok");
        }
      });
    }
    if (clearBtn) {
      clearBtn.addEventListener("click", function () {
        clearHighlights();
        setStatus("Highlights cleared.", "ok");
      });
    }
    if (highlightToggle) {
      highlightToggle.addEventListener("change", function (event) {
        state.highlightEnabled = event.target.checked;
        if (state.highlightEnabled) {
          applyHighlights();
          setStatus("Highlight enabled.", "ok");
        } else {
          clearHighlights();
          setStatus("Highlight disabled.", "warn");
        }
      });
    }
  }

  function attachEditorEvents() {
    if (window.Asc && window.Asc.plugin && window.Asc.plugin.attachEditorEvent) {
      window.Asc.plugin.attachEditorEvent("onDocumentStateChange", function () {
        if (!state.highlightEnabled) {
          return;
        }
        applyHighlights();
      });
    } else if (window.Asc && window.Asc.plugin && window.Asc.plugin.attachEvent) {
      window.Asc.plugin.attachEvent("onDocumentStateChange", function () {
        if (!state.highlightEnabled) {
          return;
        }
        applyHighlights();
      });
    }
  }

  window.Asc.plugin.init = function () {
    bindUi();
    attachEditorEvents();

    loadFields()
      .then(function () {
        if (state.highlightEnabled) {
          applyHighlights();
        }
      })
      .catch(function () {
        // status already set
      });
  };

  window.Asc.plugin.onClose = function () {
    if (state.highlightEnabled) {
      clearHighlights();
    }
  };
})();
