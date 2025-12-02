/**
 * TrendMaster Extension - Options Page Script
 */

const DEFAULT_SETTINGS = {
  serverUrl: 'http://localhost:5000',
  apiKey: '',
  pollInterval: 1,
  enableNotifications: true,
  enableJitter: true,
  autoStart: false,
  debugMode: false
};

// DOM Elements
const serverUrlInput = document.getElementById('serverUrl');
const apiKeyInput = document.getElementById('apiKey');
const pollIntervalSelect = document.getElementById('pollInterval');
const enableNotificationsCheckbox = document.getElementById('enableNotifications');
const enableJitterCheckbox = document.getElementById('enableJitter');
const autoStartCheckbox = document.getElementById('autoStart');
const debugModeCheckbox = document.getElementById('debugMode');
const saveBtn = document.getElementById('saveBtn');
const resetBtn = document.getElementById('resetBtn');
const statusMessage = document.getElementById('statusMessage');
const serverDot = document.getElementById('serverDot');
const serverStatusText = document.getElementById('serverStatusText');

/**
 * Load settings from storage
 */
async function loadSettings() {
  const result = await chrome.storage.local.get('settings');
  const settings = { ...DEFAULT_SETTINGS, ...result.settings };

  serverUrlInput.value = settings.serverUrl;
  apiKeyInput.value = settings.apiKey;
  pollIntervalSelect.value = settings.pollInterval.toString();
  enableNotificationsCheckbox.checked = settings.enableNotifications;
  enableJitterCheckbox.checked = settings.enableJitter;
  autoStartCheckbox.checked = settings.autoStart;
  debugModeCheckbox.checked = settings.debugMode;

  // Check server status
  checkServerStatus(settings.serverUrl);
}

/**
 * Save settings to storage
 */
async function saveSettings() {
  const settings = {
    serverUrl: serverUrlInput.value.trim(),
    apiKey: apiKeyInput.value.trim(),
    pollInterval: parseFloat(pollIntervalSelect.value),
    enableNotifications: enableNotificationsCheckbox.checked,
    enableJitter: enableJitterCheckbox.checked,
    autoStart: autoStartCheckbox.checked,
    debugMode: debugModeCheckbox.checked
  };

  await chrome.storage.local.set({ settings });

  // Notify background script
  await chrome.runtime.sendMessage({
    type: 'SETTINGS_UPDATED',
    settings
  });

  showStatus('Beállítások mentve!', 'success');
  checkServerStatus(settings.serverUrl);
}

/**
 * Reset to defaults
 */
async function resetSettings() {
  if (!confirm('Biztosan visszaállítod az alapértelmezett beállításokat?')) {
    return;
  }

  await chrome.storage.local.set({ settings: DEFAULT_SETTINGS });
  await loadSettings();
  showStatus('Alapértelmezett beállítások visszaállítva', 'success');
}

/**
 * Check server status
 */
async function checkServerStatus(url) {
  if (!url) {
    serverDot.className = 'dot offline';
    serverStatusText.textContent = 'Nincs URL megadva';
    return;
  }

  serverDot.className = 'dot';
  serverStatusText.textContent = 'Ellenőrzés...';

  try {
    const response = await fetch(`${url}/api/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000)
    });

    if (response.ok) {
      serverDot.className = 'dot online';
      serverStatusText.textContent = 'Szerver elérhető';
    } else {
      serverDot.className = 'dot offline';
      serverStatusText.textContent = `Hiba: ${response.status}`;
    }
  } catch (error) {
    serverDot.className = 'dot offline';
    serverStatusText.textContent = 'Szerver nem elérhető';
  }
}

/**
 * Show status message
 */
function showStatus(message, type) {
  statusMessage.textContent = message;
  statusMessage.className = `status-message ${type}`;

  setTimeout(() => {
    statusMessage.className = 'status-message';
  }, 3000);
}

// Event listeners
saveBtn.addEventListener('click', saveSettings);
resetBtn.addEventListener('click', resetSettings);

serverUrlInput.addEventListener('blur', () => {
  checkServerStatus(serverUrlInput.value.trim());
});

// Initial load
document.addEventListener('DOMContentLoaded', loadSettings);
