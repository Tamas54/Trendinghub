/**
 * TrendMaster - Instagram Content Script
 * Instagram-specifikus automatizáció kép feltöltéssel és story támogatással
 */

(() => {
  const Utils = window.TrendMasterUtils;

  const SELECTORS = {
    // Új poszt gomb
    newPostButton: [
      'aria:Új bejegyzés',
      'aria:New post',
      'aria:Create',
      'aria:Létrehozás',
      'svg[aria-label="New post"]',
      'svg[aria-label="Új bejegyzés"]',
      '[aria-label="Létrehozás"]',
      '[aria-label="Create"]'
    ],

    // Story gomb
    storyButton: [
      'aria:Történet',
      'aria:Story',
      'aria:Your story',
      'aria:Saját történet',
      '[aria-label*="story" i]',
      '[aria-label*="történet" i]',
      'div[role="button"]:has(span:contains("Your story"))'
    ],

    // Add to Story opció a létrehozás menüben
    addToStoryOption: [
      'text:Történet',
      'text:Story',
      'aria:Add to story',
      'aria:Hozzáadás a történethez'
    ],

    // File input
    fileInput: [
      'input[type="file"][accept*="image"]',
      'input[type="file"][accept*="video"]',
      'input[type="file"]'
    ],

    // Következő gomb (poszt létrehozás flow)
    nextButton: [
      'aria:Következő',
      'aria:Next',
      'text:Következő',
      'text:Next',
      'button:has-text("Next")',
      'div[role="button"]:has-text("Következő")'
    ],

    // Caption/Felirat mező
    captionInput: [
      'aria:Írj feliratot...',
      'aria:Write a caption...',
      'textarea[aria-label*="caption" i]',
      'textarea[aria-label*="felirat" i]',
      'div[aria-label*="caption" i][contenteditable="true"]'
    ],

    // Megosztás gomb
    shareButton: [
      'aria:Megosztás',
      'aria:Share',
      'text:Megosztás',
      'text:Share',
      'button:has-text("Share")',
      'div[role="button"]:has-text("Megosztás")'
    ],

    // Like gomb
    likeButton: [
      'svg[aria-label="Tetszik"]',
      'svg[aria-label="Like"]',
      '[aria-label="Tetszik"]',
      '[aria-label="Like"]',
      'span[class*="like"]'
    ],

    // Unlike gomb (már like-olva)
    unlikeButton: [
      'svg[aria-label="Már nem tetszik"]',
      'svg[aria-label="Unlike"]',
      '[aria-label="Már nem tetszik"]',
      '[aria-label="Unlike"]'
    ],

    // Komment mező
    commentBox: [
      'textarea[aria-label*="Hozzászólás"]',
      'textarea[aria-label*="Add a comment"]',
      'textarea[placeholder*="Hozzászólás"]',
      'textarea[placeholder*="Add a comment"]',
      'form textarea'
    ],

    // Komment küldés gomb
    postCommentButton: [
      'text:Közzététel',
      'text:Post',
      'button:has-text("Post")',
      'div[role="button"]:has-text("Közzététel")'
    ],

    // Story szerkesztő elemek
    storyTextButton: [
      'aria:Szöveg',
      'aria:Text',
      'button[aria-label*="Text"]'
    ],

    // Story megosztás
    shareStoryButton: [
      'aria:Megosztás a történetben',
      'aria:Share to your story',
      'aria:Your story',
      'text:Your story',
      'text:Saját történet'
    ],

    // Kép preview
    imagePreview: [
      'img[src*="blob:"]',
      'img[alt="Preview"]',
      'div[style*="background-image"]',
      'video[src*="blob:"]'
    ]
  };

  /**
   * Instagram poszt létrehozás képpel
   */
  async function createPost(content) {
    console.log('[TrendMaster/IG] Poszt létrehozás kezdés...');

    try {
      // Ellenőrizzük, van-e kép - Instagram-on kötelező
      if (!content.media_urls || content.media_urls.length === 0) {
        throw new Error('Instagram poszthoz kép szükséges');
      }

      // 1. Új poszt gomb megnyomása
      const newPostBtn = await Utils.findElement(SELECTORS.newPostButton, 5000);

      if (newPostBtn) {
        await Utils.humanClick(newPostBtn);
        await Utils.delay(1500, 2500);
      } else {
        // Alternatív: direkt URL
        window.location.href = 'https://www.instagram.com/create/style/';
        await Utils.delay(3000, 4000);
      }

      // 2. Kép feltöltése
      await Utils.delay(1000, 2000);
      const file = await Utils.fetchImageAsFile(content.media_urls[0], 'ig_post_image');

      const fileInputs = document.querySelectorAll('input[type="file"]');
      let fileInput = null;

      for (const input of fileInputs) {
        if (!input.disabled && input.accept && input.accept.includes('image')) {
          fileInput = input;
          break;
        }
      }

      if (!fileInput && fileInputs.length > 0) {
        fileInput = fileInputs[0];
      }

      if (fileInput) {
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        fileInput.files = dataTransfer.files;
        fileInput.dispatchEvent(new Event('change', { bubbles: true }));

        console.log('[TrendMaster/IG] Kép kiválasztva');
        await Utils.delay(2000, 3000);
      } else {
        throw new Error('File input nem található');
      }

      // 3. Következő gomb (filter oldal átugrása)
      let nextBtn = await Utils.findElement(SELECTORS.nextButton, 5000);
      if (nextBtn) {
        await Utils.humanClick(nextBtn);
        await Utils.delay(1500, 2500);
      }

      // 4. Még egy Következő gomb (edit oldal átugrása)
      nextBtn = await Utils.findElement(SELECTORS.nextButton, 5000);
      if (nextBtn) {
        await Utils.humanClick(nextBtn);
        await Utils.delay(1500, 2500);
      }

      // 5. Caption/Felirat beírása
      if (content.text) {
        const captionInput = await Utils.findElement(SELECTORS.captionInput, 5000);

        if (captionInput) {
          await Utils.humanClick(captionInput);
          await Utils.delay(300, 600);

          const sanitizedText = Utils.sanitizeText(content.text);

          // Instagram textarea kezelés
          if (captionInput.tagName === 'TEXTAREA') {
            captionInput.value = sanitizedText;
            captionInput.dispatchEvent(new Event('input', { bubbles: true }));
          } else {
            await Utils.humanType(captionInput, sanitizedText);
          }

          await Utils.delay(500, 1000);
        }
      }

      // 6. Megosztás gomb megnyomása
      await Utils.delay(1000, 2000);
      const shareBtn = await Utils.findElement(SELECTORS.shareButton, 5000);

      if (!shareBtn) {
        throw new Error('Megosztás gomb nem található');
      }

      await Utils.humanClick(shareBtn);
      await Utils.delay(3000, 5000);

      console.log('[TrendMaster/IG] Poszt létrehozva!');
      return { success: true };

    } catch (error) {
      console.error('[TrendMaster/IG] Poszt hiba:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Instagram Story létrehozás
   */
  async function createStory(content) {
    console.log('[TrendMaster/IG] Story létrehozás kezdés...');

    try {
      // Ellenőrizzük, van-e kép
      if (!content.media_urls || content.media_urls.length === 0) {
        throw new Error('Instagram story-hoz kép szükséges');
      }

      // 1. Story gomb keresése
      const storyBtn = await Utils.findElement(SELECTORS.storyButton, 5000);

      if (storyBtn) {
        await Utils.humanClick(storyBtn);
        await Utils.delay(2000, 3000);
      } else {
        // Próbáljuk a create menün keresztül
        const createBtn = await Utils.findElement(SELECTORS.newPostButton, 3000);
        if (createBtn) {
          await Utils.humanClick(createBtn);
          await Utils.delay(1000, 2000);

          // Story opció kiválasztása
          const storyOption = await Utils.findElement(SELECTORS.addToStoryOption, 3000);
          if (storyOption) {
            await Utils.humanClick(storyOption);
            await Utils.delay(1500, 2500);
          }
        }
      }

      // 2. Kép feltöltése
      await Utils.delay(1000, 2000);
      const file = await Utils.fetchImageAsFile(content.media_urls[0], 'ig_story_image');

      const fileInputs = document.querySelectorAll('input[type="file"]');
      let fileInput = null;

      for (const input of fileInputs) {
        if (!input.disabled) {
          fileInput = input;
          break;
        }
      }

      if (fileInput) {
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        fileInput.files = dataTransfer.files;
        fileInput.dispatchEvent(new Event('change', { bubbles: true }));

        console.log('[TrendMaster/IG] Story kép kiválasztva');
        await Utils.delay(2000, 3000);
      }

      // 3. Ha van szöveg, hozzáadjuk
      if (content.text) {
        // Szöveg gomb keresése
        const textBtn = await Utils.findElement(SELECTORS.storyTextButton, 3000);

        if (textBtn) {
          await Utils.humanClick(textBtn);
          await Utils.delay(500, 1000);

          // Szöveg beírása
          const textInput = await Utils.findElement([
            'div[contenteditable="true"]',
            'textarea',
            'input[type="text"]'
          ], 3000);

          if (textInput) {
            await Utils.humanType(textInput, Utils.sanitizeText(content.text));
            await Utils.delay(500, 1000);

            // Kattintás kívülre a szöveg rögzítéséhez
            document.body.click();
            await Utils.delay(500, 1000);
          }
        }
      }

      // 4. Megosztás
      await Utils.delay(1000, 2000);
      const shareBtn = await Utils.findElement(SELECTORS.shareStoryButton, 8000);

      if (shareBtn) {
        await Utils.humanClick(shareBtn);
        await Utils.delay(3000, 5000);
      } else {
        // Alternatív: "Your story" gomb keresése
        const yourStoryBtn = await Utils.findElement([
          'text:Your story',
          'text:Saját történet',
          'div[role="button"]:first-child'
        ], 3000);

        if (yourStoryBtn) {
          await Utils.humanClick(yourStoryBtn);
          await Utils.delay(3000, 5000);
        }
      }

      console.log('[TrendMaster/IG] Story létrehozva!');
      return { success: true };

    } catch (error) {
      console.error('[TrendMaster/IG] Story hiba:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Like végrehajtása
   */
  async function performLike(targetUrl) {
    console.log('[TrendMaster/IG] Like kezdés...');

    try {
      if (targetUrl) {
        window.location.href = targetUrl;
        await Utils.delay(2500, 4000);
      }

      // Ellenőrizzük, nincs-e már like-olva
      const unlikeBtn = await Utils.findElement(SELECTORS.unlikeButton, 2000);
      if (unlikeBtn) {
        console.log('[TrendMaster/IG] Már like-olva van');
        return { success: true };
      }

      const likeBtn = await Utils.findElement(SELECTORS.likeButton, 5000);
      if (!likeBtn) {
        throw new Error('Like gomb nem található');
      }

      await Utils.humanClick(likeBtn);
      await Utils.delay(1000, 2000);

      console.log('[TrendMaster/IG] Like végrehajtva!');
      return { success: true };

    } catch (error) {
      console.error('[TrendMaster/IG] Like hiba:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Komment írása
   */
  async function writeComment(content, targetUrl) {
    console.log('[TrendMaster/IG] Komment kezdés...');

    try {
      if (targetUrl) {
        window.location.href = targetUrl;
        await Utils.delay(2500, 4000);
      }

      const commentBox = await Utils.findElement(SELECTORS.commentBox, 5000);
      if (!commentBox) {
        throw new Error('Komment mező nem található');
      }

      await Utils.humanClick(commentBox);
      await Utils.delay(500, 1000);

      const sanitizedText = Utils.sanitizeText(content.text);

      // Instagram textarea-hoz direkt value beállítás
      commentBox.focus();
      commentBox.value = sanitizedText;
      commentBox.dispatchEvent(new Event('input', { bubbles: true }));

      await Utils.delay(500, 1000);

      // Közzététel gomb keresése
      const postBtn = await Utils.findElement(SELECTORS.postCommentButton, 3000);

      if (postBtn) {
        await Utils.humanClick(postBtn);
      } else {
        // Enter küldése alternatívaként
        commentBox.dispatchEvent(new KeyboardEvent('keydown', {
          key: 'Enter',
          code: 'Enter',
          bubbles: true
        }));
      }

      await Utils.delay(2000, 3000);

      console.log('[TrendMaster/IG] Komment elküldve!');
      return { success: true };

    } catch (error) {
      console.error('[TrendMaster/IG] Komment hiba:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Task handler
   */
  async function handleTask(task) {
    console.log('[TrendMaster/IG] Task fogadva:', task.task_type);

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

      default:
        return { success: false, error: `Ismeretlen task típus: ${task.task_type}` };
    }
  }

  // ═══════════════════════════════════════════════════════════════════
  // MESSAGE LISTENER
  // ═══════════════════════════════════════════════════════════════════

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'EXECUTE_TASK' && message.task?.platform === 'instagram') {
      handleTask(message.task).then(sendResponse);
      return true;
    }
  });

  console.log('[TrendMaster] Instagram content script betöltve (v2 - image & story support)');
})();
