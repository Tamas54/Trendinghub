/**
 * TrendMaster Extension - Popup Script
 */

document.addEventListener('DOMContentLoaded', async () => {
  // DOM elemek
  const statusIndicator = document.getElementById('statusIndicator');
  const statusText = statusIndicator.querySelector('.status-text');
  const apiKeyInput = document.getElementById('apiKey');
  const toggleApiKeyBtn = document.getElementById('toggleApiKey');
  const toggleAgentBtn = document.getElementById('toggleAgent');
  const platformItems = document.querySelectorAll('.platform-item');
  const openOptionsLink = document.getElementById('openOptions');
  
  // Stat elemek
  const tasksCompletedEl = document.getElementById('tasksCompleted');
  const tasksFailedEl = document.getElementById('tasksFailed');
  const lastPollEl = document.getElementById('lastPoll');
  
  // Platform státusz elemek
  const platformStatusEls = {
    facebook: document.getElementById('fb-status'),
    instagram: document.getElementById('ig-status'),
    twitter: document.getElementById('tw-status')
  };
  
  /**
   * Állapot frissítése a UI-on
   */
  function updateUI(state) {
    // Futás státusz
    if (state.isRunning) {
      statusIndicator.classList.add('running');
      statusText.textContent = 'Fut - Várakozás...';
      toggleAgentBtn.classList.add('running');
      toggleAgentBtn.querySelector('.btn-icon').textContent = '⏹️';
      toggleAgentBtn.querySelector('.btn-text').textContent = 'LEÁLLÍTÁS';
    } else {
      statusIndicator.classList.remove('running');
      statusText.textContent = 'Leállítva';
      toggleAgentBtn.classList.remove('running');
      toggleAgentBtn.querySelector('.btn-icon').textContent = '▶️';
      toggleAgentBtn.querySelector('.btn-text').textContent = 'INDÍTÁS';
    }
    
    // API kulcs
    if (state.apiKey) {
      apiKeyInput.value = state.apiKey;
    }
    
    // Aktív platformok
    platformItems.forEach(item => {
      const platform = item.dataset.platform;
      if (state.activePlatforms?.includes(platform)) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });
    
    // Statisztikák
    if (state.stats) {
      tasksCompletedEl.textContent = state.stats.tasksCompleted || 0;
      tasksFailedEl.textContent = state.stats.tasksFailed || 0;
    }
    
    // Utolsó poll
    if (state.lastPoll) {
      const ago = Math.round((Date.now() - state.lastPoll) / 1000);
      lastPollEl.textContent = `${ago}s`;
    }
  }
  
  /**
   * Platform login státusz ellenőrzése
   */
  async function checkPlatformLogins() {
    for (const platform of ['facebook', 'instagram', 'twitter']) {
      const result = await chrome.runtime.sendMessage({
        type: 'CHECK_LOGIN',
        platform
      });
      
      const statusEl = platformStatusEls[platform];
      if (result?.loggedIn) {
        statusEl.textContent = '🟢';
        statusEl.classList.add('logged-in');
      } else {
        statusEl.textContent = '⚫';
        statusEl.classList.remove('logged-in');
      }
    }
  }
  
  /**
   * Kezdeti állapot betöltése
   */
  async function loadState() {
    const state = await chrome.runtime.sendMessage({ type: 'GET_STATE' });
    updateUI(state);
    await checkPlatformLogins();
  }
  
  // API kulcs megjelenítés toggle
  toggleApiKeyBtn.addEventListener('click', () => {
    if (apiKeyInput.type === 'password') {
      apiKeyInput.type = 'text';
      toggleApiKeyBtn.textContent = '🙈';
    } else {
      apiKeyInput.type = 'password';
      toggleApiKeyBtn.textContent = '👁️';
    }
  });
  
  // API kulcs mentése
  apiKeyInput.addEventListener('change', async () => {
    await chrome.runtime.sendMessage({
      type: 'SET_API_KEY',
      apiKey: apiKeyInput.value.trim()
    });
  });
  
  // Platform kiválasztás
  platformItems.forEach(item => {
    item.addEventListener('click', async () => {
      item.classList.toggle('active');
      
      const activePlatforms = Array.from(platformItems)
        .filter(el => el.classList.contains('active'))
        .map(el => el.dataset.platform);
      
      await chrome.runtime.sendMessage({
        type: 'SET_PLATFORMS',
        platforms: activePlatforms
      });
    });
  });
  
  // Agent indítás/leállítás
  toggleAgentBtn.addEventListener('click', async () => {
    const state = await chrome.runtime.sendMessage({ type: 'GET_STATE' });
    
    if (!state.apiKey) {
      alert('Kérlek add meg az API kulcsot!');
      return;
    }
    
    if (!state.activePlatforms?.length) {
      alert('Válassz ki legalább egy platformot!');
      return;
    }
    
    if (state.isRunning) {
      await chrome.runtime.sendMessage({ type: 'STOP_AGENT' });
    } else {
      await chrome.runtime.sendMessage({ type: 'START_AGENT' });
    }
  });
  
  // Options megnyitása
  openOptionsLink.addEventListener('click', (e) => {
    e.preventDefault();
    chrome.runtime.openOptionsPage();
  });
  
  // Állapot frissítések figyelése
  chrome.runtime.onMessage.addListener((message) => {
    if (message.type === 'STATE_UPDATE') {
      updateUI(message.state);
    }
  });
  
  // Periodikus frissítés (minden másodpercben)
  setInterval(async () => {
    const state = await chrome.runtime.sendMessage({ type: 'GET_STATE' });
    updateUI(state);
  }, 1000);
  
  // Induláskor betöltés
  await loadState();
});
