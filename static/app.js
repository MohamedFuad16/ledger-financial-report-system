/* ============================================================
   Financial Report System — Client-Side Application
   ============================================================ */

// ---- Global State ----
let currentPanel = 'dashboard';
let selectedFile = null;
let selectedFiles = [];
let lastResult = null;
let bestStats = { accuracy: 0, bestAccRun: '', coverage: 0, bestCovRun: '' };
let hasApiKey = false;
let allRuns = [];
let s1RunsExpanded = false;
let s1RunsToggledByUser = false;
let s2RunsExpanded = false;
let s2RunsToggledByUser = false;
let promptEditorExpanded = false;
let activeRun = false;

// ---- Golden answers -------------------------------------------------------
// The golden answers live in schema.py and are served by /api/golden_answers.
// They are deliberately NOT duplicated here: two copies drift, and a drifted
// copy silently changes every accuracy number in the UI.
let GOLDEN_ANSWERS_STORE = {};

function loadGoldenAnswers() {
  return fetch('/api/golden_answers')
    .then(r => r.json())
    .then(store => {
      GOLDEN_ANSWERS_STORE = store || {};
      return GOLDEN_ANSWERS_STORE;
    })
    .catch(() => {
      showToast('Could not load golden answers; accuracy will not be scored.', 'error');
      return GOLDEN_ANSWERS_STORE;
    });
}

// Returns {} for a year we have no answer key for. Never falls back to another
// year: comparing an FY2025 report against FY2022 answers would report a
// meaningless accuracy as if it were real.
function getGoldenAnswers(fiscalYear) {
  const yr = String(fiscalYear || '').trim();
  return GOLDEN_ANSWERS_STORE[yr] || {};
}

function hasGoldenAnswers(fiscalYear) {
  return Object.keys(getGoldenAnswers(fiscalYear)).length > 0;
}

// ---- DOM Ready ----
document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initUploadZone();
  initS2UI();
  initS2ExtractorPicker();
  initSettingsUI();
  initPromptEditor();
  initEvidenceToggle();
  initDownloads();

  loadSettings();
  loadGoldenAnswers().then(() => {
    loadSchema();
    loadRunHistory(true).then(applyHashRoute);
  });

  window.addEventListener('hashchange', applyHashRoute);
});

// Deep-link to a panel: /#strategy2, /#schema, /#history …
const PANELS = ['dashboard', 'strategy1', 'strategy2', 'strategy3', 'strategy4', 'history', 'schema', 'settings'];

function applyHashRoute() {
  const name = (location.hash || '').replace('#', '');
  if (name && PANELS.includes(name) && name !== currentPanel) switchPanel(name);
}

// ============================================================
//  NAVIGATION (Multi-Strategy Routing)
// ============================================================
function initNavigation() {
  document.querySelectorAll('.sidebar-nav-item[data-panel]').forEach(btn => {
    btn.addEventListener('click', () => {
      switchPanel(btn.dataset.panel);
    });
  });
}

function switchPanel(name) {
  document.querySelectorAll('.sidebar-nav-item').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));

  const btn = document.querySelector(`.sidebar-nav-item[data-panel="${name}"]`);
  const panel = document.getElementById(`panel-${name}`);
  if (btn) btn.classList.add('active');
  if (panel) panel.classList.add('active');

  currentPanel = name;
  if (location.hash.replace('#', '') !== name) {
    history.replaceState(null, '', `#${name}`);
  }

  if (name === 'history') loadRunHistory(false);
  if (name === 'settings') loadSettings();
  if (name === 'schema') loadSchema();
  if (name === 'strategy1') {
    renderS1RunsList();
    loadPrompt();
  }
  if (name === 'dashboard') {
    if (lastResult && lastResult.rows) {
      setTimeout(() => {
        const fy = lastResult.detected_fiscal_year || lastResult.fiscal_year || '';
        renderDashboardCharts();
      }, 60);
    } else if (allRuns.length === 0) {
      resetDashboardToEmptyState();
    }
  }
}

// Runs have carried the strategy as 1/2, 's1'/'s2' or only as a run-id prefix
// across versions of this app; resolve all of them the same way.
function runStrategy(run) {
  if (!run) return 's1';
  const raw = String(run.strategy ?? '');
  // Every s2-* parser variant belongs to Strategy 2; only the exact key
  // identifies which parser, which is what parserChip() shows separately.
  if (raw === '2' || raw === 's2' || raw.startsWith('s2-')) return 's2';
  if (raw === '1' || raw === 's1') return 's1';
  if (raw === 's3' || raw === 's4') return raw;
  return String(run.run_id || '').startsWith('S2') ? 's2' : 's1';
}

// ============================================================
//  TOAST NOTIFICATIONS (Clean, Minimal, No colored strips)
// ============================================================
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  let icon;
  if (type === 'success') {
    icon = '<svg viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:16px;height:16px;"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>';
  } else if (type === 'error') {
    icon = '<svg viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:16px;height:16px;"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>';
  } else {
    icon = '<svg viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:16px;height:16px;"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>';
  }

  toast.innerHTML = `<span class="toast-icon">${icon}</span><span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('leaving');
    toast.addEventListener('animationend', () => toast.remove());
  }, 4000);
}

function escapeHtml(text) {
  if (text === null || text === undefined) return '';
  const div = document.createElement('div');
  div.textContent = String(text);
  return div.innerHTML;
}

// ============================================================
//  SETTINGS & API CONNECTION
// ============================================================
function initSettingsUI() {
  const providerSel = document.getElementById('input-provider');
  if (providerSel) providerSel.addEventListener('change', () => applyProviderChoice());

  const btnSave = document.getElementById('btn-test-save');
  if (btnSave) btnSave.addEventListener('click', saveSettings);

  const btnReconfig = document.getElementById('btn-reconfigure');
  if (btnReconfig) {
    btnReconfig.addEventListener('click', () => showSettingsEditView(true));
  }

  const btnCancel = document.getElementById('btn-cancel-edit');
  if (btnCancel) {
    btnCancel.addEventListener('click', () => {
      if (hasApiKey) showSettingsSavedView();
    });
  }

  // Slider live value badges
  const settingsTempSlider = document.getElementById('input-settings-temp');
  const settingsTempBadge = document.getElementById('settings-temp-badge');
  if (settingsTempSlider && settingsTempBadge) {
    settingsTempSlider.addEventListener('input', (e) => {
      settingsTempBadge.textContent = parseFloat(e.target.value).toFixed(2);
    });
  }

  const s1TempSlider = document.getElementById('input-s1-temp');
  const s1TempBadge = document.getElementById('s1-temp-badge');
  if (s1TempSlider && s1TempBadge) {
    s1TempSlider.addEventListener('input', (e) => {
      s1TempBadge.textContent = parseFloat(e.target.value).toFixed(2);
    });
  }

  const s1ConcSlider = document.getElementById('input-batch-concurrency');
  const s1ConcBadge = document.getElementById('batch-concurrency-badge');
  if (s1ConcSlider && s1ConcBadge) {
    s1ConcSlider.addEventListener('input', (e) => {
      s1ConcBadge.textContent = e.target.value;
    });
  }
}



// ---- Provider catalogue ----------------------------------------------------
let PROVIDER_CATALOGUE = { providers: [], reasoning_efforts: [] };

function providerByKey(key) {
  return PROVIDER_CATALOGUE.providers.find(p => p.key === key) || null;
}

function loadProviders() {
  return fetch('/api/providers')
    .then(r => r.json())
    .then(data => { PROVIDER_CATALOGUE = data; renderProviderOptions(); return data; })
    .catch(() => showToast('Could not load the provider list.', 'error'));
}

function renderProviderOptions() {
  const sel = document.getElementById('input-provider');
  if (sel && !sel.options.length) {
    sel.innerHTML = PROVIDER_CATALOGUE.providers
      .map(p => `<option value="${escapeHtml(p.key)}">${escapeHtml(p.label)}</option>`).join('');
  }
  const effort = document.getElementById('input-settings-reasoning');
  if (effort && !effort.options.length) {
    // "none" is presented as Off; the rest are the provider-neutral effort scale.
    effort.innerHTML = (PROVIDER_CATALOGUE.reasoning_efforts || []).map(e =>
      `<option value="${e}">${e === 'none' ? 'Off — no reasoning' : e.charAt(0).toUpperCase() + e.slice(1)}</option>`
    ).join('');
  }
}

// Provider choice drives base URL, model suggestions and the caching note.
function applyProviderChoice({ keepModel = false } = {}) {
  const sel = document.getElementById('input-provider');
  if (!sel) return;
  const provider = providerByKey(sel.value);
  if (!provider) return;

  const urlEl = document.getElementById('input-custom-url');
  if (urlEl && (!keepModel || !urlEl.value.trim())) urlEl.value = provider.base_url || '';

  const modelEl = document.getElementById('input-model');
  if (modelEl && (!keepModel || !modelEl.value.trim())) modelEl.value = provider.default_model || '';

  const list = document.getElementById('model-suggestions');
  if (list) {
    list.innerHTML = (provider.suggested_models || [])
      .map(m => `<option value="${escapeHtml(m)}"></option>`).join('');
  }

  const hint = document.getElementById('provider-hint');
  if (hint) {
    hint.textContent = provider.reasoning_style === 'thinking'
      ? 'Reasoning is on/off only on this provider; graded effort levels collapse to on.'
      : 'Supports graded reasoning effort.';
  }

  const banner = document.getElementById('cache-banner');
  const text = document.getElementById('cache-banner-text');
  if (banner && text) {
    banner.style.display = 'flex';
    text.textContent = provider.automatic_prompt_caching
      ? 'Prompt caching is automatic here. The system prompt and the 27-row schema are '
        + 'sent as a fixed prefix (~2,660 tokens) so they hit the cache on repeat runs.'
      : 'This provider does not report prompt caching; only the document text varies per run.';
  }
}

function loadSettings() {
  return loadProviders()
    .then(() => fetch('/api/settings'))
    .then(r => r.json())
    .then(data => {
      hasApiKey = Boolean(data.has_key);

      const setText = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
      setText('saved-key-val', data.api_key_masked || 'Not configured');
      setText('saved-model-val', data.model || '—');
      setText('saved-endpoint-val', data.base_url || '—');
      const reasoningEl = document.getElementById('saved-reasoning-val');
      if (reasoningEl) {
        const off = data.reasoning_effort === 'none';
        reasoningEl.textContent = off ? 'Off' : `${data.reasoning_effort} effort`;
        reasoningEl.style.color = off ? '#6b7280' : '#2563eb';
      }
      const tempVal = data.temperature !== undefined ? parseFloat(data.temperature) : 0.1;
      setText('saved-temp-val', tempVal.toFixed(2));

      const sel = document.getElementById('input-provider');
      if (sel && data.provider) sel.value = data.provider;
      const modelEl = document.getElementById('input-model');
      if (modelEl) modelEl.value = data.model || '';
      const urlEl = document.getElementById('input-custom-url');
      if (urlEl) urlEl.value = data.base_url || '';
      const effortEl = document.getElementById('input-settings-reasoning');
      if (effortEl && data.reasoning_effort) effortEl.value = data.reasoning_effort;
      const tempEl = document.getElementById('input-settings-temp');
      if (tempEl) tempEl.value = tempVal;
      const tempBadge = document.getElementById('settings-temp-badge');
      if (tempBadge) tempBadge.textContent = tempVal.toFixed(2);

      applyProviderChoice({ keepModel: true });
      hasApiKey ? showSettingsSavedView() : showSettingsEditView(false);
      ['s1', 's2'].forEach(updateExtractButton);
    })
    .catch(() => showToast('Could not load settings.', 'error'));
}

function saveSettings() {
  const val = id => { const el = document.getElementById(id); return el ? el.value.trim() : ''; };
  const btn = document.getElementById('btn-test-save');
  const payload = {
    provider: val('input-provider'),
    api_key: val('input-api-key'),
    model: val('input-model'),
    base_url: val('input-custom-url'),
    reasoning_effort: val('input-settings-reasoning'),
    temperature: parseFloat(val('input-settings-temp') || '0.1')
  };
  if (!payload.api_key) { showToast('Enter an API key first.', 'error'); return; }

  const original = btn ? btn.innerHTML : '';
  if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Testing connection…'; }

  fetch('/api/settings', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
  })
    .then(r => r.json().then(d => ({ ok: r.ok, d })))
    .then(({ ok, d }) => {
      if (!ok || d.error) throw new Error(d.error || 'Connection test failed');
      showToast(`Connected to ${d.model} in ${Number(d.elapsed || 0).toFixed(2)}s. Saved.`, 'success');
      return loadSettings();
    })
    .catch(err => showToast(err.message, 'error'))
    .finally(() => { if (btn) { btn.disabled = false; btn.innerHTML = original; } });
}

function showSettingsSavedView() {
  const savedView = document.getElementById('settings-saved-view');
  const editView = document.getElementById('settings-edit-view');
  if (savedView) savedView.style.display = 'block';
  if (editView) editView.style.display = 'none';
}

function showSettingsEditView(showCancel) {
  const savedView = document.getElementById('settings-saved-view');
  const editView = document.getElementById('settings-edit-view');
  const btnCancel = document.getElementById('btn-cancel-edit');
  if (savedView) savedView.style.display = 'none';
  if (editView) editView.style.display = 'block';
  if (btnCancel) btnCancel.style.display = showCancel ? 'inline-flex' : 'none';
}





// ============================================================
//  SYSTEM PROMPT EDITOR (Strategy 1)
// ============================================================
function initPromptEditor() {
  const btnSave = document.getElementById('btn-save-prompt');
  const btnReset = document.getElementById('btn-reset-prompt');

  if (btnSave) {
    btnSave.addEventListener('click', savePrompt);
  }
  if (btnReset) {
    btnReset.addEventListener('click', resetPrompt);
  }
}

function togglePromptEditor() {
  promptEditorExpanded = !promptEditorExpanded;
  const bodyEl = document.getElementById('prompt-editor-body');
  const textEl = document.getElementById('prompt-toggle-text');
  if (bodyEl) bodyEl.style.display = promptEditorExpanded ? 'block' : 'none';
  if (textEl) textEl.textContent = promptEditorExpanded ? 'Hide Prompt' : 'View / Edit Prompt';
  if (promptEditorExpanded) loadPrompt();
}

function loadPrompt() {
  fetch('/api/prompt')
    .then(r => r.json())
    .then(data => {
      const textarea = document.getElementById('input-system-prompt');
      if (textarea) textarea.value = data.system_prompt || data.default_prompt || '';
    })
    .catch(() => {});
}

function savePrompt() {
  const textarea = document.getElementById('input-system-prompt');
  const newPrompt = textarea.value.trim();
  if (!newPrompt) {
    showToast('Prompt cannot be empty.', 'error');
    return;
  }

  fetch('/api/prompt', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ system_prompt: newPrompt })
  })
    .then(r => r.json())
    .then(data => {
      if (data.ok) {
        showToast('System prompt saved successfully.', 'success');
      } else {
        showToast(data.error || 'Failed to save prompt.', 'error');
      }
    })
    .catch(err => {
      showToast(`Error saving prompt: ${err.message}`, 'error');
    });
}

function resetPrompt() {
  fetch('/api/prompt')
    .then(r => r.json())
    .then(data => {
      if (data.default_prompt) {
        const textarea = document.getElementById('input-system-prompt');
        if (textarea) textarea.value = data.default_prompt;
        savePrompt();
      }
    });
}

// ============================================================
//  UPLOAD ZONE & PIPELINE (Strategy 1)
// ============================================================
function initUploadZone() {
  const zone = document.getElementById('upload-zone');
  const input = document.getElementById('pdf-input');
  if (!zone || !input) return;

  zone.addEventListener('dragover', (e) => {
    e.preventDefault();
    zone.classList.add('drag-over');
  });

  zone.addEventListener('dragleave', () => {
    zone.classList.remove('drag-over');
  });

  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFilesSelected(Array.from(files), 's1');
    } else {
      showToast('Please drop PDF files.', 'error');
    }
  });

  input.addEventListener('change', () => {
    if (input.files.length > 0) {
      handleFilesSelected(Array.from(input.files), 's1');
    }
  });

  const btnExtract = document.getElementById('btn-run-extract');
  if (btnExtract) btnExtract.addEventListener('click', () => startRun('s1'));

  const btnBatch = document.getElementById('btn-run-batch');
  if (btnBatch) btnBatch.addEventListener('click', () => startRun('s1'));
}

function handleFilesSelected(files, strategy = 's1') {
  const validFiles = files.filter(f => f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf'));
  if (validFiles.length === 0) {
    showToast('No valid PDF files selected.', 'error');
    return;
  }
  
  selectedFiles = validFiles;
  selectedFile = validFiles[0]; // backward compatibility
  
  const isS2 = strategy === 's2';
  const prefix = isS2 ? 's2-' : '';
  const zone = document.getElementById(prefix + 'upload-zone');
  
  if (zone) {
    zone.classList.add('has-file');
    document.getElementById(prefix + 'upload-title').textContent = validFiles.length === 1 ? validFiles[0].name : `${validFiles.length} files selected`;
    const totalSize = validFiles.reduce((acc, f) => acc + f.size, 0);
    document.getElementById(prefix + 'upload-subtitle').textContent =
      `${(totalSize / 1024 / 1024).toFixed(2)} MB total · Click to replace`;
  }
  
  const batchControls = document.getElementById(isS2 ? 's2-batch-controls' : 'batch-controls');
  const btnExtract = document.getElementById(isS2 ? 'btn-run-extract-s2' : 'btn-run-extract');
  const btnBatch = document.getElementById(isS2 ? 'btn-run-batch-s2' : 'btn-run-batch');
  const batchCount = document.getElementById(isS2 ? 's2-batch-file-count' : 'batch-file-count');
  const batchBtnCount = document.getElementById(isS2 ? 's2-batch-btn-count' : 'batch-btn-count');
  
  if (validFiles.length > 1) {
    if (batchControls) batchControls.style.display = 'block';
    if (btnExtract) btnExtract.style.display = 'none';
    if (btnBatch) btnBatch.style.display = 'inline-flex';
    if (batchCount) batchCount.textContent = `${validFiles.length} files selected`;
    if (batchBtnCount) batchBtnCount.textContent = validFiles.length;
  } else {
    if (batchControls) batchControls.style.display = 'none';
    if (btnExtract) btnExtract.style.display = 'inline-flex';
    if (btnBatch) btnBatch.style.display = 'none';
  }
  
  // Reset the execution panel so the previous run's tracks are not mistaken
  // for this one, and re-run the pre-flight estimate for the new selection.
  const ids = execIds(strategy);
  renderExecFiles(strategy, []);
  execSetHeader(strategy, 'Idle', 'pending', '');
  const preflightEl = document.getElementById(ids.preflight);
  if (preflightEl) { preflightEl.style.display = 'none'; preflightEl.innerHTML = ''; }
  showLocalPreflight(strategy, validFiles);

  updateExtractButton(strategy);
}

// An immediate, browser-side sizing note so the user sees something before the
// server-side estimate arrives. Sizes only — token counts need the server.
function showLocalPreflight(strategy, files) {
  if (files.length < 2) return;
  const ids = execIds(strategy);
  const el = document.getElementById(ids.preflight);
  if (!el) return;
  const totalMb = files.reduce((acc, f) => acc + f.size, 0) / 1024 / 1024;
  el.style.display = 'block';
  el.innerHTML = `<div class="preflight">
    <div class="preflight-stats">
      <span>${files.length} files</span><span>${totalMb.toFixed(1)} MB</span>
    </div>
    Token estimate and recommended concurrency are computed when the run starts.
  </div>`;
}

function updateExtractButton(strategy = 's1') {
  const isS2 = strategy === 's2';
  const btnExtract = document.getElementById(isS2 ? 'btn-run-extract-s2' : 'btn-run-extract');
  const btnBatch = document.getElementById(isS2 ? 'btn-run-batch-s2' : 'btn-run-batch');
  
  const blocked = selectedFiles.length === 0 || !hasApiKey || activeRun;
  if (btnExtract) btnExtract.disabled = blocked;
  if (btnBatch) btnBatch.disabled = blocked;
}




function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}







function closeResultsTable() {
  const resultsEl = document.getElementById('inline-results');
  if (resultsEl) {
    resultsEl.style.display = 'none';
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ============================================================
//  EXECUTION: STREAMING, CONCURRENT, ANIMATED
// ============================================================

// The six pipeline steps every file passes through. `key` matches the step ids
// the server emits from pipeline.run_pipeline().
const PIPELINE_STEPS = [
  { key: 'upload',   short: 'Save' },
  { key: 'extract',  short: 'Extract' },
  { key: 'prompt',   short: 'Prompt' },
  { key: 'api',      short: 'Model' },
  { key: 'validate', short: 'Contract' },
  { key: 'output',   short: 'Output' }
];

function execIds(strategy) {
  const p = strategy === 's2' ? 's2-' : '';
  return {
    files: `${p}exec-files`,
    empty: `${p}exec-empty`,
    state: `${p}exec-state`,
    summary: `${p}exec-summary`,
    results: strategy === 's2' ? 's2-inline-results' : 'inline-results',
    runBtn: strategy === 's2' ? 'btn-run-extract-s2' : 'btn-run-extract',
    batchBtn: strategy === 's2' ? 'btn-run-batch-s2' : 'btn-run-batch',
    concurrency: strategy === 's2' ? 'input-s2-batch-concurrency' : 'input-batch-concurrency',
    reasoning: strategy === 's2' ? 'input-s2-reasoning' : 'input-s1-reasoning',
    temp: strategy === 's2' ? 'input-s2-temp' : 'input-s1-temp',
    prompt: strategy === 's2' ? 'input-s2-system-prompt' : 'input-system-prompt',
    preflight: strategy === 's2' ? 's2-preflight' : 'preflight'
  };
}

function execExtractorName(strategy) {
  return strategy === 's2' ? 'PyMuPDF4LLM' : 'PyPDF';
}

// Build one track per file. Every file gets its own row, so concurrent work is
// visible as concurrent work instead of a single shared progress bar.
function renderExecFiles(strategy, files) {
  const ids = execIds(strategy);
  const container = document.getElementById(ids.files);
  const empty = document.getElementById(ids.empty);
  if (!container) return;
  if (empty) empty.style.display = files.length ? 'none' : 'block';

  const stepsFor = file => PIPELINE_STEPS.map(step => ({
    ...step,
    // In a bake-off each row runs a different extractor, so the label is
    // per-row, not per-panel.
    short: step.key === 'extract'
      ? (file.strategy ? shortExtractorName(file.strategy) : execExtractorName(strategy))
      : step.short
  }));

  container.innerHTML = files.map((file, i) => `
    <div class="exec-file" id="${ids.files}-item-${i}">
      <div class="exec-file-head">
        <span class="exec-file-name" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</span>
        <span class="exec-file-status" id="${ids.files}-status-${i}">Queued</span>
      </div>
      ${(file.passes && file.passes.length > 1) ? `
      <div class="exec-passes" id="${ids.files}-passes-${i}">
        ${file.passes.map(k => `<span class="exec-pass" data-pass="${k}"
            id="${ids.files}-pass-${i}-${k}">${escapeHtml(shortExtractorName(k))}</span>`).join('')}
      </div>` : ''}
      <div class="exec-track">
        ${stepsFor(file).map(step => `<div class="exec-seg" data-step="${step.key}" id="${ids.files}-seg-${i}-${step.key}"></div>`).join('')}
      </div>
      <div class="exec-step-labels">
        ${stepsFor(file).map(step => step.key === 'extract'
          ? `<span id="${ids.files}-extractlabel-${i}">${escapeHtml(step.short)}</span>`
          : `<span>${escapeHtml(step.short)}</span>`).join('')}
      </div>
      <div class="exec-message" id="${ids.files}-msg-${i}">${file.pages ? `${file.pages} pages · ~${formatNumber(file.approx_tokens)} est. tokens` : 'Waiting to start'}</div>
    </div>
  `).join('');
}

function execMarkStep(strategy, index, stepKey, state) {
  const ids = execIds(strategy);
  const stepIndex = PIPELINE_STEPS.findIndex(st => st.key === stepKey);
  if (stepIndex < 0) return;

  // Everything before the current step is finished by definition.
  PIPELINE_STEPS.forEach((st, i) => {
    const seg = document.getElementById(`${ids.files}-seg-${index}-${st.key}`);
    if (!seg) return;
    if (i < stepIndex) seg.className = 'exec-seg done';
    else if (i === stepIndex) seg.className = `exec-seg ${state}`;
  });
}

// Switch the row to a new technology pass: relabel the extract step, mark the
// matching chip active, and reset the track so the animation replays.
function execSetPass(strategy, index, passKey, plan) {
  const ids = execIds(strategy);
  const label = document.getElementById(`${ids.files}-extractlabel-${index}`);
  if (label) label.textContent = shortExtractorName(passKey);

  PIPELINE_STEPS.forEach(st => {
    const seg = document.getElementById(`${ids.files}-seg-${index}-${st.key}`);
    if (seg) seg.className = 'exec-seg';
  });

  (plan || []).forEach(k => {
    const chip = document.getElementById(`${ids.files}-pass-${index}-${k}`);
    if (chip && !chip.classList.contains('done') && !chip.classList.contains('failed')) {
      chip.classList.toggle('active', k === passKey);
    }
  });
}

function execMarkPassDone(strategy, index, passKey, ok) {
  const ids = execIds(strategy);
  const chip = document.getElementById(`${ids.files}-pass-${index}-${passKey}`);
  if (chip) {
    chip.classList.remove('active');
    chip.classList.add(ok ? 'done' : 'failed');
  }
}

// Belt-and-braces: once a file is finished, nothing on its row may still be
// animating, whatever order its events arrived in.
function execFreezeRow(strategy, index) {
  const ids = execIds(strategy);
  PIPELINE_STEPS.forEach(st => {
    const seg = document.getElementById(`${ids.files}-seg-${index}-${st.key}`);
    if (seg && (seg.classList.contains('active') || seg.classList.contains('throttled'))) {
      seg.className = 'exec-seg failed';
    }
  });
  const ids2 = execIds(strategy);
  document.querySelectorAll(`#${ids2.files}-item-${index} .exec-pass.active`)
    .forEach(chip => chip.classList.remove('active'));
}

function execSetStatus(strategy, index, text, message) {
  const ids = execIds(strategy);
  const statusEl = document.getElementById(`${ids.files}-status-${index}`);
  if (statusEl && text !== undefined) statusEl.textContent = text;
  const msgEl = document.getElementById(`${ids.files}-msg-${index}`);
  if (msgEl && message !== undefined) msgEl.textContent = message;
}

function execSetCardState(strategy, index, cls) {
  const ids = execIds(strategy);
  const card = document.getElementById(`${ids.files}-item-${index}`);
  if (card) card.className = `exec-file ${cls}`;
}

function execSetHeader(strategy, stateText, stateClass, summaryHtml) {
  const ids = execIds(strategy);
  const badge = document.getElementById(ids.state);
  if (badge) {
    badge.textContent = stateText;
    badge.className = `table-badge ${stateClass}`;
  }
  const summary = document.getElementById(ids.summary);
  if (summary) {
    summary.style.display = summaryHtml ? 'flex' : 'none';
    summary.innerHTML = summaryHtml || '';
  }
}

function renderPreflight(strategy, data) {
  const ids = execIds(strategy);
  const el = document.getElementById(ids.preflight);
  if (!el) return;
  const plan = data.plan || {};
  const failed = (data.files || []).filter(f => f.error);

  el.style.display = 'block';
  el.innerHTML = `
    <div class="preflight">
      <div class="preflight-stats">
        <span>${plan.file_count || 0} file${plan.file_count === 1 ? '' : 's'}</span>
        <span>${formatNumber(plan.total_pages)} pages</span>
        <span>~${formatNumber(plan.total_approx_tokens)} input tokens (estimated)</span>
        <span>Concurrency ${plan.recommended_concurrency}</span>
      </div>
      ${plan.advisories && plan.advisories.length
        ? `<ul>${plan.advisories.map(a => `<li>${escapeHtml(a)}</li>`).join('')}</ul>`
        : ''}
      ${failed.length
        ? `<ul>${failed.map(f => `<li>${escapeHtml(f.name)}: ${escapeHtml(f.error)}</li>`).join('')}</ul>`
        : ''}
    </div>`;
}

// ---- Streaming run ---------------------------------------------------------

// Parses an SSE body incrementally. EventSource cannot be used because this is
// a POST with a JSON body.

let bakeoffResults = [];

const EXTRACTOR_SHORT = {
  's1': 'PyPDF',
  's2': 'PyMuPDF4LLM',
  's2-docling': 'Docling',
  's2-inspector': 'pdf-inspector'
};

function shortExtractorName(key) {
  return EXTRACTOR_SHORT[key] || key;
}

// With four parsers in play, "Strategy 2" alone does not identify a run. Every
// run table names the parsing technology that produced it.
function parserChip(run) {
  const key = SERIES_KEYS.includes(run.strategy) ? run.strategy : runStrategy(run);
  const style = seriesStyle(key);
  return `<span class="parser-chip" style="color:${style.color};background:${style.fill};">`
       + `${escapeHtml(shortExtractorName(key))}</span>`;
}

function selectedExtractors() {
  const picker = document.getElementById('s2-extractor-picker');
  if (!picker) return ['s2'];
  return [...picker.querySelectorAll('input[type=checkbox]:checked')].map(el => el.value);
}

function initS2ExtractorPicker() {
  const picker = document.getElementById('s2-extractor-picker');
  if (!picker) return;
  const update = () => {
    const n = selectedExtractors().length;
    const files = Math.max(selectedFiles.length, 1);
    const label = document.getElementById('s2-extractor-count');
    if (label) {
      label.textContent = `${n} selected · ${n * files} GLM call${n * files === 1 ? '' : 's'}`
        + (selectedFiles.length > 1 ? ` for ${selectedFiles.length} PDFs` : ' per PDF');
    }
    updateExtractButton('s2');
  };
  picker.addEventListener('change', update);
  update();
}

// Rank the technologies on the run that just finished. Accuracy first when the
// fiscal year has an answer key, otherwise coverage — and the ranking is
// reported with an explicit caveat when the spread is inside known run-to-run
// variance, because at one run per cell it usually is.
function renderBakeoff() {
  const card = document.getElementById('s2-bakeoff-card');
  const tableEl = document.getElementById('s2-bakeoff-table');
  const verdictEl = document.getElementById('s2-bakeoff-verdict');
  if (!card || !tableEl) return;

  const ok = bakeoffResults.filter(r => r.ok);
  if (ok.length === 0) { card.style.display = 'none'; return; }
  if (card.style.display !== 'block') {
    card.style.display = 'block';
    card.classList.add('card-appear');
  }
  const sub = document.getElementById('s2-bakeoff-subtitle');
  if (sub) {
    sub.textContent = `Same PDF, same prompt — only the parser differs · ${ok.length} result${ok.length === 1 ? '' : 's'} in`;
  }

  // Aggregate per extractor across whatever files were run.
  const agg = {};
  bakeoffResults.forEach(r => {
    const k = r.strategy || 's2';
    agg[k] = agg[k] || { key: k, runs: 0, failed: 0, acc: [], cov: [], prec: [], cons: [], tok: [], parse: [], secs: [] };
    if (!r.ok) { agg[k].failed++; return; }
    const m = r.metrics || {};
    agg[k].runs++;
    if (m.accuracy !== null && m.accuracy !== undefined) agg[k].acc.push(Number(m.accuracy));
    if (m.coverage !== null && m.coverage !== undefined) agg[k].cov.push(Number(m.coverage));
    if (m.precision !== null && m.precision !== undefined) agg[k].prec.push(Number(m.precision));
    if (r.consistency !== null && r.consistency !== undefined) agg[k].cons.push(Number(r.consistency));
    if (r.input_tokens) agg[k].tok.push(Number(r.input_tokens));
    if (r.extract_seconds !== null && r.extract_seconds !== undefined) agg[k].parse.push(Number(r.extract_seconds));
    if (r.total_seconds) agg[k].secs.push(Number(r.total_seconds));
  });

  const mean = a => (a.length ? a.reduce((x, y) => x + y, 0) / a.length : null);
  const rows = Object.values(agg).map(a => ({
    key: a.key,
    name: shortExtractorName(a.key),
    runs: a.runs,
    failed: a.failed,
    accuracy: mean(a.acc),
    coverage: mean(a.cov),
    precision: mean(a.prec),
    consistency: mean(a.cons),
    tokens: mean(a.tok),
    parse: mean(a.parse),
    seconds: mean(a.secs)
  }));

  const scored = rows.some(r => r.accuracy !== null);
  const rank = r => (scored ? (r.accuracy ?? -1) : (r.coverage ?? -1));
  rows.sort((a, b) => rank(b) - rank(a));

  const best = rows[0];
  const spread = rank(best) - rank(rows[rows.length - 1]);
  const cheapest = rows.slice().sort((a, b) => (a.tokens ?? 1e12) - (b.tokens ?? 1e12))[0];

  const fmt = (v, suffix = '%') => (v === null || v === undefined ? '—' : `${v.toFixed(1)}${suffix}`);
  tableEl.innerHTML = `
    <div class="table-wrapper">
      <table class="data-table">
        <thead><tr>
          <th>Technology</th><th>Runs</th>
          <th>${scored ? 'Exact accuracy' : 'Accuracy'}</th>
          <th>Coverage</th><th>Precision</th><th>Consistency</th>
          <th>Input tokens</th><th>Parse time</th><th>Total time</th>
        </tr></thead>
        <tbody>
          ${rows.map((r, i) => `
            <tr class="${i === 0 ? 'subtotal' : ''}">
              <td><strong>${escapeHtml(r.name)}</strong>${r.failed ? ` <span class="table-badge error">${r.failed} failed</span>` : ''}</td>
              <td class="table-value">${r.runs}</td>
              <td class="table-value">${fmt(r.accuracy)}</td>
              <td class="table-value">${fmt(r.coverage)}</td>
              <td class="table-value">${fmt(r.precision)}</td>
              <td class="table-value">${fmt(r.consistency)}</td>
              <td class="table-value">${r.tokens ? formatNumber(Math.round(r.tokens)) : '—'}</td>
              <td class="table-value"><strong>${r.parse !== null && r.parse !== undefined ? formatSeconds(r.parse) : '—'}</strong></td>
              <td class="table-value">${r.seconds ? formatSeconds(r.seconds) : '—'}</td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>`;

  // A spread this small is inside the run-to-run variance measured on this
  // corpus (up to 7.4 points on an unchanged input), so say so rather than
  // presenting a coin flip as a winner.
  const inconclusive = spread < 7.5;

  // Parsing speed is deterministic, so a multiple is a real claim rather than a
  // sampled one. Report the fastest against every slower technology.
  const timed = rows.filter(r => r.parse !== null && r.parse !== undefined && r.parse > 0);
  const fastest = timed.slice().sort((a, b) => a.parse - b.parse)[0];
  let speedLine = '';
  if (fastest && timed.length > 1) {
    const others = timed.filter(r => r.key !== fastest.key)
      .sort((a, b) => a.parse - b.parse)
      .map(r => `${(r.parse / fastest.parse).toFixed(1)}× faster than ${escapeHtml(r.name)}`);
    speedLine = `<div style="margin-top:6px;">
      <strong>${escapeHtml(fastest.name)}</strong> parses in ${formatSeconds(fastest.parse)} —
      ${others.join(', ')}.</div>`;
  }

  verdictEl.innerHTML = `
    <div class="verdict-box ${inconclusive ? 'inconclusive' : ''}">
      <div>
        <div>
          <span class="verdict-winner">${escapeHtml(best.name)}</span>
          ${inconclusive
            ? ` leads on ${scored ? 'accuracy' : 'coverage'} (${fmt(rank(best))}), but the spread across all
               technologies is only ${spread.toFixed(1)} points — inside the run-to-run variance measured on
               this corpus. <strong>Treat the quality ranking as inconclusive at one run per cell.</strong>`
            : ` wins on ${scored ? 'accuracy' : 'coverage'} (${fmt(rank(best))}), ahead by ${spread.toFixed(1)} points.`}
          Cheapest on tokens: <strong>${escapeHtml(cheapest.name)}</strong>
          at ${cheapest.tokens ? formatNumber(Math.round(cheapest.tokens)) : '—'}.
        </div>
        ${speedLine}
      </div>
    </div>`;
}
// ============================================================
//  ACCURACY BENCHMARK & EVALUATION ENGINE (Multi-Year Ground Truth)
// ============================================================
function miniPieSvg(percent, color = '#16a34a', size = 22) {
  const r = 8, cx = size/2, cy = size/2;
  const circumference = 2 * Math.PI * r;
  const filled = (percent / 100) * circumference;
  const empty = circumference - filled;
  return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" style="vertical-align: middle; margin-right: 4px;">
    <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="#e5e7eb" stroke-width="3"/>
    <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${color}" stroke-width="3"
      stroke-dasharray="${filled} ${empty}" stroke-dashoffset="${circumference/4}" stroke-linecap="round"/>
  </svg>`;
}

const SCHEMA_ROW_COUNT = 27;
// Measured, not chosen: across 824 scored observations the model's confidence
// is ~59% correct in the 0.50-0.80 band and 94-100% correct at/above 0.80.
// Must match CONFIDENCE_THRESHOLD in pipeline.py.
const CONFIDENCE_THRESHOLD = 0.8;

// A row counts as answered only when it has a value AND the model was confident
// about it; a low-confidence guess is not an answer. Mirrors compute_metrics()
// in pipeline.py so the UI and the stored run never disagree.
function isAnswered(row) {
  const value = row.answer_m_usd;
  if (value === null || value === undefined) return false;
  const confidence = (row.confidence === undefined || row.confidence === null) ? 1.0 : Number(row.confidence);
  return !Number.isNaN(confidence) && confidence >= CONFIDENCE_THRESHOLD;
}

function isExactMatch(row, expected) {
  if (expected === undefined || expected === null) return false;
  if (!isAnswered(row)) return false;
  return Math.abs(Number(row.answer_m_usd) - Number(expected)) < 0.5;
}

function calculateAccuracy(rows, fiscalYear) {
  const golden = getGoldenAnswers(fiscalYear);
  let exactMatches = 0;
  let totalCompared = 0;
  let filledCount = 0;

  (rows || []).forEach(r => {
    if (isAnswered(r)) filledCount++;
    const expected = golden[r.item];
    if (expected === undefined || expected === null) return;
    totalCompared++;
    if (isExactMatch(r, expected)) exactMatches++;
  });

  return {
    accuracy: totalCompared > 0 ? ((exactMatches / totalCompared) * 100).toFixed(1) : null,
    exact: exactMatches,
    diff: totalCompared - exactMatches,
    total: totalCompared,
    coverage: ((filledCount / SCHEMA_ROW_COUNT) * 100).toFixed(1),
    filled: filledCount,
    scored: totalCompared > 0
  };
}

// "—" rather than "0.0%" when there is no answer key: an unscored run is not a
// run that scored zero.
function formatAccuracy(stats) {
  return stats && stats.scored ? `${stats.accuracy}%` : '—';
}

function updateDashboardStats() {
  const totalRunsEl = document.getElementById('stat-total-runs');
  if (totalRunsEl) totalRunsEl.textContent = String(allRuns.length);

  if (allRuns.length === 0) {
    resetDashboardToEmptyState();
    return;
  }

  // allRuns is newest-first, so [0] is the latest run overall.
  const latest = allRuns[0];
  const scoredCount = allRuns.filter(r => r.accuracy !== undefined && r.accuracy !== null).length;

  const detail = document.getElementById('stat-total-runs-detail');
  if (detail) {
    detail.textContent = `${allRuns.length} logged · ${scoredCount} scored`;
  }

  const setStat = (id, value, detailId, detailText) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
    const d = document.getElementById(detailId);
    if (d) d.textContent = detailText;
  };

  const scored = latest.accuracy !== undefined && latest.accuracy !== null;
  setStat(
    'stat-accuracy',
    scored ? `${Number(latest.accuracy).toFixed(1)}%` : '—',
    'stat-accuracy-detail',
    scored
      ? `Latest run · ${latest.exact_matches} of ${latest.total_compared} exact`
      : `Latest run · FY ${latest.fiscal_year || '—'} has no answer key`
  );

  setStat(
    'stat-coverage',
    latest.coverage !== undefined && latest.coverage !== null ? `${Number(latest.coverage).toFixed(1)}%` : '—',
    'stat-coverage-detail',
    `Latest run · ${latest.filled_fields || 0} of ${SCHEMA_ROW_COUNT} fields`
  );

  setStat(
    'stat-time',
    formatSeconds(latest.api_elapsed),
    'stat-time-detail',
    `Latest run · ${seriesStyle(latest.strategy || runStrategy(latest)).label.split(' · ')[0]}`
  );

  const tokensEl = document.getElementById('stat-tokens');
  if (tokensEl) tokensEl.textContent = formatNumber(latest.approx_input_tokens);
  const charsDetailEl = document.getElementById('stat-chars-detail');
  if (charsDetailEl) {
    charsDetailEl.textContent = latest.page_count
      ? `Latest run · ${latest.page_count} pages`
      : 'Latest run';
  }

  updateStrategyCardsStats();
  renderDashboardCharts();
}

function resetDashboardToEmptyState() {
  lastResult = null;

  const setText = (id, value) => { const el = document.getElementById(id); if (el) el.textContent = value; };
  setText('stat-total-runs', '0');
  setText('stat-total-runs-detail', 'Experiments logged');
  setText('stat-accuracy', '—');
  setText('stat-accuracy-detail', 'No runs evaluated');
  setText('stat-coverage', '—');
  setText('stat-coverage-detail', `0 of ${SCHEMA_ROW_COUNT} fields extracted`);
  setText('stat-time', '—');
  setText('stat-time-detail', 'Latest run');
  setText('stat-tokens', '—');
  setText('stat-chars-detail', 'Latest run');

  ['s1-card-acc', 's1-card-cov', 's1-card-lat', 's2-card-acc', 's2-card-cov', 's2-card-lat']
    .forEach(id => setText(id, '—'));

  renderDashboardCharts();

  const resultsEl = document.getElementById('inline-results');
  if (resultsEl) resultsEl.style.display = 'none';
  const s2ResultsEl = document.getElementById('s2-inline-results');
  if (s2ResultsEl) s2ResultsEl.style.display = 'none';
}

function updateStrategyCardsStats() {
  // Strategy 1 Cumulative / Average Stats
  const s1Runs = allRuns.filter(r => runStrategy(r) === 's1');
  const cardS1Acc = document.getElementById('s1-card-acc');
  const cardS1Cov = document.getElementById('s1-card-cov');
  const cardS1Lat = document.getElementById('s1-card-lat');

  if (s1Runs.length > 0) {
    const validAcc = s1Runs.filter(r => r.accuracy !== undefined && r.accuracy !== null);
    const avgAcc = validAcc.length > 0 ? (validAcc.reduce((a, b) => a + Number(b.accuracy), 0) / validAcc.length).toFixed(1) : '—';
    const validCov = s1Runs.filter(r => r.coverage !== undefined && r.coverage !== null);
    const avgCov = validCov.length > 0 ? (validCov.reduce((a, b) => a + Number(b.coverage), 0) / validCov.length).toFixed(1) : '—';
    const validLat = s1Runs.filter(r => r.api_elapsed);
    const avgLat = validLat.length > 0 ? (validLat.reduce((a, b) => a + Number(b.api_elapsed), 0) / validLat.length).toFixed(1) : '—';

    if (cardS1Acc) cardS1Acc.textContent = `${avgAcc}%`;
    if (cardS1Cov) cardS1Cov.textContent = `${avgCov}%`;
    if (cardS1Lat) cardS1Lat.textContent = `${avgLat}s`;
  } else {
    if (cardS1Acc) cardS1Acc.textContent = '—';
    if (cardS1Cov) cardS1Cov.textContent = '—';
    if (cardS1Lat) cardS1Lat.textContent = '—';
  }

  // Strategy 2 Cumulative / Average Stats
  const s2Runs = allRuns.filter(r => runStrategy(r) === 's2');
  const cardS2Acc = document.getElementById('s2-card-acc');
  const cardS2Cov = document.getElementById('s2-card-cov');
  const cardS2Lat = document.getElementById('s2-card-lat');

  if (s2Runs.length > 0) {
    const validAcc = s2Runs.filter(r => r.accuracy !== undefined && r.accuracy !== null);
    const avgAcc = validAcc.length > 0 ? (validAcc.reduce((a, b) => a + Number(b.accuracy), 0) / validAcc.length).toFixed(1) : '—';
    const validCov = s2Runs.filter(r => r.coverage !== undefined && r.coverage !== null);
    const avgCov = validCov.length > 0 ? (validCov.reduce((a, b) => a + Number(b.coverage), 0) / validCov.length).toFixed(1) : '—';
    const validLat = s2Runs.filter(r => r.api_elapsed);
    const avgLat = validLat.length > 0 ? (validLat.reduce((a, b) => a + Number(b.api_elapsed), 0) / validLat.length).toFixed(1) : '—';

    if (cardS2Acc) cardS2Acc.textContent = `${avgAcc}%`;
    if (cardS2Cov) cardS2Cov.textContent = `${avgCov}%`;
    if (cardS2Lat) cardS2Lat.textContent = `${avgLat}s`;
  } else {
    if (cardS2Acc) cardS2Acc.textContent = '—';
    if (cardS2Cov) cardS2Cov.textContent = '—';
    if (cardS2Lat) cardS2Lat.textContent = '—';
  }
}

function formatNumber(n) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return '—';
  return Number(n).toLocaleString('en-US');
}

function formatDollarMillions(val) {
  if (val === null || val === undefined) return '—';
  const num = Math.round(Number(val));
  if (Number.isNaN(num)) return '—';
  if (num < 0) {
    return `-$${Math.abs(num).toLocaleString('en-US')}M`;
  }
  return `$${num.toLocaleString('en-US')}M`;
}

// Latency is missing on failed or partially written runs; `.toFixed()` on
// undefined used to throw here and abort the whole render.
function formatSeconds(seconds) {
  const value = Number(seconds);
  return Number.isFinite(value) && value > 0 ? `${value.toFixed(1)}s` : '—';
}

// ---- Run verdicts ---------------------------------------------------------

// Every outcome maps to a fixed, pre-written line. Nothing here is generated or
// reasoned about at display time: a given state always produces the same words,
// so two runs in the same state read identically.
const VERDICT_COPY = {
  reconciled: {
    tone: 'ok',
    title: 'Internally consistent',
    detail: n => `All ${n} subtotal identities reconcile — every subtotal equals the sum of its parts.`
  },
  reconciled_partial: {
    tone: 'ok',
    title: 'Consistent where checkable',
    detail: (n, skipped, total) =>
      `${n} of ${total} subtotal identities reconcile. The other ${skipped} could not be checked `
      + 'because a row they depend on was left unanswered.'
  },
  failed: {
    tone: 'bad',
    title: 'Does not add up',
    detail: names =>
      `${names.length} subtotal${names.length === 1 ? '' : 's'} disagree with the sum of its parts: `
      + `${names.join(', ')}. A component was read into the wrong row, or a value is wrong.`
  },
  unverifiable: {
    tone: 'warn',
    title: 'Not verifiable',
    detail: unanswered =>
      `${unanswered} of ${SCHEMA_ROW_COUNT} rows were left unanswered, so no subtotal identity `
      + 'could be checked. Answer more rows to make the arithmetic checkable.'
  },
  unreadable_pages: {
    tone: 'warn',
    title: 'Unreadable pages skipped',
    detail: n => `${n} page${n === 1 ? '' : 's'} had no usable text layer and were excluded from the prompt. `
      + 'Figures that appear only there cannot be recovered without OCR.'
  },
  repairs: {
    tone: 'info',
    title: 'Reply repaired before validation',
    detail: n => `${n} formatting issue${n === 1 ? '' : 's'} in the model's JSON were corrected `
      + '(number formats, row order or item names) before the contract was applied.'
  },
  not_scored: {
    tone: 'info',
    title: 'Not scored',
    detail: fy => `No answer key is stored for FY ${fy || '—'}, so coverage is reported but accuracy is not.`
  }
};

function verdictChip(kind, detail) {
  const copy = VERDICT_COPY[kind];
  if (!copy) return '';
  return `<div class="verdict verdict-${copy.tone}">
      <span class="verdict-title">${escapeHtml(copy.title)}</span>
      <span class="verdict-detail">${escapeHtml(detail)}</span>
    </div>`;
}

// Builds the whole verdict strip for a run: reconciliation first, then any
// pipeline warnings, then contract repairs.
function renderRunVerdicts(containerId, data) {
  const el = document.getElementById(containerId);
  if (!el) return;

  const chips = [];
  const rec = data.reconciliation;

  if (rec && rec.checks) {
    const unanswered = (data.rows || []).filter(r => !isAnswered(r)).length;
    if (rec.evaluated === 0) {
      chips.push(verdictChip('unverifiable', VERDICT_COPY.unverifiable.detail(unanswered)));
    } else if (rec.failed > 0) {
      chips.push(verdictChip('failed', VERDICT_COPY.failed.detail(rec.failed_identities)));
    } else if (rec.skipped > 0) {
      chips.push(verdictChip('reconciled_partial',
        VERDICT_COPY.reconciled_partial.detail(rec.evaluated, rec.skipped, rec.total_identities)));
    } else {
      chips.push(verdictChip('reconciled', VERDICT_COPY.reconciled.detail(rec.evaluated)));
    }
  }

  const fy = String(data.detected_fiscal_year || data.fiscal_year || '').trim();
  if (!hasGoldenAnswers(fy)) {
    chips.push(verdictChip('not_scored', VERDICT_COPY.not_scored.detail(fy)));
  }

  const garbled = (data.garbled_pages || []).length;
  if (garbled) chips.push(verdictChip('unreadable_pages', VERDICT_COPY.unreadable_pages.detail(garbled)));

  const repairs = (data.contract_repairs || []).length;
  if (repairs) chips.push(verdictChip('repairs', VERDICT_COPY.repairs.detail(repairs)));

  el.innerHTML = chips.join('');
  el.style.display = chips.length ? 'flex' : 'none';
}

// ============================================================
//  CHARTS (Values in $M USD + Exact Accuracy + Coverage Rings)
// ============================================================
// Accuracy of every scored run, ordered oldest → newest and grouped by
// strategy: each strategy is a contiguous, differently-coloured segment, and
// the next segment starts from where the previous one ended.
// Colours chosen to be distinguishable at a glance and in greyscale: blue,
// amber, teal, magenta. Blue vs purple read as the same line on this chart.
const STRATEGY_STYLE = {
  s1: { label: 'Strategy 1 · PyPDF baseline', color: '#2563eb', fill: 'rgba(37, 99, 235, 0.12)' },
  s2: { label: 'Strategy 2 · Document representation', color: '#d97706', fill: 'rgba(217, 119, 6, 0.14)' },
  s3: { label: 'Strategy 3 · Hybrid RAG', color: '#0d9488', fill: 'rgba(13, 148, 136, 0.12)' },
  s4: { label: 'Strategy 4 · Agentic verification', color: '#be185d', fill: 'rgba(190, 24, 93, 0.12)' }
};

// Strategy 2 covers several parsers; the chart separates them so a bake-off is
// readable rather than collapsing into one amber line.
const EXTRACTOR_STYLE = {
  's2': { label: 'S2 · PyMuPDF4LLM', color: '#d97706', fill: 'rgba(217, 119, 6, 0.14)' },
  's2-docling': { label: 'S2 · Docling', color: '#7c3aed', fill: 'rgba(124, 58, 237, 0.12)' },
  's2-inspector': { label: 'S2 · pdf-inspector', color: '#059669', fill: 'rgba(5, 150, 105, 0.12)' }
};

function seriesStyle(key) {
  return EXTRACTOR_STYLE[key] || STRATEGY_STYLE[key] || STRATEGY_STYLE.s1;
}

const SERIES_KEYS = ['s1', 's2', 's2-docling', 's2-inspector', 's3', 's4'];

// Aggregate every stored run by the parsing technology that produced it.
function statsByParser() {
  const agg = {};
  allRuns.forEach(run => {
    const key = SERIES_KEYS.includes(run.strategy) ? run.strategy : runStrategy(run);
    agg[key] = agg[key] || { key, runs: 0, acc: [], parse: [], tokens: [] };
    agg[key].runs++;
    if (run.accuracy !== null && run.accuracy !== undefined) agg[key].acc.push(Number(run.accuracy));
    if (run.extract_seconds !== null && run.extract_seconds !== undefined) agg[key].parse.push(Number(run.extract_seconds));
    if (run.approx_input_tokens) agg[key].tokens.push(Number(run.approx_input_tokens));
  });
  const mean = a => (a.length ? a.reduce((x, y) => x + y, 0) / a.length : null);
  return Object.values(agg).map(a => ({
    key: a.key,
    name: shortExtractorName(a.key),
    runs: a.runs,
    scored: a.acc.length,
    accuracy: mean(a.acc),
    parse: mean(a.parse),
    tokens: mean(a.tokens)
  }));
}

// Accuracy vs parse time for the parsing technologies, laid out like a
// price/performance frontier chart: shaded "most attractive" quadrant, a dashed
// Pareto line through the non-dominated points, and bare technology names as
// labels. Parse times span 1.2s to 109s, so the x axis is logarithmic.
function drawParserChart() {
  const canvas = document.getElementById('chart-accuracy');
  if (!canvas || !canvas.parentElement) return;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.parentElement.getBoundingClientRect();
  const w = rect.width, h = rect.height || 400;
  canvas.width = w * dpr; canvas.height = h * dpr;
  canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);

  // Generous left padding: the rotated axis title sits outside the tick labels
  // instead of colliding with them.
  const padLeft = 84, padRight = 34, padTop = 20, padBottom = 62;
  const plotW = Math.max(10, w - padLeft - padRight);
  const plotH = Math.max(10, h - padTop - padBottom);

  const points = statsByParser().filter(p => p.parse !== null && p.accuracy !== null);

  // Y range framed around the data rather than always 0-100, so the points are
  // not squeezed into one band.
  let yMin = 0, yMax = 100;
  if (points.length) {
    const accs = points.map(p => p.accuracy);
    const lo = Math.min(...accs), hi = Math.max(...accs);
    const pad = Math.max(8, (hi - lo) * 0.9);
    yMin = Math.max(0, Math.floor((lo - pad) / 10) * 10);
    yMax = Math.min(100, Math.ceil((hi + pad) / 10) * 10);
    if (yMax - yMin < 20) { yMax = Math.min(100, yMin + 20); }
  }
  const yFor = pct => padTop + plotH - ((pct - yMin) / (yMax - yMin)) * plotH;

  const TICKS = [0.5, 1, 2, 5, 10, 30, 100, 300];
  const lo = Math.log10(0.5), hi = Math.log10(300);
  const xFor = secs => padLeft + ((Math.log10(Math.min(Math.max(secs, 0.5), 300)) - lo) / (hi - lo)) * plotW;

  // Attractive quadrant: fast and accurate. Drawn first, under everything.
  if (points.length) {
    const medianX = xFor(10);
    const midAcc = (yMin + yMax) / 2;
    ctx.fillStyle = '#eff6ff';
    ctx.fillRect(padLeft, padTop, medianX - padLeft, yFor(midAcc) - padTop);
    ctx.strokeStyle = '#dbeafe';
    ctx.lineWidth = 1;
    ctx.strokeRect(padLeft + 0.5, padTop + 0.5, medianX - padLeft, yFor(midAcc) - padTop);
  }

  ctx.font = '11px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
  ctx.textBaseline = 'middle'; ctx.textAlign = 'right';
  const step = (yMax - yMin) <= 30 ? 5 : 10;
  for (let pct = yMin; pct <= yMax; pct += step) {
    const y = yFor(pct);
    ctx.strokeStyle = pct === yMin ? '#d1d5db' : '#eef0f3';
    ctx.setLineDash(pct === yMin ? [] : [3, 3]);
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(padLeft, Math.round(y) + 0.5); ctx.lineTo(padLeft + plotW, Math.round(y) + 0.5); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = '#9ca3af'; ctx.fillText(`${pct}%`, padLeft - 12, y);
  }

  ctx.textAlign = 'center'; ctx.textBaseline = 'top';
  TICKS.forEach(t => {
    const x = xFor(t);
    ctx.fillStyle = '#9ca3af';
    ctx.fillText(t < 1 ? `${t}s` : `${t}s`, x, padTop + plotH + 10);
  });
  ctx.strokeStyle = '#d1d5db';
  ctx.beginPath(); ctx.moveTo(padLeft, padTop + plotH + 0.5); ctx.lineTo(padLeft + plotW, padTop + plotH + 0.5); ctx.stroke();

  ctx.fillStyle = '#4b5563';
  ctx.font = '600 12px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
  ctx.fillText('Parse time per document (log scale)', padLeft + plotW / 2, padTop + plotH + 34);
  ctx.save();
  ctx.translate(22, padTop + plotH / 2); ctx.rotate(-Math.PI / 2);
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText('Exact accuracy', 0, 0);
  ctx.restore();

  if (points.length === 0) {
    ctx.fillStyle = '#9ca3af'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.font = '13px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
    ctx.fillText('No runs with both a parse time and a score yet', padLeft + plotW / 2, padTop + plotH / 2);
    return;
  }

  const byTime = points.slice().sort((a, b) => a.parse - b.parse);

  // A point is Pareto-optimal when nothing else is both faster and at least as
  // accurate. When one technology dominates outright the frontier is a single
  // point, so the dashed line joins every technology in parse-time order and
  // the dominant one is marked separately.
  const frontier = [];
  let bestSoFar = -Infinity;
  byTime.forEach(p => {
    if (p.accuracy > bestSoFar) { frontier.push(p); bestSoFar = p.accuracy; }
  });

  const MARKER_R = 8;
  const WINNER_R = 10;
  const radiusOf = p => (p.key === byTime[0].key && frontier.includes(p) ? WINNER_R : MARKER_R);

  // Draw each segment from the edge of one marker to the edge of the next, with
  // a small gap, so a connector never crosses or sits on top of a circle.
  const connect = (list, dashed) => {
    ctx.save();
    ctx.setLineDash(dashed ? [5, 5] : []);
    ctx.strokeStyle = dashed ? '#94a3b8' : '#475569';
    ctx.lineWidth = dashed ? 1.5 : 2;
    for (let i = 0; i < list.length - 1; i++) {
      const a = list[i], b = list[i + 1];
      const ax = xFor(a.parse), ay = yFor(a.accuracy);
      const bx = xFor(b.parse), by = yFor(b.accuracy);
      const dx = bx - ax, dy = by - ay;
      const len = Math.hypot(dx, dy);
      if (len === 0) continue;
      const ux = dx / len, uy = dy / len;
      const gapA = radiusOf(a) + 4;
      const gapB = radiusOf(b) + 4;
      if (len <= gapA + gapB) continue;   // markers touch: nothing to draw
      ctx.beginPath();
      ctx.moveTo(ax + ux * gapA, ay + uy * gapA);
      ctx.lineTo(bx - ux * gapB, by - uy * gapB);
      ctx.stroke();
    }
    ctx.restore();
  };

  if (byTime.length > 1) {
    connect(byTime, true);
    // Solid over the Pareto-optimal stretch, when there is one.
    if (frontier.length > 1) connect(frontier, false);
  }

  const best = points.reduce((a, b) => (b.accuracy > a.accuracy ? b : a), points[0]);
  const fastest = byTime[0];

  // Flat, solid markers. The previous version stacked a grey halo around the
  // dot, which read as a smudge rather than a data point.
  points.forEach(p => {
    const style = seriesStyle(p.key);
    const x = xFor(p.parse), y = yFor(p.accuracy);
    const r = radiusOf(p);

    // Opaque fill: a translucent marker let the connector show through it.
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fillStyle = style.color;
    ctx.fill();

    // Hairline in a darker shade of the marker's own colour, so the edge is
    // defined on every background without introducing a second colour.
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = 'rgba(15, 23, 42, 0.35)';
    ctx.stroke();

    // The dominant technology is marked by a white core, not by a halo — but
    // only when there is more than one technology for it to dominate.
    if (points.length > 1 && p.key === fastest.key && frontier.includes(p)) {
      ctx.beginPath();
      ctx.arc(x, y, 3.5, 0, Math.PI * 2);
      ctx.fillStyle = '#ffffff';
      ctx.fill();
    }
  });

  // Labels: the technology name only. Alternated above/below so neighbouring
  // points do not collide.
  byTime.forEach((p, i) => {
    const style = seriesStyle(p.key);
    const x = xFor(p.parse), y = yFor(p.accuracy);
    const above = i % 2 === 0;
    const nearRight = x > padLeft + plotW * 0.72;
    ctx.font = (p.key === best.key ? '700 ' : '600 ') + '13px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
    ctx.fillStyle = style.color;
    ctx.textAlign = nearRight ? 'right' : 'left';
    ctx.textBaseline = above ? 'bottom' : 'top';
    ctx.fillText(p.name, x + (nearRight ? -16 : 16), y + (above ? -8 : 8));
  });
}

// S2 Evidence Table Rendering
function renderEvidenceTableS2(data) {
  const rows = data.rows || [];
  const tbody = document.getElementById('s2-evidence-table-body');
  if (!tbody) return;
  tbody.innerHTML = rows.map(r => `<tr>
    <td><strong>${escapeHtml(r.item)}</strong></td>
    <td class="table-value">${r.source_page !== null && r.source_page !== undefined ? r.source_page : '—'}</td>
    <td>${escapeHtml(r.source_label || '—')}</td>
    <td style="font-size:12px;color:var(--text-secondary);max-width:400px;">${escapeHtml(r.evidence || '—')}</td>
  </tr>`).join('');
}

// S2 Batch Extraction


function renderS2RunsList() { renderStrategyRuns('s2'); }



// ============================================================
//  RING HELPERS & DASHBOARD VISUALS
// ============================================================

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

// Square canvas, sized in JS to match its CSS box times devicePixelRatio.
// Letting CSS stretch these is what turned the original gauges into ellipses.
function setupRingCanvas(canvas, size = 132, lineWidth = 10) {
  const dpr = window.devicePixelRatio || 1;
  canvas.width = size * dpr;
  canvas.height = size * dpr;
  canvas.style.width = size + 'px';
  canvas.style.height = size + 'px';
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, size, size);
  return { ctx, size, cx: size / 2, cy: size / 2, radius: size / 2 - lineWidth - 1, lineWidth };
}

function drawArcRing(ctx, cx, cy, radius, lineWidth, fraction, color) {
  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  ctx.strokeStyle = '#e5e7eb';
  ctx.lineWidth = lineWidth;
  ctx.stroke();
  if (fraction > 0) {
    ctx.beginPath();
    ctx.arc(cx, cy, radius, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * Math.min(fraction, 1));
    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'round';
    ctx.stroke();
  }
}

// One ring per parsing technology. The dashboard exists to compare parsers, so
// this replaced the old single "best result" card.
function renderParserRings() {
  const grid = document.getElementById('parser-ring-grid');
  const subtitle = document.getElementById('parser-rings-subtitle');
  if (!grid) return;

  const points = statsByParser().filter(p => p.accuracy !== null)
    .sort((a, b) => b.accuracy - a.accuracy);

  if (!points.length) {
    grid.innerHTML = '<div style="grid-column:1/-1;padding:24px;text-align:center;'
      + 'font-size:13px;color:var(--text-tertiary);">No scored runs yet</div>';
    return;
  }

  if (subtitle) {
    const n = points.reduce((a, p) => a + p.scored, 0);
    subtitle.textContent = `Mean exact accuracy per parser · ${n} scored runs`;
  }

  // Adapt to how many parsers there actually are. With four, the grid fills the
  // card so it matches the chart beside it. With one or two, the card shrinks
  // to its content instead of leaving a tall empty box.
  const n = points.length;
  grid.style.gridTemplateColumns = `repeat(${n === 1 ? 1 : 2}, minmax(0, 1fr))`;

  const fills = n >= 3;
  grid.style.gridAutoRows = fills ? '1fr' : 'max-content';
  grid.style.alignContent = fills ? 'stretch' : 'start';

  const card = grid.closest('.card');
  if (card) {
    card.style.alignSelf = fills ? 'stretch' : 'start';
    // A single parser means there is nothing to compare yet; say so rather
    // than leaving the reader wondering what the card is for.
    let hint = card.querySelector('.parser-ring-hint');
    if (n < 2) {
      if (!hint) {
        hint = document.createElement('div');
        hint.className = 'parser-ring-hint';
        card.appendChild(hint);
      }
      hint.textContent = 'Run Strategy 2 to compare this against the other parsing technologies.';
    } else if (hint) {
      hint.remove();
    }
  }

  grid.innerHTML = points.map(p => `
    <div class="parser-ring-card">
      <div class="parser-ring-wrap">
        <canvas id="parser-ring-${p.key}"></canvas>
        <div class="parser-ring-center">
          <span class="parser-ring-val" style="color:${seriesStyle(p.key).color};">${p.accuracy.toFixed(0)}%</span>
          <span class="parser-ring-sub">Accuracy</span>
        </div>
      </div>
      <div class="parser-ring-name" style="color:${seriesStyle(p.key).color};">${escapeHtml(p.name)}</div>
      <div class="parser-ring-meta">${p.parse !== null ? (p.parse < 10 ? p.parse.toFixed(1) : Math.round(p.parse)) + 's parse' : '—'} · n=${p.scored}</div>
    </div>`).join('');

  points.forEach(p => {
    const canvas = document.getElementById(`parser-ring-${p.key}`);
    if (!canvas) return;
    const r = setupRingCanvas(canvas, 104, 9);
    drawArcRing(r.ctx, r.cx, r.cy, r.radius, r.lineWidth, p.accuracy / 100, seriesStyle(p.key).color);
  });
}

// Relative parse speed. The multiple against the fastest is the headline claim,
// because parse time is deterministic — unlike the accuracy ranking, which at
// this sample size is not.
function renderSpeedBenchmark() {
  const host = document.getElementById('speed-bench');
  const subtitle = document.getElementById('speed-bench-subtitle');
  if (!host) return;

  const points = statsByParser().filter(p => p.parse !== null && p.parse > 0)
    .sort((a, b) => a.parse - b.parse);

  if (points.length < 2) {
    host.innerHTML = '<div style="padding:18px;text-align:center;font-size:13px;'
      + 'color:var(--text-tertiary);">Not enough measured parse times yet</div>';
    return;
  }

  const fastest = points[0];
  const slowest = points[points.length - 1];
  if (subtitle) {
    subtitle.textContent = `Relative time to convert one annual report to text — `
      + `${fastest.name} is ${(slowest.parse / fastest.parse).toFixed(0)}× faster than ${slowest.name}`;
  }

  host.innerHTML = points.map(p => {
    const style = seriesStyle(p.key);
    const ratio = p.parse / fastest.parse;
    // Log-scaled width: on a linear scale the fastest bar is an invisible
    // sliver next to one 90x slower.
    const width = Math.max(5, (Math.log10(ratio + 1) / Math.log10(slowest.parse / fastest.parse + 1)) * 100);
    return `
      <div class="speed-row">
        <span class="speed-name" style="color:${style.color};">${escapeHtml(p.name)}</span>
        <div class="speed-track">
          <div class="speed-fill" style="width:${width}%;background:${style.color};"></div>
        </div>
        <span class="speed-value">
          <strong>${p.parse < 10 ? p.parse.toFixed(1) : Math.round(p.parse)}s</strong>
          &nbsp;·&nbsp;${ratio < 1.05 ? 'fastest' : ratio.toFixed(1) + '\u00d7'}
        </span>
      </div>`;
  }).join('');
}

// Mini rings inside the accuracy and coverage stat cards.
function renderStatRings(latest) {
  const paint = (id, value, color) => {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    const r = setupRingCanvas(canvas, 48, 5);
    drawArcRing(r.ctx, r.cx, r.cy, r.radius, r.lineWidth, (Number(value) || 0) / 100, color);
  };
  paint('ring-accuracy', latest && latest.accuracy, '#16a34a');
  paint('ring-coverage', latest && latest.coverage, '#2563eb');
}

function renderDashboardCharts() {
  drawParserChart();
  renderParserRings();
  renderSpeedBenchmark();
  renderStatRings(allRuns.length ? allRuns[0] : null);
}

// ============================================================
//  RUN ACTIONS: EXPORT & DELETE
// ============================================================

function exportRunJson(runId) {
  fetch(`/api/runs/${encodeURIComponent(runId)}`)
    .then(r => r.json())
    .then(data => {
      if (data.error) { showToast(data.error, 'error'); return; }
      downloadBlob(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }),
                   `${runId}_prediction.json`);
      showToast(`Exported ${runId}_prediction.json`, 'success');
    })
    .catch(err => showToast(`Failed to export run: ${err.message}`, 'error'));
}

function deleteRun(runId) {
  if (!confirm(`Delete run "${runId}"? This permanently removes its logs and artifacts.`)) return;
  fetch(`/api/runs/${encodeURIComponent(runId)}`, { method: 'DELETE' })
    .then(r => r.json())
    .then(data => {
      if (!data.ok) throw new Error(data.error || 'Failed to delete run.');
      showToast(`Run "${runId}" deleted.`, 'success');
      if (lastResult && lastResult.run_id === runId) lastResult = null;
      loadRunHistory(true);
    })
    .catch(err => showToast(`Error deleting run: ${err.message}`, 'error'));
}

// Reset the whole experiment: every run directory and every artifact.
function deleteAllRuns() {
  if (allRuns.length === 0) { showToast('There are no runs to delete.', 'info'); return; }
  const typed = prompt(
    `This permanently deletes all ${allRuns.length} run(s) and their request/response artifacts.\n`
    + `Type DELETE to confirm.`);
  if (typed !== 'DELETE') { showToast('Cancelled — nothing was deleted.', 'info'); return; }

  fetch('/api/runs/all', { method: 'DELETE' })
    .then(r => r.json())
    .then(data => {
      if (!data.ok) throw new Error(data.error || 'Delete failed');
      lastResult = null;
      showToast(`Deleted ${data.deleted} run(s). Experiment reset.`, 'success');
      return loadRunHistory(false);
    })
    .then(() => { if (allRuns.length === 0) resetDashboardToEmptyState(); })
    .catch(err => showToast(`Failed to reset runs: ${err.message}`, 'error'));
}

// ============================================================
//  RUN TABLES
// ============================================================

// Shared cell fragments so every table reports a run identically.
function runCells(run) {
  const scored = run.accuracy !== undefined && run.accuracy !== null;
  const accVal = scored ? `${Number(run.accuracy).toFixed(1)}%` : '—';
  const accClass = !scored ? 'pending' : (run.accuracy >= 75 ? 'completed' : (run.accuracy >= 50 ? 'strategy' : 'error'));
  const covVal = (run.coverage !== undefined && run.coverage !== null) ? `${Number(run.coverage).toFixed(1)}%` : '—';
  const parseVal = (run.extract_seconds !== undefined && run.extract_seconds !== null)
    ? formatSeconds(run.extract_seconds) : '—';
  return { accVal, accClass, covVal, parseVal };
}

function runActions(runId) {
  const id = escapeHtml(runId);
  return `<div class="table-actions-group">
      <button class="table-action-btn" onclick="loadRunDetail('${id}', true)">View</button>
      <button class="table-action-btn export" onclick="exportRunJson('${id}')">Export</button>
      <button class="table-action-btn delete" onclick="deleteRun('${id}')">Delete</button>
    </div>`;
}

function strategyBadge(run) {
  const isS2 = runStrategy(run) === 's2';
  return isS2
    ? '<span class="table-badge strategy" style="background:#e0e7ff;color:#3730a3;">Strategy 2</span>'
    : '<span class="table-badge strategy">Strategy 1</span>';
}

function renderRunHistory(runs) {
  const container = document.getElementById('history-container');
  if (!container) return;

  if (!runs.length) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
        </div>
        <div style="font-size: 15px; font-weight: 600; color: var(--text-primary);">No experiment runs recorded</div>
        <div style="font-size: 13px; color: var(--text-tertiary); margin-top: 4px;">Run an extraction from Strategy 1 or Strategy 2 to populate history.</div>
      </div>`;
    return;
  }

  container.innerHTML = `
    <div class="table-wrapper">
      <table class="data-table">
        <thead><tr>
          <th>Run ID &amp; Timestamp</th><th>Strategy</th><th>Parser</th><th>Model</th><th>FY</th>
          <th>Accuracy</th><th>Coverage</th><th>Parse</th><th>Latency</th><th>Actions</th>
        </tr></thead>
        <tbody>
          ${runs.map(run => {
            const c = runCells(run);
            return `<tr>
              <td>
                <div style="display:flex;flex-direction:column;">
                  <strong style="font-family:var(--font-mono);font-size:13px;">${escapeHtml(run.run_id)}</strong>
                  <span style="font-size:11px;color:var(--text-tertiary);">${escapeHtml(formatTimestamp(run.timestamp))}</span>
                </div>
              </td>
              <td>${strategyBadge(run)}</td>
              <td>${parserChip(run)}</td>
              <td>${escapeHtml(run.model || '—')}</td>
              <td><strong>FY ${escapeHtml(run.detected_fiscal_year || run.fiscal_year || '—')}</strong></td>
              <td><span class="table-badge ${c.accClass}">${c.accVal}</span></td>
              <td><span class="table-badge completed">${c.covVal}</span></td>
              <td class="table-value">${c.parseVal}</td>
              <td class="table-value">${formatSeconds(run.api_elapsed)}</td>
              <td>${runActions(run.run_id)}</td>
            </tr>`;
          }).join('')}
        </tbody>
      </table>
    </div>`;
}

function renderDashboardRuns(runs) {
  const container = document.getElementById('dashboard-runs-container');
  if (!container) return;
  const recent = runs.slice(0, 8);

  if (!recent.length) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
        </div>
        <div style="font-size: 14px; color: var(--text-tertiary);">No extraction runs yet</div>
      </div>`;
    return;
  }

  container.innerHTML = `
    <div class="table-wrapper">
      <table class="data-table">
        <thead><tr>
          <th>Run ID</th><th>Strategy</th><th>Parser</th><th>FY</th>
          <th>Accuracy</th><th>Coverage</th><th>Parse</th><th>Latency</th><th>Actions</th>
        </tr></thead>
        <tbody>
          ${recent.map(run => {
            const c = runCells(run);
            return `<tr>
              <td><strong style="font-family:var(--font-mono);font-size:13px;">${escapeHtml(run.run_id)}</strong></td>
              <td>${strategyBadge(run)}</td>
              <td>${parserChip(run)}</td>
              <td><strong>FY ${escapeHtml(run.detected_fiscal_year || run.fiscal_year || '—')}</strong></td>
              <td><span class="table-badge ${c.accClass}">${c.accVal}</span></td>
              <td><span class="table-badge completed">${c.covVal}</span></td>
              <td class="table-value">${c.parseVal}</td>
              <td class="table-value">${formatSeconds(run.api_elapsed)}</td>
              <td>${runActions(run.run_id)}</td>
            </tr>`;
          }).join('')}
        </tbody>
      </table>
    </div>`;
}

// Shared body for the S1 / S2 accordion tables.
function renderStrategyRuns(strategyKey) {
  const isS2 = strategyKey === 's2';
  const container = document.getElementById(isS2 ? 's2-runs-list' : 's1-runs-list');
  const countEl = document.getElementById(isS2 ? 's2-runs-count' : 's1-runs-count');
  if (!container) return;

  const runs = allRuns.filter(r => runStrategy(r) === strategyKey);
  if (countEl) countEl.textContent = String(runs.length);

  // Open automatically the first time there is something to show; a manual
  // collapse sticks.
  const toggled = isS2 ? s2RunsToggledByUser : s1RunsToggledByUser;
  let expanded = isS2 ? s2RunsExpanded : s1RunsExpanded;
  if (!toggled && runs.length > 0 && !expanded) {
    expanded = true;
    if (isS2) s2RunsExpanded = true; else s1RunsExpanded = true;
    const textEl = document.getElementById(isS2 ? 's2-runs-toggle-text' : 's1-runs-toggle-text');
    if (textEl) textEl.textContent = 'Hide Runs';
  }
  container.style.display = expanded ? 'block' : 'none';

  if (!runs.length) {
    container.innerHTML = `<div style="padding:16px;font-size:13px;color:var(--text-tertiary);text-align:center;">
      No Strategy ${isS2 ? '2' : '1'} runs recorded yet.</div>`;
    return;
  }

  container.innerHTML = `
    <div class="table-wrapper">
      <table class="data-table">
        <thead><tr>
          <th>Run ID</th><th>Fiscal Year</th><th>Parser</th>
          <th>Accuracy</th><th>Coverage</th><th>Parse</th><th>Latency</th><th>Actions</th>
        </tr></thead>
        <tbody>
          ${runs.map(run => {
            const c = runCells(run);
            return `<tr>
              <td><strong style="font-family:var(--font-mono);font-size:13px;">${escapeHtml(run.run_id)}</strong></td>
              <td><strong>FY ${escapeHtml(run.detected_fiscal_year || run.fiscal_year || '—')}</strong></td>
              <td>${parserChip(run)}</td>
              <td><span class="table-badge ${c.accClass}">${c.accVal}</span></td>
              <td><span class="table-badge completed">${c.covVal}</span></td>
              <td class="table-value">${c.parseVal}</td>
              <td class="table-value">${formatSeconds(run.api_elapsed)}</td>
              <td>${runActions(run.run_id)}</td>
            </tr>`;
          }).join('')}
        </tbody>
      </table>
    </div>`;
}

function renderS1RunsList() { renderStrategyRuns('s1'); }

function toggleS1RunsList() {
  s1RunsToggledByUser = true;
  s1RunsExpanded = !s1RunsExpanded;
  const list = document.getElementById('s1-runs-list');
  const text = document.getElementById('s1-runs-toggle-text');
  if (list) list.style.display = s1RunsExpanded ? 'block' : 'none';
  if (text) text.textContent = s1RunsExpanded ? 'Hide Runs' : 'Show Runs';
}

function toggleS2RunsList() {
  s2RunsToggledByUser = true;
  s2RunsExpanded = !s2RunsExpanded;
  const list = document.getElementById('s2-runs-list');
  const text = document.getElementById('s2-runs-toggle-text');
  if (list) list.style.display = s2RunsExpanded ? 'block' : 'none';
  if (text) text.textContent = s2RunsExpanded ? 'Hide Runs' : 'Show Runs';
}

function formatTimestamp(ts) {
  if (!ts) return '';
  const m = String(ts).match(/(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z/);
  return m ? `${m[1]}-${m[2]}-${m[3]} ${m[4]}:${m[5]}:${m[6]} UTC` : ts;
}

// ============================================================
//  RUN HISTORY LOADING
// ============================================================

function loadRunHistory(autoLoadLatest = false) {
  return fetch('/api/runs')
    .then(r => r.json())
    .then(data => {
      allRuns = data.runs || [];
      renderRunHistory(allRuns);
      renderDashboardRuns(allRuns);
      renderS1RunsList();
      renderS2RunsList();
      updateDashboardStats();

      if (allRuns.length > 0) {
        const currentDeleted = lastResult && !allRuns.some(r => r.run_id === lastResult.run_id);
        if (autoLoadLatest || !lastResult || currentDeleted) loadRunDetail(allRuns[0].run_id, false);
      }
    })
    .catch(err => {
      showToast(`Failed to load run history: ${err.message}`, 'error');
      renderRunHistory([]);
      renderDashboardRuns([]);
      resetDashboardToEmptyState();
    });
}

function loadRunDetail(runId, shouldOpenTable = true) {
  return fetch(`/api/runs/${encodeURIComponent(runId)}`)
    .then(r => r.json())
    .then(data => {
      if (data.error) { showToast(data.error, 'error'); return; }
      lastResult = data;
      const isS2Run = runStrategy(data) === 's2';

      updateDashboardStats();
      // Render into the owning strategy's panel only, so the other panel never
      // shows a run it did not produce.
      if (isS2Run) { renderResultTableS2(data); renderEvidenceTableS2(data); }
      else { renderResultTable(data); renderEvidenceTable(data); }

      if (shouldOpenTable) {
        switchPanel(isS2Run ? 'strategy2' : 'strategy1');
        const el = document.getElementById(isS2Run ? 's2-inline-results' : 'inline-results');
        if (el) {
          el.style.display = 'block';
          setTimeout(() => el.scrollIntoView({ behavior: 'smooth', block: 'start' }), 150);
        }
        showToast(`Loaded run ${runId}`, 'info');
      }
    })
    .catch(err => showToast(`Failed to load run: ${err.message}`, 'error'));
}

// ============================================================
//  RESULT & EVIDENCE TABLES
// ============================================================

const SUBTOTAL_ITEMS = ['Current Assets', 'Quick Assets', 'Fixed Assets', 'Tangible Assets',
  'Financial Assets', 'Other Current Assets (subtotal)', 'Deferred Charges', 'Total Assets'];

// One renderer for both panels; the prefix picks the element ids.
function renderResultTableInto(prefix, data) {
  const tbody = document.getElementById(`${prefix}results-table-body`);
  if (!tbody) return;

  const rows = data.rows || [];
  const fy = String(data.detected_fiscal_year || data.fiscal_year || '').trim();
  const golden = getGoldenAnswers(fy);
  const scored = hasGoldenAnswers(fy);
  const stats = calculateAccuracy(rows, fy);

  const setEl = (id, html) => { const el = document.getElementById(id); if (el) el.innerHTML = html; };
  setEl(`${prefix}meta-run-id`, escapeHtml(data.run_id || '—'));
  setEl(`${prefix}meta-model`, escapeHtml(data.model || '—'));
  setEl(`${prefix}meta-fy`, `FY ${escapeHtml(fy || '—')}`);
  setEl(`${prefix}meta-accuracy`, scored
    ? `${miniPieSvg(stats.accuracy)} ${stats.accuracy}% (${stats.exact} / ${stats.total})`
    : 'Not scored — no answer key');
  setEl(`${prefix}meta-coverage`,
    `${miniPieSvg(stats.coverage, '#3b82f6')} ${stats.coverage}% (${stats.filled} / ${SCHEMA_ROW_COUNT})`);
  setEl(`${prefix}meta-tokens`, formatNumber(data.approx_input_tokens));
  setEl(`${prefix}meta-pages`, data.page_count ? String(data.page_count) : '—');
  setEl(`${prefix}meta-time`, formatSeconds(data.api_elapsed_seconds));

  const subtitle = document.getElementById(`${prefix}results-table-subtitle`);
  if (subtitle) {
    subtitle.textContent = scored
      ? `${SCHEMA_ROW_COUNT}-row fixed schema · Values in Millions USD ($M) · Compared with FY ${fy} golden answers`
      : `${SCHEMA_ROW_COUNT}-row fixed schema · Values in Millions USD ($M) · No golden answers stored for FY ${fy || '—'}`;
  }

  renderRunVerdicts(`${prefix}run-verdicts`, data);

  tbody.innerHTML = rows.map(row => {
    const expected = golden[row.item];
    const answered = isAnswered(row);
    const val = answered ? Number(row.answer_m_usd) : null;
    const conf = (row.confidence === undefined || row.confidence === null) ? 1.0 : Number(row.confidence);
    const match = isExactMatch(row, expected);

    let confBg = '#dcfce7', confColor = '#15803d';
    if (conf < CONFIDENCE_THRESHOLD) { confBg = '#fef3c7'; confColor = '#d97706'; }
    else if (conf < 0.9) { confBg = '#dbeafe'; confColor = '#1d4ed8'; }

    const evalBadge = !scored
      ? '<span class="table-badge" style="background:#f1f5f9;color:#475569;">Not scored</span>'
      : match
        ? '<span class="table-badge" style="background:#dcfce7;color:#15803d;">Exact Match</span>'
        : '<span class="table-badge" style="background:#fef3c7;color:#d97706;">Discrepancy</span>';

    return `<tr class="${SUBTOTAL_ITEMS.includes(row.item) ? 'subtotal' : ''}">
      <td>${escapeHtml(row.classification)}</td>
      <td>${escapeHtml(row.subclassification || '—')}</td>
      <td><strong>${escapeHtml(row.item)}</strong></td>
      <td style="text-align:right;"><span class="table-value ${val === null ? 'null' : (val < 0 ? 'negative' : '')}">${val === null ? '—' : formatDollarMillions(val)}</span></td>
      <td style="text-align:right;"><span class="table-value" style="color:var(--text-secondary);">${(expected !== undefined && expected !== null) ? formatDollarMillions(expected) : '—'}</span></td>
      <td style="text-align:center;"><span style="padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;background:${confBg};color:${confColor};">${Math.round(conf * 100)}%</span></td>
      <td style="text-align:center;">${evalBadge}</td>
    </tr>`;
  }).join('');
}

function renderResultTable(data) { renderResultTableInto('', data); }
function renderResultTableS2(data) { renderResultTableInto('s2-', data); }

function renderEvidenceTableInto(prefix, data) {
  const tbody = document.getElementById(`${prefix}evidence-table-body`);
  if (!tbody) return;
  tbody.innerHTML = (data.rows || []).map(r => `<tr>
      <td><strong>${escapeHtml(r.item)}</strong></td>
      <td class="table-value">${r.source_page !== null && r.source_page !== undefined ? r.source_page : '—'}</td>
      <td>${escapeHtml(r.source_label || '—')}</td>
      <td style="font-size:12px;color:var(--text-secondary);max-width:400px;">${escapeHtml(r.evidence || '—')}</td>
    </tr>`).join('');
}

function renderEvidenceTable(data) { renderEvidenceTableInto('', data); }

function closeResultsTableS2() {
  const el = document.getElementById('s2-inline-results');
  if (el) el.style.display = 'none';
  const zone = document.getElementById('s2-upload-zone');
  if (zone) zone.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function initEvidenceToggle() {
  [['evidence-toggle', 'evidence-card'], ['s2-evidence-toggle', 's2-evidence-card']].forEach(([tid, cid]) => {
    const toggle = document.getElementById(tid);
    const card = document.getElementById(cid);
    if (!toggle || !card) return;
    toggle.addEventListener('click', () => {
      const hidden = card.style.display === 'none' || !card.style.display;
      card.style.display = hidden ? 'block' : 'none';
      toggle.classList.toggle('open', hidden);
    });
  });
}

// ============================================================
//  DOWNLOADS
// ============================================================

function initDownloads() {
  const csv = document.getElementById('btn-download-csv');
  const json = document.getElementById('btn-download-json');
  if (csv) csv.addEventListener('click', downloadCSV);
  if (json) json.addEventListener('click', downloadJSON);
}

function quote(str) {
  return `"${String(str ?? '').replace(/"/g, '""')}"`;
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function downloadCSV() {
  if (!lastResult || !lastResult.rows) return;
  const fy = String(lastResult.detected_fiscal_year || lastResult.fiscal_year || '').trim();
  const golden = getGoldenAnswers(fy);
  const scored = hasGoldenAnswers(fy);
  const lines = [[
    'Classification', 'Subclassification', 'Item', 'Answer (M USD)',
    `FY ${fy || 'n/a'} Golden Answer (M USD)`, 'Confidence', 'Accepted', 'Evaluation'
  ].join(',')];

  lastResult.rows.forEach(r => {
    const exp = golden[r.item];
    // Same rule as the on-screen table and the server: no answer key means the
    // row is unscored, and an unaccepted value never counts as a match.
    const evaluation = !scored ? 'NOT_SCORED' : (isExactMatch(r, exp) ? 'MATCH' : 'DIFF');
    const conf = (r.confidence !== undefined && r.confidence !== null)
      ? Math.round(Number(r.confidence) * 100) + '%' : '100%';
    lines.push([
      quote(r.classification), quote(r.subclassification), quote(r.item),
      (r.answer_m_usd !== null && r.answer_m_usd !== undefined) ? r.answer_m_usd : '',
      (exp !== undefined && exp !== null) ? exp : '',
      conf, isAnswered(r) ? 'YES' : 'NO', evaluation
    ].join(','));
  });

  downloadBlob(new Blob([lines.join('\n')], { type: 'text/csv' }), `${lastResult.run_id}_prediction.csv`);
}

function downloadJSON() {
  if (!lastResult) return;
  downloadBlob(new Blob([JSON.stringify(lastResult, null, 2)], { type: 'application/json' }),
               `${lastResult.run_id}_prediction.json`);
}

// ============================================================
//  TARGET SCHEMA PANEL
// ============================================================

let benchmarkSchemaData = [];

function loadSchema() {
  const yearSelect = document.getElementById('schema-year-select');
  if (yearSelect && !yearSelect.dataset.initialized) {
    yearSelect.dataset.initialized = 'true';
    yearSelect.addEventListener('change', () => {
      renderSchemaTable(benchmarkSchemaData, yearSelect.value);
      renderSchemaPreview(benchmarkSchemaData, yearSelect.value);
    });
  }

  return fetch('/api/schema')
    .then(r => r.json())
    .then(schema => {
      benchmarkSchemaData = schema;
      const year = yearSelect ? yearSelect.value : '';
      renderSchemaTable(schema, year);
      renderSchemaPreview(schema, year);
    })
    .catch(() => {
      showToast('Could not load the target schema from the server.', 'error');
      benchmarkSchemaData = [];
      renderSchemaTable([], '');
      renderSchemaPreview([], '');
    });
}

function renderSchemaTable(schema, selectedYear = '') {
  const tbody = document.getElementById('schema-table-body');
  const thAnswer = document.getElementById('schema-th-answer');
  const showAnswers = Boolean(selectedYear);
  if (thAnswer) {
    // Default view is the target output format the assignment asks for. Golden
    // answers are an explicit opt-in, not something the benchmark shows by default.
    thAnswer.textContent = showAnswers ? `FY ${selectedYear} Golden Answer ($M)` : 'Expected Output';
  }
  if (!tbody) return;

  const golden = showAnswers ? getGoldenAnswers(selectedYear) : {};
  tbody.innerHTML = (schema || []).map((item, i) => {
    let val = null;
    if (showAnswers) {
      if (item.golden_answers && item.golden_answers[selectedYear] !== undefined && item.golden_answers[selectedYear] !== null) {
        val = item.golden_answers[selectedYear];
      } else if (golden[item.item] !== undefined) {
        val = golden[item.item];
      }
    }
    const answer = !showAnswers
      ? '<span style="color:var(--text-tertiary);font-family:var(--font-mono);font-size:11px;">number ($M) or null</span>'
      : (val !== null && val !== undefined)
        ? `<span class="table-value" style="color:var(--text-primary);font-weight:700;">${formatDollarMillions(val)}</span>`
        : '<span style="color:var(--text-tertiary);font-style:italic;font-size:11px;">No answer key</span>';

    const isSubtotal = SUBTOTAL_ITEMS.includes(item.item);
    return `<tr class="${isSubtotal ? 'subtotal' : ''}">
      <td style="color:var(--text-tertiary);font-family:var(--font-mono);font-size:11px;">${i + 1}</td>
      <td><div style="font-weight:600;color:var(--text-primary);">${escapeHtml(item.classification || '')}</div></td>
      <td><div style="color:var(--text-secondary);">${escapeHtml(item.subclassification || '—')}</div></td>
      <td><div style="font-weight:600;color:var(--text-primary);">${escapeHtml(item.item || '')}</div></td>
      <td><div style="font-size:12px;color:var(--text-secondary);line-height:1.4;">${escapeHtml(item.description || '')}</div></td>
      <td style="text-align:right;white-space:nowrap;">${answer}</td>
    </tr>`;
  }).join('');
}

function renderSchemaPreview(schema, selectedYear = '') {
  const container = document.getElementById('schema-preview');
  if (!container) return;

  const highlights = ['Current Assets', 'Fixed Assets', 'Deferred Charges', 'Total Assets']
    .map(name => (schema || []).find(s => s.item === name)).filter(Boolean);
  const iconMap = { 'Current Assets': 'current', 'Fixed Assets': 'fixed', 'Deferred Charges': 'deferred', 'Total Assets': 'total' };
  const abbrev = { 'Current Assets': 'CA', 'Fixed Assets': 'FA', 'Deferred Charges': 'DC', 'Total Assets': 'TA' };

  container.innerHTML = highlights.map(item => {
    let val = selectedYear ? getGoldenAnswers(selectedYear)[item.item] : undefined;
    if (selectedYear && (val === undefined || val === null) && item.golden_answers) val = item.golden_answers[selectedYear];
    const display = (val !== undefined && val !== null)
      ? formatDollarMillions(val)
      : '<span style="font-size:11px;font-weight:600;color:var(--text-tertiary);">$M or null</span>';
    return `
      <div class="schema-card">
        <div class="schema-card-top">
          <div class="schema-card-header-left">
            <div class="schema-card-icon ${iconMap[item.item] || 'current'}">${abbrev[item.item] || 'XX'}</div>
            <div><div class="schema-card-title">${escapeHtml(item.item)}</div></div>
          </div>
          <div class="schema-card-val">${display}</div>
        </div>
        <div class="schema-card-desc">${escapeHtml(item.description || '')}</div>
      </div>`;
  }).join('');
}

// ============================================================
//  STRATEGY 2 PANEL WIRING
// ============================================================

let s2PromptEditorExpanded = false;

function toggleS2PromptEditor() {
  s2PromptEditorExpanded = !s2PromptEditorExpanded;
  const body = document.getElementById('s2-prompt-editor-body');
  const text = document.getElementById('s2-prompt-toggle-text');
  if (body) body.style.display = s2PromptEditorExpanded ? 'block' : 'none';
  if (text) text.textContent = s2PromptEditorExpanded ? 'Collapse' : 'View / Edit Prompt';
}

function initS2UI() {
  const zone = document.getElementById('s2-upload-zone');
  const input = document.getElementById('s2-pdf-input');
  if (zone && input) {
    zone.addEventListener('click', e => { if (e.target.tagName !== 'INPUT') input.click(); });
    zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', e => {
      e.preventDefault(); zone.classList.remove('drag-over');
      if (e.dataTransfer.files.length) handleFilesSelected(Array.from(e.dataTransfer.files), 's2');
    });
    input.addEventListener('change', () => {
      if (input.files.length) handleFilesSelected(Array.from(input.files), 's2');
    });
  }

  const btnExtract = document.getElementById('btn-run-extract-s2');
  if (btnExtract) btnExtract.addEventListener('click', () => startRun('s2'));
  const btnBatch = document.getElementById('btn-run-batch-s2');
  if (btnBatch) btnBatch.addEventListener('click', () => startRun('s2'));

  const bindSlider = (sliderId, badgeId, fmt) => {
    const slider = document.getElementById(sliderId);
    const badge = document.getElementById(badgeId);
    if (slider && badge) slider.addEventListener('input', e => { badge.textContent = fmt(e.target.value); });
  };
  bindSlider('input-s2-temp', 's2-temp-badge', v => parseFloat(v).toFixed(2));
  bindSlider('input-s2-batch-concurrency', 's2-batch-concurrency-badge', v => v);

  const area = document.getElementById('input-s2-system-prompt');
  if (area) fetch('/api/prompt').then(r => r.json()).then(d => { area.value = d.system_prompt || ''; }).catch(() => {});

  const reset = document.getElementById('btn-reset-s2-prompt');
  if (reset) reset.addEventListener('click', () => {
    fetch('/api/prompt').then(r => r.json()).then(d => {
      const a = document.getElementById('input-s2-system-prompt');
      if (a) a.value = d.default_prompt || d.system_prompt || '';
      showToast('Prompt reset to default.', 'success');
    });
  });

  const save = document.getElementById('btn-save-s2-prompt');
  if (save) save.addEventListener('click', () => {
    const a = document.getElementById('input-s2-system-prompt');
    if (!a) return;
    fetch('/api/prompt', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ system_prompt: a.value })
    }).then(() => showToast('System prompt saved.', 'success'))
      .catch(() => showToast('Failed to save prompt.', 'error'));
  });
}

// ============================================================
//  EXECUTION: STAGING, STREAMING, ANIMATION
// ============================================================

// Stage the files server-side once, get back a token estimate and a recommended
// concurrency, and show it before anything is spent.
async function stageAndPreflight(strategy) {
  const ids = execIds(strategy);
  const concurrencyEl = document.getElementById(ids.concurrency);
  const form = new FormData();
  selectedFiles.forEach(f => form.append('pdfs', f));
  form.append('concurrency', concurrencyEl ? concurrencyEl.value : '5');

  const response = await fetch('/api/uploads', { method: 'POST', body: form });
  const data = await response.json();
  if (!response.ok || !data.ok) throw new Error(data.error || 'Upload failed');
  renderPreflight(strategy, data);
  return data;
}

// Parses an SSE body incrementally. EventSource cannot be used because this is
// a POST with a JSON body.
async function consumeEventStream(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let split;
    while ((split = buffer.indexOf('\n\n')) !== -1) {
      const chunk = buffer.slice(0, split);
      buffer = buffer.slice(split + 2);
      let event = 'message';
      const dataLines = [];
      chunk.split('\n').forEach(line => {
        if (line.startsWith('event:')) event = line.slice(6).trim();
        else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
      });
      if (!dataLines.length) continue;   // keep-alive comment
      try { onEvent(event, JSON.parse(dataLines.join('\n'))); }
      catch (err) { console.warn('Unparseable SSE payload', err); }
    }
  }
}

async function startRun(strategy) {
  if (selectedFiles.length === 0 || !hasApiKey || activeRun) return;
  activeRun = true;

  const ids = execIds(strategy);
  const runBtn = document.getElementById(ids.runBtn);
  const batchBtn = document.getElementById(ids.batchBtn);
  const buttons = [runBtn, batchBtn].filter(Boolean);
  const labels = buttons.map(b => b.innerHTML);
  buttons.forEach(b => { b.disabled = true; b.innerHTML = '<span class="spinner"></span> Running…'; });

  const started = Date.now();
  let succeeded = 0, failed = 0, firstResultRunId = null, passPlan = [];
  const fileOutcomes = {};
  let ticker = null;
  bakeoffResults = [];
  const bakeoffCard = document.getElementById('s2-bakeoff-card');
  if (bakeoffCard && strategy === 's2') bakeoffCard.style.display = 'none';

  renderExecFiles(strategy, selectedFiles.map((f, i) => ({ name: f.name, index: i })));
  execSetHeader(strategy, 'Staging', 'in-progress', '');

  try {
    if (strategy === 's2' && selectedExtractors().length === 0) {
      throw new Error('Select at least one extraction technology to compare.');
    }

    const staged = await stageAndPreflight(strategy);
    const usable = (staged.files || []).filter(f => !f.error);
    if (usable.length === 0) throw new Error('No readable PDFs in the selection.');

    execSetHeader(strategy, 'Running', 'in-progress',
      `<span>${usable.length} file(s) · concurrency ${staged.plan.recommended_concurrency}</span>`
      + `<span id="${ids.summary}-elapsed">0s elapsed</span>`);

    ticker = setInterval(() => {
      const el = document.getElementById(`${ids.summary}-elapsed`);
      if (el) el.textContent = `${Math.round((Date.now() - started) / 1000)}s elapsed`;
    }, 1000);

    const readValue = (id, fallback) => {
      const el = document.getElementById(id);
      return el ? el.value : fallback;
    };

    const response = await fetch('/api/extract/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        upload_ids: usable.map(f => f.id),
        ...(strategy === 's2' ? { strategies: selectedExtractors() } : { strategy }),
        concurrency: staged.plan.recommended_concurrency,
        enable_reasoning: readValue(ids.reasoning, 'true'),
        temperature: readValue(ids.temp, '0.1'),
        system_prompt: String(readValue(ids.prompt, '')).trim() || undefined
      })
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.error || `Run failed (HTTP ${response.status})`);
    }

    await consumeEventStream(response, (event, payload) => {
      if (event === 'batch_start') {
        // One row per PDF, however many technologies each is run through; the
        // row's parser label changes as the passes proceed.
        passPlan = (payload.strategies || []).map(s => s.key);
        renderExecFiles(strategy, (payload.files || []).map(f => ({
          name: f.name, pages: f.pages, approx_tokens: f.approx_tokens,
          index: f.index, passes: passPlan
        })));

      } else if (event === 'pass_start') {
        execSetCardState(strategy, payload.index, 'running');
        execSetPass(strategy, payload.index, payload.strategy, passPlan);
        execSetStatus(strategy, payload.index, shortExtractorName(payload.strategy),
          `${payload.pages} pages · ~${formatNumber(payload.approx_tokens)} est. tokens`);
        execMarkStep(strategy, payload.index, 'upload', 'active');

      } else if (event === 'progress') {
        execMarkStep(strategy, payload.index, payload.step,
          payload.throttled ? 'throttled' : (payload.done ? 'done' : 'active'));
        const stepLabel = payload.step === 'extract'
          ? shortExtractorName(payload.strategy || strategy)
          : (PIPELINE_STEPS.find(st => st.key === payload.step) || {}).short || payload.step;
        execSetStatus(strategy, payload.index, payload.throttled ? 'Rate limited' : stepLabel, payload.message);

      } else if (event === 'file_done') {
        bakeoffResults.push(payload);
        const outcome = fileOutcomes[payload.index] || (fileOutcomes[payload.index] = { ok: 0, failed: 0 });
        payload.ok ? outcome.ok++ : outcome.failed++;
        if (strategy === 's2') renderBakeoff();          // grows as results land
        if (payload.ok) {
          succeeded++;
          firstResultRunId = firstResultRunId || payload.run_id;
          PIPELINE_STEPS.forEach(st => execMarkStep(strategy, payload.index, st.key, 'done'));
          execMarkPassDone(strategy, payload.index, payload.strategy, true);
          const acc = (payload.metrics && payload.metrics.accuracy !== null && payload.metrics.accuracy !== undefined)
            ? `${payload.metrics.accuracy}% accuracy` : 'not scored';
          const warned = (payload.warnings && payload.warnings.length) ? ` · ${payload.warnings.length} warning(s)` : '';
          execSetStatus(strategy, payload.index,
            `FY ${payload.fiscal_year || '—'} · ${formatSeconds(payload.api_elapsed_seconds)}`,
            `${acc} · ${payload.metrics ? payload.metrics.coverage : 0}% coverage · ${payload.page_count} pages${warned}`);
          loadRunHistory(false);
        } else {
          failed++;
          execMarkPassDone(strategy, payload.index, payload.strategy, false);
          execSetCardState(strategy, payload.index, 'failed');
          execSetStatus(strategy, payload.index, 'Failed', payload.error);
        }

      } else if (event === 'quota_exhausted') {
        // Not a throttle: the account's allowance is spent. Say so once, loudly,
        // instead of letting every remaining file report its own failure.
        execSetHeader(strategy, 'Quota exhausted', 'error',
          `<span>${escapeHtml(payload.message)}</span><span>Remaining files skipped</span>`);
        showToast(payload.message, 'error');
      } else if (event === 'file_complete') {
        execFreezeRow(strategy, payload.index);
        // The row is "done" only if every pass for that file succeeded.
        const outcome = fileOutcomes[payload.index] || { ok: 0, failed: 0 };
        execSetCardState(strategy, payload.index, outcome.failed ? 'failed' : 'done');
        if (outcome.failed) {
          execSetStatus(strategy, payload.index, `${outcome.ok} ok · ${outcome.failed} failed`, undefined);
        }

      } else if (event === 'batch_done') {
        if (ticker) clearInterval(ticker);
        document.querySelectorAll(`#${ids.files} .exec-file`)
          .forEach((_, idx) => execFreezeRow(strategy, idx));
        const throttles = payload.rate_limit ? payload.rate_limit.throttle_events : 0;
        execSetHeader(strategy, failed ? 'Completed with errors' : 'Completed',
          failed ? 'error' : 'completed',
          `<span>${succeeded} succeeded · ${failed} failed</span>`
          + `<span>${Math.round((Date.now() - started) / 1000)}s total`
          + `${throttles ? ` · ${throttles} rate-limit backoff(s)` : ''}</span>`);
        loadRunHistory(false);
      }
    });

    if (ticker) clearInterval(ticker);
    showToast(`${strategy === 's2' ? 'Strategy 2' : 'Strategy 1'}: ${succeeded} succeeded, ${failed} failed.`,
              failed ? 'error' : 'success');

    await loadRunHistory(false);
    if (firstResultRunId) loadRunDetail(firstResultRunId, true);

  } catch (err) {
    if (ticker) clearInterval(ticker);
    execSetHeader(strategy, 'Failed', 'error', `<span>${escapeHtml(err.message)}</span>`);
    showToast(err.message, 'error');
  } finally {
    activeRun = false;
    buttons.forEach((b, i) => { b.innerHTML = labels[i]; });
    updateExtractButton(strategy);
  }
}

async function runExtraction() { return startRun('s1'); }
async function runBatchExtraction() { return startRun('s1'); }
async function runExtractionS2() { return startRun('s2'); }
async function runBatchExtractionS2() { return startRun('s2'); }
