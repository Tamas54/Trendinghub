/**
 * TrendMaster - Common Content Script Utilities
 * Megosztott funkciók minden platform content script-jéhez
 */

// ═══════════════════════════════════════════════════════════════════
// EMBERI VISELKEDÉS SZIMULÁCIÓ
// ═══════════════════════════════════════════════════════════════════

const TrendMasterUtils = {
  
  /**
   * Véletlenszerű késleltetés (emberi viselkedés)
   */
  async delay(minMs = 500, maxMs = 2000) {
    const ms = Math.random() * (maxMs - minMs) + minMs;
    return new Promise(resolve => setTimeout(resolve, ms));
  },
  
  /**
   * Emberi gépelés szimuláció
   */
  async humanType(element, text, options = {}) {
    const { minDelay = 30, maxDelay = 100, mistakeChance = 0.03 } = options;
    
    element.focus();
    await this.delay(200, 500);
    
    for (let i = 0; i < text.length; i++) {
      const char = text[i];
      
      // Véletlenszerű elütés és javítás
      if (Math.random() < mistakeChance && text.length > 10) {
        const wrongChar = 'abcdefghijklmnop'[Math.floor(Math.random() * 16)];
        await this.typeChar(element, wrongChar);
        await this.delay(100, 200);
        document.execCommand('delete', false, null);
        await this.delay(50, 150);
      }
      
      await this.typeChar(element, char);
      await this.delay(minDelay, maxDelay);
    }
  },
  
  /**
   * Egyetlen karakter beírása
   */
  async typeChar(element, char) {
    // Input event szimulálása
    const inputEvent = new InputEvent('input', {
      bubbles: true,
      cancelable: true,
      inputType: 'insertText',
      data: char
    });
    
    // React/Vue kompatibilitás - native value setter
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype, 'value'
    )?.set || Object.getOwnPropertyDescriptor(
      window.HTMLTextAreaElement.prototype, 'value'
    )?.set;
    
    if (element.isContentEditable) {
      // ContentEditable elemekhez
      document.execCommand('insertText', false, char);
    } else if (nativeInputValueSetter) {
      // Input/Textarea elemekhez (React kompatibilis)
      nativeInputValueSetter.call(element, element.value + char);
      element.dispatchEvent(inputEvent);
    } else {
      element.value += char;
      element.dispatchEvent(inputEvent);
    }
  },
  
  /**
   * Elem keresése több szelektorral (fallback rendszer)
   */
  async findElement(selectors, timeout = 10000) {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
      for (const selector of selectors) {
        try {
          // Próbáljuk CSS szelektorként
          let element = document.querySelector(selector);
          
          // Ha nincs, próbáljuk XPath-ként (ha /-vel kezdődik)
          if (!element && selector.startsWith('/')) {
            const result = document.evaluate(
              selector, document, null, 
              XPathResult.FIRST_ORDERED_NODE_TYPE, null
            );
            element = result.singleNodeValue;
          }
          
          // Aria-label alapú keresés
          if (!element && selector.startsWith('aria:')) {
            const label = selector.replace('aria:', '');
            element = document.querySelector(`[aria-label*="${label}"]`);
          }
          
          // Text alapú keresés
          if (!element && selector.startsWith('text:')) {
            const text = selector.replace('text:', '');
            const xpath = `//*[contains(text(), "${text}")]`;
            const result = document.evaluate(
              xpath, document, null,
              XPathResult.FIRST_ORDERED_NODE_TYPE, null
            );
            element = result.singleNodeValue;
          }
          
          if (element && this.isVisible(element)) {
            return element;
          }
        } catch (e) {
          // Szelektor hiba, próbáljuk a következőt
        }
      }
      
      // Kis várakozás és újrapróbálás
      await this.delay(200, 300);
    }
    
    return null;
  },
  
  /**
   * Elem láthatóság ellenőrzése
   */
  isVisible(element) {
    if (!element) return false;
    
    const style = window.getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    
    return (
      style.display !== 'none' &&
      style.visibility !== 'hidden' &&
      style.opacity !== '0' &&
      rect.width > 0 &&
      rect.height > 0
    );
  },
  
  /**
   * Emberi kattintás szimuláció
   */
  async humanClick(element) {
    if (!element) {
      throw new Error('Nincs elem a kattintáshoz');
    }
    
    // Scroll into view
    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    await this.delay(300, 600);
    
    // Mouse events szimuláció
    const rect = element.getBoundingClientRect();
    const x = rect.left + rect.width / 2 + (Math.random() - 0.5) * 10;
    const y = rect.top + rect.height / 2 + (Math.random() - 0.5) * 10;
    
    const events = ['mouseenter', 'mouseover', 'mousedown', 'mouseup', 'click'];
    
    for (const eventType of events) {
      const event = new MouseEvent(eventType, {
        bubbles: true,
        cancelable: true,
        view: window,
        clientX: x,
        clientY: y
      });
      element.dispatchEvent(event);
      await this.delay(10, 30);
    }
    
    await this.delay(100, 300);
  },
  
  /**
   * Oldal betöltés várakozás
   */
  async waitForPageLoad(timeout = 30000) {
    return new Promise((resolve, reject) => {
      if (document.readyState === 'complete') {
        resolve();
        return;
      }
      
      const timer = setTimeout(() => {
        reject(new Error('Page load timeout'));
      }, timeout);
      
      window.addEventListener('load', () => {
        clearTimeout(timer);
        resolve();
      }, { once: true });
    });
  },
  
  /**
   * Biztonságos szöveg (XSS védelem)
   */
  sanitizeText(text) {
    return text
      .replace(/<script[^>]*>.*?<\/script>/gi, '')
      .replace(/javascript:/gi, '')
      .replace(/on\w+\s*=/gi, '')
      .trim();
  },
  
  /**
   * Eredmény küldése a background script-nek
   */
  async sendResult(taskId, success, error = null) {
    await chrome.runtime.sendMessage({
      type: 'TASK_RESULT',
      taskId,
      success,
      error
    });
  },

  // ═══════════════════════════════════════════════════════════════════
  // KÉP KEZELÉS
  // ═══════════════════════════════════════════════════════════════════

  /**
   * Kép letöltése URL-ről és File objektummá alakítása
   */
  async fetchImageAsFile(imageUrl, filename = 'image.jpg') {
    try {
      console.log('[TrendMaster] Kép letöltése:', imageUrl);

      const response = await fetch(imageUrl);
      if (!response.ok) {
        throw new Error(`Kép letöltés sikertelen: ${response.status}`);
      }

      const blob = await response.blob();
      const mimeType = blob.type || 'image/jpeg';
      const extension = mimeType.split('/')[1] || 'jpg';
      const finalFilename = filename.includes('.') ? filename : `${filename}.${extension}`;

      return new File([blob], finalFilename, { type: mimeType });
    } catch (error) {
      console.error('[TrendMaster] Kép letöltési hiba:', error);
      throw error;
    }
  },

  /**
   * File input elem keresése és fájl beállítása
   */
  async setFileInput(selectors, file) {
    const fileInput = await this.findElement(selectors, 5000);

    if (!fileInput) {
      throw new Error('File input nem található');
    }

    // DataTransfer használata a fájl beállításához
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    fileInput.files = dataTransfer.files;

    // Events triggerelése
    fileInput.dispatchEvent(new Event('change', { bubbles: true }));
    fileInput.dispatchEvent(new Event('input', { bubbles: true }));

    console.log('[TrendMaster] Fájl beállítva:', file.name);
    return true;
  },

  /**
   * Kép feltöltés drag & drop szimulációval
   */
  async simulateDrop(targetElement, file) {
    if (!targetElement || !file) {
      throw new Error('Target element vagy file hiányzik');
    }

    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);

    const events = ['dragenter', 'dragover', 'drop'];

    for (const eventType of events) {
      const event = new DragEvent(eventType, {
        bubbles: true,
        cancelable: true,
        dataTransfer: dataTransfer
      });
      targetElement.dispatchEvent(event);
      await this.delay(100, 200);
    }

    console.log('[TrendMaster] Drop szimuláció kész');
    return true;
  },

  /**
   * Várakozás kép feltöltés befejezésére (preview megjelenése)
   */
  async waitForImagePreview(previewSelectors, timeout = 15000) {
    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      for (const selector of previewSelectors) {
        try {
          const elements = document.querySelectorAll(selector);
          if (elements.length > 0) {
            console.log('[TrendMaster] Kép preview megjelent');
            return true;
          }
        } catch (e) {}
      }
      await this.delay(500, 800);
    }

    console.warn('[TrendMaster] Kép preview nem jelent meg időben');
    return false;
  },

  /**
   * Több kép feltöltése egymás után
   */
  async uploadMultipleImages(imageUrls, uploadFunction) {
    const results = [];

    for (let i = 0; i < imageUrls.length; i++) {
      try {
        const file = await this.fetchImageAsFile(imageUrls[i], `image_${i + 1}`);
        const result = await uploadFunction(file);
        results.push({ success: true, index: i });
        await this.delay(1000, 2000);
      } catch (error) {
        results.push({ success: false, index: i, error: error.message });
      }
    }

    return results;
  },

  /**
   * Clipboard-ra kép másolása és beillesztés
   */
  async pasteImageFromClipboard(file, targetElement) {
    try {
      // ClipboardItem létrehozása
      const clipboardItem = new ClipboardItem({
        [file.type]: file
      });

      await navigator.clipboard.write([clipboardItem]);

      // Paste event szimulálása
      targetElement.focus();
      await this.delay(200, 400);

      const pasteEvent = new ClipboardEvent('paste', {
        bubbles: true,
        cancelable: true,
        clipboardData: new DataTransfer()
      });

      targetElement.dispatchEvent(pasteEvent);

      // Ctrl+V szimuláció
      document.execCommand('paste');

      return true;
    } catch (error) {
      console.warn('[TrendMaster] Clipboard paste nem sikerült:', error);
      return false;
    }
  }
};

// Globálisan elérhetővé tesszük
window.TrendMasterUtils = TrendMasterUtils;

console.log('[TrendMaster] Common utilities betöltve (v2 - image support)');
