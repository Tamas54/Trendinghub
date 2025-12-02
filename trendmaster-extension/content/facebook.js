/**
 * TrendMaster - Facebook Content Script
 * Facebook-specifikus automatizáció kép feltöltéssel és story támogatással
 */

(() => {
  const Utils = window.TrendMasterUtils;

  // Facebook szelektorok (robusztus, több alternatíva)
  const SELECTORS = {
    // Poszt létrehozás trigger
    createPostTrigger: [
      'aria:Mi jár a fejedben',
      'aria:What\'s on your mind',
      'aria:Create a post',
      'aria:Bejegyzés létrehozása',
      '[role="button"][tabindex="0"] span:first-child',
      'div[role="button"]:has(span)'
    ],

    // Poszt szerkesztő (dialógusban)
    postEditor: [
      '[role="textbox"][contenteditable="true"][data-lexical-editor="true"]',
      '[role="textbox"][aria-label*="Mi jár"]',
      '[role="textbox"][aria-label*="What\'s on your mind"]',
      'div[contenteditable="true"][role="textbox"]',
      'div[aria-label*="fejedben"][contenteditable="true"]'
    ],

    // Fotó/Videó gomb a poszt dialógusban
    photoVideoButton: [
      '[aria-label="Fotó/videó"]',
      '[aria-label="Photo/video"]',
      '[aria-label*="Fotó"][aria-label*="videó"]',
      '[aria-label*="Photo"][aria-label*="video"]',
      'div[role="button"] svg[viewBox="0 0 24 24"]',
      'aria:Fénykép vagy videó hozzáadása'
    ],

    // File input a kép feltöltéshez
    fileInput: [
      'input[type="file"][accept*="image"]',
      'input[type="file"][accept*="video"]',
      'input[type="file"][multiple]',
      'input[type="file"]'
    ],

    // Kép preview ellenőrzés
    imagePreview: [
      'img[src*="blob:"]',
      'div[data-visualcompletion="media-vc-image"]',
      'img[alt=""]',
      'div[style*="background-image"]'
    ],

    // Közzététel gomb
    postButton: [
      'aria:Közzététel',
      'aria:Post',
      '[aria-label="Közzététel"]',
      '[aria-label="Post"]',
      'div[role="button"]:has(span:contains("Közzététel"))',
      'div[role="button"]:has(span:contains("Post"))'
    ],

    // Like gomb
    likeButton: [
      '[aria-label*="Tetszik"]',
      '[aria-label*="Like"]',
      'div[aria-label="Like"]',
      'div[aria-label="Tetszik"]'
    ],

    // Komment mező
    commentBox: [
      '[aria-label*="Írj hozzászólást"]',
      '[aria-label*="Write a comment"]',
      'div[contenteditable="true"][aria-label*="comment"]',
      'div[contenteditable="true"][aria-label*="hozzászólás"]'
    ],

    // Story létrehozás
    storyButton: [
      'aria:Történet létrehozása',
      'aria:Create story',
      'aria:Történet hozzáadása',
      'aria:Add to story',
      '[aria-label*="Történet"]',
      '[aria-label*="Story"]'
    ],

    // Story szerkesztő
    storyEditor: [
      'div[data-pagelet="StoriesCreation"]',
      '[aria-label*="Add text"]',
      '[aria-label*="Szöveg hozzáadása"]'
    ],

    // Story megosztás gomb
    shareStoryButton: [
      'aria:Megosztás a történetben',
      'aria:Share to story',
      'aria:Megosztás',
      '[aria-label*="Share"][role="button"]'
    ]
  };

  /**
   * Facebook poszt létrehozás képpel
   */
  async function createPost(content) {
    console.log('[TrendMaster/FB] Poszt létrehozás kezdés...');

    try {
      // 1. Poszt trigger megnyitása
      const trigger = await Utils.findElement(SELECTORS.createPostTrigger);
      if (!trigger) {
        throw new Error('Poszt trigger nem található');
      }

      await Utils.humanClick(trigger);
      await Utils.delay(1500, 2500);

      // 2. Szerkesztő mező megkeresése
      const editor = await Utils.findElement(SELECTORS.postEditor);
      if (!editor) {
        throw new Error('Szerkesztő mező nem található');
      }

      // 3. Ha van kép, először feltöltjük
      if (content.media_urls && content.media_urls.length > 0) {
        console.log('[TrendMaster/FB] Képek feltöltése...');
        await uploadImages(content.media_urls);
        await Utils.delay(1000, 2000);
      }

      // 4. Szöveg beírása
      if (content.text) {
        const sanitizedText = Utils.sanitizeText(content.text);
        await Utils.humanClick(editor);
        await Utils.delay(500, 1000);
        await Utils.humanType(editor, sanitizedText);
      }

      await Utils.delay(1500, 2500);

      // 5. Közzététel gomb megnyomása
      const postBtn = await Utils.findElement(SELECTORS.postButton);
      if (!postBtn) {
        throw new Error('Közzététel gomb nem található');
      }

      await Utils.humanClick(postBtn);
      await Utils.delay(3000, 5000);

      console.log('[TrendMaster/FB] Poszt létrehozva!');
      return { success: true };

    } catch (error) {
      console.error('[TrendMaster/FB] Poszt hiba:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Képek feltöltése a poszthoz
   */
  async function uploadImages(imageUrls) {
    console.log('[TrendMaster/FB] Képek feltöltése:', imageUrls.length, 'db');

    try {
      // Fotó/Videó gomb megnyomása
      const photoBtn = await Utils.findElement(SELECTORS.photoVideoButton, 5000);

      if (photoBtn) {
        // Kattintással nyitjuk meg
        await Utils.humanClick(photoBtn);
        await Utils.delay(1000, 1500);
      }

      // File input keresése
      await Utils.delay(500, 1000);

      for (let i = 0; i < imageUrls.length; i++) {
        const imageUrl = imageUrls[i];
        console.log(`[TrendMaster/FB] Kép ${i + 1}/${imageUrls.length} feltöltése...`);

        try {
          // Kép letöltése
          const file = await Utils.fetchImageAsFile(imageUrl, `fb_image_${i + 1}`);

          // File input keresése és beállítása
          const fileInputs = document.querySelectorAll('input[type="file"]');
          let fileInput = null;

          // Az utolsó (legújabb) file input-ot használjuk
          for (const input of fileInputs) {
            if (input.accept && (input.accept.includes('image') || input.accept.includes('video') || input.accept.includes('*'))) {
              fileInput = input;
            }
          }

          if (!fileInput && fileInputs.length > 0) {
            fileInput = fileInputs[fileInputs.length - 1];
          }

          if (fileInput) {
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);
            fileInput.files = dataTransfer.files;
            fileInput.dispatchEvent(new Event('change', { bubbles: true }));

            console.log(`[TrendMaster/FB] Kép ${i + 1} kiválasztva`);
          } else {
            console.warn('[TrendMaster/FB] File input nem található, próbálom drag & drop-pal');

            // Alternatív: drag & drop a szerkesztőre
            const editor = await Utils.findElement(SELECTORS.postEditor, 3000);
            if (editor) {
              await Utils.simulateDrop(editor, file);
            }
          }

          // Várakozás a kép feldolgozására
          await Utils.waitForImagePreview(SELECTORS.imagePreview, 10000);
          await Utils.delay(1000, 2000);

        } catch (imgError) {
          console.error(`[TrendMaster/FB] Kép ${i + 1} feltöltési hiba:`, imgError);
        }
      }

      console.log('[TrendMaster/FB] Képek feltöltve');
      return true;

    } catch (error) {
      console.error('[TrendMaster/FB] Kép feltöltési hiba:', error);
      throw error;
    }
  }

  /**
   * Facebook Story létrehozás
   */
  async function createStory(content) {
    console.log('[TrendMaster/FB] Story létrehozás kezdés...');

    try {
      // 1. Story gomb keresése és megnyomása
      const storyBtn = await Utils.findElement(SELECTORS.storyButton);
      if (!storyBtn) {
        // Próbáljuk a story URL-t direktben
        window.location.href = 'https://www.facebook.com/stories/create';
        await Utils.delay(3000, 4000);
      } else {
        await Utils.humanClick(storyBtn);
        await Utils.delay(2000, 3000);
      }

      // 2. Ha van kép, feltöltjük
      if (content.media_urls && content.media_urls.length > 0) {
        const imageUrl = content.media_urls[0]; // Story-hoz 1 kép
        console.log('[TrendMaster/FB] Story kép feltöltése...');

        const file = await Utils.fetchImageAsFile(imageUrl, 'story_image');

        // File input keresése a story creator-ban
        await Utils.delay(1000, 2000);
        const fileInputs = document.querySelectorAll('input[type="file"]');

        if (fileInputs.length > 0) {
          const fileInput = fileInputs[fileInputs.length - 1];
          const dataTransfer = new DataTransfer();
          dataTransfer.items.add(file);
          fileInput.files = dataTransfer.files;
          fileInput.dispatchEvent(new Event('change', { bubbles: true }));

          await Utils.delay(2000, 3000);
        }
      }

      // 3. Ha van szöveg, hozzáadjuk
      if (content.text) {
        // Szöveg hozzáadás gomb keresése
        const textBtn = await Utils.findElement([
          'aria:Szöveg hozzáadása',
          'aria:Add text',
          '[aria-label*="text"]'
        ], 5000);

        if (textBtn) {
          await Utils.humanClick(textBtn);
          await Utils.delay(500, 1000);

          // Szöveg mező kitöltése
          const textInput = await Utils.findElement([
            'div[contenteditable="true"]',
            'textarea',
            'input[type="text"]'
          ], 3000);

          if (textInput) {
            await Utils.humanType(textInput, Utils.sanitizeText(content.text));
            await Utils.delay(500, 1000);

            // Kattintás a szerkesztőn kívülre a szöveg rögzítéséhez
            document.body.click();
            await Utils.delay(500, 1000);
          }
        }
      }

      // 4. Megosztás gomb megnyomása
      await Utils.delay(1000, 2000);
      const shareBtn = await Utils.findElement(SELECTORS.shareStoryButton, 10000);

      if (!shareBtn) {
        throw new Error('Story megosztás gomb nem található');
      }

      await Utils.humanClick(shareBtn);
      await Utils.delay(3000, 5000);

      console.log('[TrendMaster/FB] Story létrehozva!');
      return { success: true };

    } catch (error) {
      console.error('[TrendMaster/FB] Story hiba:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Like végrehajtása
   */
  async function performLike(targetUrl) {
    console.log('[TrendMaster/FB] Like kezdés...');

    try {
      if (targetUrl && !window.location.href.includes(targetUrl)) {
        window.location.href = targetUrl;
        await Utils.delay(3000, 5000);
      }

      const likeBtn = await Utils.findElement(SELECTORS.likeButton);
      if (!likeBtn) {
        throw new Error('Like gomb nem található');
      }

      // Ellenőrizzük, nincs-e már like-olva
      const isLiked = likeBtn.getAttribute('aria-pressed') === 'true' ||
                      likeBtn.classList.contains('liked');

      if (isLiked) {
        console.log('[TrendMaster/FB] Már like-olva van');
        return { success: true };
      }

      await Utils.humanClick(likeBtn);
      await Utils.delay(1000, 2000);

      console.log('[TrendMaster/FB] Like végrehajtva!');
      return { success: true };

    } catch (error) {
      console.error('[TrendMaster/FB] Like hiba:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Komment írása
   */
  async function writeComment(content, targetUrl) {
    console.log('[TrendMaster/FB] Komment kezdés...');

    try {
      if (targetUrl && !window.location.href.includes(targetUrl)) {
        window.location.href = targetUrl;
        await Utils.delay(3000, 5000);
      }

      const commentBox = await Utils.findElement(SELECTORS.commentBox);
      if (!commentBox) {
        throw new Error('Komment mező nem található');
      }

      await Utils.humanClick(commentBox);
      await Utils.delay(500, 1000);

      const sanitizedText = Utils.sanitizeText(content.text);
      await Utils.humanType(commentBox, sanitizedText);

      await Utils.delay(500, 1000);

      // Enter küldése
      commentBox.dispatchEvent(new KeyboardEvent('keydown', {
        key: 'Enter',
        code: 'Enter',
        bubbles: true
      }));

      await Utils.delay(2000, 3000);

      console.log('[TrendMaster/FB] Komment elküldve!');
      return { success: true };

    } catch (error) {
      console.error('[TrendMaster/FB] Komment hiba:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Megosztás
   */
  async function performShare(targetUrl) {
    console.log('[TrendMaster/FB] Megosztás kezdés...');

    try {
      if (targetUrl) {
        window.location.href = targetUrl;
        await Utils.delay(3000, 5000);
      }

      // Share gomb keresése
      const shareBtn = await Utils.findElement([
        '[aria-label*="Megosztás"]',
        '[aria-label*="Share"]',
        'div[aria-label="Send this to friends or post it on your profile."]'
      ]);

      if (!shareBtn) {
        throw new Error('Megosztás gomb nem található');
      }

      await Utils.humanClick(shareBtn);
      await Utils.delay(1000, 2000);

      // "Megosztás most" opció keresése
      const shareNowBtn = await Utils.findElement([
        'aria:Megosztás most',
        'aria:Share now',
        'text:Megosztás most',
        'text:Share now'
      ], 5000);

      if (shareNowBtn) {
        await Utils.humanClick(shareNowBtn);
        await Utils.delay(2000, 3000);
      }

      console.log('[TrendMaster/FB] Megosztva!');
      return { success: true };

    } catch (error) {
      console.error('[TrendMaster/FB] Megosztás hiba:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Task handler
   */
  async function handleTask(task) {
    console.log('[TrendMaster/FB] Task fogadva:', task.task_type);

    const content = task.content || { text: '', media_urls: [] };

    switch (task.task_type.toLowerCase()) {
      case 'post':
        return await createPost(content);

      case 'story':
        return await createStory(content);

      case 'like':
        return await performLike(task.target_url);

      case 'comment':
        return await writeComment(content, task.target_url);

      case 'share':
        return await performShare(task.target_url);

      default:
        return { success: false, error: `Ismeretlen task típus: ${task.task_type}` };
    }
  }

  // ═══════════════════════════════════════════════════════════════════
  // MESSAGE LISTENER
  // ═══════════════════════════════════════════════════════════════════

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'EXECUTE_TASK' && message.task?.platform === 'facebook') {
      handleTask(message.task).then(result => {
        sendResponse(result);
      });
      return true; // Async response
    }
  });

  console.log('[TrendMaster] Facebook content script betöltve (v2 - image & story support)');

})();
