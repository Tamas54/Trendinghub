/**
 * TrendMaster Extension - Service Worker (Background)
 * Manifest V3 kompatibilis
 * 
 * Felelősségek:
 * - Szerver polling (alarms API)
 * - Task elosztás a content script-eknek
 * - Állapot kezelés
 */

// ═══════════════════════════════════════════════════════════════════
// KONFIGURÁCIÓ
// ═══════════════════════════════════════════════════════════════════

const CONFIG = {
  SERVER_URL: 'http://localhost:5000',  // Lokális fejlesztéshez
  POLL_ALARM_NAME: 'trendmaster-poll',
  POLL_INTERVAL_MINUTES: 0.5, // 30 másodperc (minimum az alarms API-ban)
  JITTER_ENABLED: true,
  VERSION: '1.0.0'
};

// Platform URL mapping
const PLATFORM_URLS = {
  facebook: 'https://www.facebook.com',
  instagram: 'https://www.instagram.com',
  twitter: 'https://twitter.com'
};

// ═══════════════════════════════════════════════════════════════════
// ÁLLAPOT KEZELÉS
// ═══════════════════════════════════════════════════════════════════

/**
 * Alapértelmezett állapot
 */
const DEFAULT_STATE = {
  isRunning: false,
  apiKey: '',
  agentId: '',  // Backend agent ID
  agentName: 'TrendMaster Extension',
  activePlatforms: [],
  lastPoll: null,
  lastTask: null,
  taskQueue: [],
  stats: {
    tasksCompleted: 0,
    tasksFailed: 0,
    lastError: null
  }
};

/**
 * Állapot betöltése storage-ból
 */
async function getState() {
  const result = await chrome.storage.local.get('state');
  return { ...DEFAULT_STATE, ...result.state };
}

/**
 * Állapot mentése
 */
async function setState(updates) {
  const current = await getState();
  const newState = { ...current, ...updates };
  await chrome.storage.local.set({ state: newState });
  return newState;
}

/**
 * Broadcast állapot változás a popup-nak
 */
async function broadcastState() {
  const state = await getState();
  chrome.runtime.sendMessage({ type: 'STATE_UPDATE', state }).catch(() => {
    // Popup nincs nyitva, nem baj
  });
}

// ═══════════════════════════════════════════════════════════════════
// SZERVER KOMMUNIKÁCIÓ
// ═══════════════════════════════════════════════════════════════════

/**
 * Settings betöltése (options page-ből)
 */
async function getSettings() {
  const result = await chrome.storage.local.get('settings');
  return result.settings || { serverUrl: CONFIG.SERVER_URL };
}

/**
 * API hívás wrapper
 */
async function apiCall(endpoint, data = {}, requireAuth = true) {
  const state = await getState();
  const settings = await getSettings();

  // Szerver URL a settings-ből vagy fallback CONFIG-ra
  const serverUrl = settings.serverUrl || CONFIG.SERVER_URL;

  if (requireAuth && !state.apiKey) {
    throw new Error('Nincs API kulcs beállítva');
  }

  const headers = {
    'Content-Type': 'application/json',
    'X-Client-Version': CONFIG.VERSION,
    'X-Client-Type': 'extension'
  };

  // API key header-ben is küldjük (backend így várja)
  if (state.apiKey) {
    headers['X-API-Key'] = state.apiKey;
  }

  console.log(`[TrendMaster] API call: ${serverUrl}${endpoint}`);

  const response = await fetch(`${serverUrl}${endpoint}`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      api_key: state.apiKey,
      ...data
    })
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API hiba: ${response.status} - ${errorText}`);
  }

  return response.json();
}

/**
 * Agent regisztráció a backend-en
 */
async function registerAgent() {
  const state = await getState();

  if (!state.apiKey) {
    throw new Error('Nincs API kulcs beállítva');
  }

  try {
    const result = await apiCall('/api/agent/register', {
      name: state.agentName || 'TrendMaster Extension',
      hwid_hash: 'extension_' + Date.now(), // Extension-nél nincs HWID
      version: CONFIG.VERSION,
      capabilities: state.activePlatforms
    });

    if (result.success && result.agent_id) {
      await setState({ agentId: result.agent_id });
      console.log('[TrendMaster] Agent regisztrálva:', result.agent_id);
      return result.agent_id;
    } else {
      throw new Error(result.error || 'Agent regisztráció sikertelen');
    }
  } catch (error) {
    console.error('[TrendMaster] Agent regisztráció hiba:', error);
    throw error;
  }
}

/**
 * Task lekérése a szervertől
 */
async function fetchTask() {
  const state = await getState();

  if (!state.isRunning || !state.apiKey) {
    return null;
  }

  // Ha nincs agent ID, regisztráljuk
  if (!state.agentId) {
    try {
      await registerAgent();
    } catch (error) {
      console.error('[TrendMaster] Agent regisztráció sikertelen:', error);
      return null;
    }
  }

  const currentState = await getState();

  try {
    const data = await apiCall('/api/agent/get-task', {
      agent_id: currentState.agentId,
      platforms: currentState.activePlatforms,
      version: CONFIG.VERSION
    });

    await setState({ lastPoll: Date.now() });

    if (data.has_task && data.task) {
      console.log('[TrendMaster] Új task érkezett:', data.task.id);

      // Backend task formátum átalakítása extension formátumra
      const task = {
        id: data.task.id,
        platform: data.task.platform,
        task_type: data.task.task_type,
        target_url: data.task.target_url,
        content: {
          text: data.task.content || '',
          media_urls: data.task.media_urls || []
        }
      };

      return task;
    }

    return null;
  } catch (error) {
    console.error('[TrendMaster] Polling hiba:', error);
    await setState({
      stats: {
        ...(await getState()).stats,
        lastError: error.message
      }
    });
    return null;
  }
}

/**
 * Task státusz jelentése
 */
async function reportTaskStatus(taskId, status, errorMessage = '') {
  const state = await getState();

  try {
    await apiCall('/api/agent/task-status', {
      agent_id: state.agentId,
      task_id: taskId,
      status,
      error: errorMessage || null,
      result: status === 'completed' ? 'Task executed by extension' : null
    });

    const stats = { ...state.stats };

    if (status === 'completed') {
      stats.tasksCompleted++;
    } else if (status === 'failed') {
      stats.tasksFailed++;
      stats.lastError = errorMessage;
    }

    await setState({ stats, lastTask: { id: taskId, status, time: Date.now() } });
    await broadcastState();

  } catch (error) {
    console.error('[TrendMaster] Státusz jelentési hiba:', error);
  }
}

// ═══════════════════════════════════════════════════════════════════
// TASK VÉGREHAJTÁS
// ═══════════════════════════════════════════════════════════════════

/**
 * Task validálás (biztonsági szűrés)
 */
function validateTask(task) {
  const ALLOWED_TYPES = ['post', 'like', 'comment', 'share', 'story'];
  const ALLOWED_PLATFORMS = ['facebook', 'instagram', 'twitter'];
  const MAX_CONTENT_LENGTH = 5000;
  
  if (!task || typeof task !== 'object') {
    return { valid: false, reason: 'Invalid task object' };
  }
  
  if (!task.id || typeof task.id !== 'string') {
    return { valid: false, reason: 'Missing task ID' };
  }
  
  if (!ALLOWED_PLATFORMS.includes(task.platform?.toLowerCase())) {
    return { valid: false, reason: `Invalid platform: ${task.platform}` };
  }
  
  if (!ALLOWED_TYPES.includes(task.task_type?.toLowerCase())) {
    return { valid: false, reason: `Invalid task type: ${task.task_type}` };
  }
  
  if (task.content?.text && task.content.text.length > MAX_CONTENT_LENGTH) {
    return { valid: false, reason: 'Content too long' };
  }
  
  // XSS szűrés
  if (task.content?.text) {
    const dangerous = /<script|javascript:|on\w+\s*=/i;
    if (dangerous.test(task.content.text)) {
      return { valid: false, reason: 'Suspicious content detected' };
    }
  }
  
  return { valid: true };
}

/**
 * Task végrehajtása - megkeresi/megnyitja a megfelelő tabot
 */
async function executeTask(task) {
  const validation = validateTask(task);
  
  if (!validation.valid) {
    console.warn('[TrendMaster] Task elutasítva:', validation.reason);
    await reportTaskStatus(task.id, 'rejected', validation.reason);
    return;
  }
  
  const platform = task.platform.toLowerCase();
  const baseUrl = PLATFORM_URLS[platform];
  
  if (!baseUrl) {
    await reportTaskStatus(task.id, 'failed', 'Unknown platform');
    return;
  }
  
  try {
    // Keresünk már nyitott tabot
    const tabs = await chrome.tabs.query({ url: `${baseUrl}/*` });
    let targetTab;
    
    if (tabs.length > 0) {
      // Van már nyitott tab
      targetTab = tabs[0];
      await chrome.tabs.update(targetTab.id, { active: true });
    } else {
      // Új tab nyitása
      targetTab = await chrome.tabs.create({ url: baseUrl, active: false });
      
      // Várunk amíg betölt
      await new Promise(resolve => {
        const listener = (tabId, info) => {
          if (tabId === targetTab.id && info.status === 'complete') {
            chrome.tabs.onUpdated.removeListener(listener);
            resolve();
          }
        };
        chrome.tabs.onUpdated.addListener(listener);
      });
      
      // Kis várakozás az oldal renderelésére
      await new Promise(r => setTimeout(r, 2000));
    }
    
    // Task küldése a content script-nek
    const response = await chrome.tabs.sendMessage(targetTab.id, {
      type: 'EXECUTE_TASK',
      task
    });
    
    if (response?.success) {
      await reportTaskStatus(task.id, 'completed');
      showNotification('Task kész', `${platform} - ${task.task_type}`);
    } else {
      await reportTaskStatus(task.id, 'failed', response?.error || 'Unknown error');
    }
    
  } catch (error) {
    console.error('[TrendMaster] Task végrehajtási hiba:', error);
    await reportTaskStatus(task.id, 'failed', error.message);
  }
}

// ═══════════════════════════════════════════════════════════════════
// POLLING RENDSZER (Alarms API)
// ═══════════════════════════════════════════════════════════════════

/**
 * Polling indítása
 */
async function startPolling() {
  // Töröljük a meglévő alarm-ot
  await chrome.alarms.clear(CONFIG.POLL_ALARM_NAME);
  
  // Új alarm létrehozása
  chrome.alarms.create(CONFIG.POLL_ALARM_NAME, {
    delayInMinutes: 0.1, // Első poll gyorsan
    periodInMinutes: CONFIG.POLL_INTERVAL_MINUTES
  });
  
  console.log('[TrendMaster] Polling elindítva');
}

/**
 * Polling leállítása
 */
async function stopPolling() {
  await chrome.alarms.clear(CONFIG.POLL_ALARM_NAME);
  console.log('[TrendMaster] Polling leállítva');
}

/**
 * Alarm handler
 */
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name !== CONFIG.POLL_ALARM_NAME) return;
  
  const state = await getState();
  if (!state.isRunning) {
    await stopPolling();
    return;
  }
  
  // Jitter - véletlenszerű késleltetés (0-5 sec)
  if (CONFIG.JITTER_ENABLED) {
    const jitter = Math.random() * 5000;
    await new Promise(r => setTimeout(r, jitter));
  }
  
  const task = await fetchTask();
  
  if (task) {
    await executeTask(task);
  }
  
  await broadcastState();
});

// ═══════════════════════════════════════════════════════════════════
// NOTIFICATION
// ═══════════════════════════════════════════════════════════════════

function showNotification(title, message) {
  chrome.notifications.create({
    type: 'basic',
    iconUrl: 'icons/icon128.png',
    title: `TrendMaster: ${title}`,
    message
  });
}

// ═══════════════════════════════════════════════════════════════════
// MESSAGE HANDLING (Popup ↔ Background)
// ═══════════════════════════════════════════════════════════════════

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handleMessage(message, sender).then(sendResponse);
  return true; // Async response
});

async function handleMessage(message, sender) {
  switch (message.type) {

    case 'GET_STATE':
      return await getState();

    case 'SET_API_KEY':
      await setState({ apiKey: message.apiKey });
      return { success: true };

    case 'SET_PLATFORMS':
      await setState({ activePlatforms: message.platforms });
      return { success: true };

    case 'SETTINGS_UPDATED':
      // Options page-ről jön - szinkronizáljuk a state-tel
      if (message.settings) {
        const updates = {};
        if (message.settings.apiKey) {
          updates.apiKey = message.settings.apiKey;
        }
        if (Object.keys(updates).length > 0) {
          await setState(updates);
        }
        console.log('[TrendMaster] Settings frissítve:', message.settings.serverUrl);
      }
      return { success: true };

    case 'START_AGENT':
      await setState({ isRunning: true });
      await startPolling();
      await broadcastState();
      showNotification('Agent elindítva', 'Várakozás feladatokra...');
      return { success: true };
    
    case 'STOP_AGENT':
      await setState({ isRunning: false });
      await stopPolling();
      await broadcastState();
      showNotification('Agent leállítva', '');
      return { success: true };
    
    case 'TASK_RESULT':
      // Content script-től jön vissza
      if (message.taskId) {
        await reportTaskStatus(
          message.taskId, 
          message.success ? 'completed' : 'failed',
          message.error || ''
        );
      }
      return { success: true };
    
    case 'CHECK_LOGIN':
      // Ellenőrizzük, be van-e jelentkezve a user az adott platformra
      return await checkPlatformLogin(message.platform);
    
    default:
      console.warn('[TrendMaster] Ismeretlen üzenet:', message.type);
      return { error: 'Unknown message type' };
  }
}

/**
 * Platform login ellenőrzése (cookie alapján)
 */
async function checkPlatformLogin(platform) {
  const cookieNames = {
    facebook: 'c_user',
    instagram: 'sessionid',
    twitter: 'auth_token'
  };
  
  const cookieName = cookieNames[platform];
  const url = PLATFORM_URLS[platform];
  
  if (!cookieName || !url) {
    return { loggedIn: false };
  }
  
  try {
    const cookie = await chrome.cookies.get({ url, name: cookieName });
    return { loggedIn: !!cookie };
  } catch {
    return { loggedIn: false };
  }
}

// ═══════════════════════════════════════════════════════════════════
// INICIALIZÁLÁS
// ═══════════════════════════════════════════════════════════════════

chrome.runtime.onInstalled.addListener(async (details) => {
  console.log('[TrendMaster] Extension telepítve:', details.reason);
  
  // Alapállapot inicializálása
  await setState(DEFAULT_STATE);
  
  if (details.reason === 'install') {
    // Első telepítéskor megnyitjuk az options oldalt
    chrome.runtime.openOptionsPage();
  }
});

// Service worker "wake up" kezelése
chrome.runtime.onStartup.addListener(async () => {
  console.log('[TrendMaster] Service worker elindult');
  
  const state = await getState();
  if (state.isRunning) {
    await startPolling();
  }
});

console.log('[TrendMaster] Service Worker betöltve');
