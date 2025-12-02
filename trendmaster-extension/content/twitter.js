/**
 * TrendMaster - Twitter/X Content Script
 * Twitter-specifikus automatizáció kép feltöltéssel
 */

(() => {
  const Utils = window.TrendMasterUtils;

  const SELECTORS = {
    // Tweet/Post compose box
    tweetBox: [
      '[data-testid="tweetTextarea_0"]',
      '[data-testid="tweetTextarea_0_label"]',
      'div[aria-label*="Tweet text"]',
      'div[aria-label*="Post text"]',
      'div[role="textbox"][data-testid]',
      'div[contenteditable="true"][role="textbox"]'
    ],

    // Tweet/Post küldés gomb
    tweetButton: [
      '[data-testid="tweetButtonInline"]',
      '[data-testid="tweetButton"]',
      'button[data-testid="tweetButtonInline"]',
      'div[role="button"][data-testid="tweetButtonInline"]'
    ],

    // Compose gomb (új tweet indításához)
    composeButton: [
      '[data-testid="SideNav_NewTweet_Button"]',
      'a[href="/compose/tweet"]',
      '[aria-label*="Post"]',
      '[aria-label*="Tweet"]'
    ],

    // Media gomb (kép feltöltéshez)
    mediaButton: [
      '[data-testid="fileInput"]',
      '[aria-label="Add photos or video"]',
      '[aria-label*="Media"]',
      '[aria-label*="Média"]',
      'input[data-testid="fileInput"]'
    ],

    // File input
    fileInput: [
      'input[data-testid="fileInput"]',
      'input[type="file"][accept*="image"]',
      'input[type="file"][accept*="video"]',
      'input[type="file"][multiple]'
    ],

    // Like gomb
    likeButton: [
      '[data-testid="like"]',
      '[data-testid="unlike"]',
      'div[aria-label*="Like"]',
      'button[aria-label*="Like"]'
    ],

    // Retweet/Repost gomb
    retweetButton: [
      '[data-testid="retweet"]',
      '[data-testid="unretweet"]',
      'div[aria-label*="Repost"]',
      'div[aria-label*="Retweet"]'
    ],

    // Reply box
    replyBox: [
      '[data-testid="tweetTextarea_0"]',
      'div[aria-label*="Post your reply"]',
      'div[aria-label*="Tweet your reply"]'
    ],

    // Kép preview
    imagePreview: [
      '[data-testid="attachments"]',
      'div[aria-label="Image"]',
      'img[src*="blob:"]',
      'div[style*="background-image"]'
    ]
  };

  /**
   * Tweet/Post létrehozás képpel
   */
  async function createTweet(content) {
    console.log('[TrendMaster/X] Tweet kezdés...');

    try {
      // Tweet box keresése, vagy compose oldal megnyitása
      let tweetBox = await Utils.findElement(SELECTORS.tweetBox, 3000);

      if (!tweetBox) {
        // Compose gomb keresése
        const composeBtn = await Utils.findElement(SELECTORS.composeButton, 3000);

        if (composeBtn) {
          await Utils.humanClick(composeBtn);
          await Utils.delay(1500, 2500);
          tweetBox = await Utils.findElement(SELECTORS.tweetBox, 5000);
        }
      }

      if (!tweetBox) {
        // Navigálás a compose oldalra
        window.location.href = 'https://twitter.com/compose/tweet';
        await Utils.delay(2500, 3500);
        tweetBox = await Utils.findElement(SELECTORS.tweetBox, 8000);
      }

      if (!tweetBox) {
        throw new Error('Tweet mező nem található');
      }

      // Képek feltöltése (ha van)
      if (content.media_urls && content.media_urls.length > 0) {
        console.log('[TrendMaster/X] Képek feltöltése...');
        await uploadImages(content.media_urls);
        await Utils.delay(1000, 2000);
      }

      // Szöveg beírása
      if (content.text) {
        await Utils.humanClick(tweetBox);
        await Utils.delay(300, 600);

        const sanitizedText = Utils.sanitizeText(content.text);
        await Utils.humanType(tweetBox, sanitizedText);
      }

      await Utils.delay(1000, 2000);

      // Tweet gomb megnyomása
      const tweetBtn = await Utils.findElement(SELECTORS.tweetButton, 5000);
      if (!tweetBtn) {
        throw new Error('Tweet gomb nem található');
      }

      await Utils.humanClick(tweetBtn);
      await Utils.delay(2500, 4000);

      console.log('[TrendMaster/X] Tweet elküldve!');
      return { success: true };

    } catch (error) {
      console.error('[TrendMaster/X] Tweet hiba:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Képek feltöltése
   */
  async function uploadImages(imageUrls) {
    console.log('[TrendMaster/X] Képek feltöltése:', imageUrls.length, 'db');

    try {
      // Maximum 4 kép Twitter-en
      const urls = imageUrls.slice(0, 4);

      for (let i = 0; i < urls.length; i++) {
        const imageUrl = urls[i];
        console.log(`[TrendMaster/X] Kép ${i + 1}/${urls.length} feltöltése...`);

        try {
          // Kép letöltése
          const file = await Utils.fetchImageAsFile(imageUrl, `tweet_image_${i + 1}`);

          // File input keresése
          let fileInput = document.querySelector('input[data-testid="fileInput"]');

          if (!fileInput) {
            fileInput = document.querySelector('input[type="file"][accept*="image"]');
          }

          if (!fileInput) {
            // Összes file input közül az első használható
            const fileInputs = document.querySelectorAll('input[type="file"]');
            for (const input of fileInputs) {
              if (!input.disabled) {
                fileInput = input;
                break;
              }
            }
          }

          if (fileInput) {
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);
            fileInput.files = dataTransfer.files;
            fileInput.dispatchEvent(new Event('change', { bubbles: true }));

            console.log(`[TrendMaster/X] Kép ${i + 1} kiválasztva`);

            // Várakozás a feltöltésre
            await Utils.waitForImagePreview(SELECTORS.imagePreview, 10000);
            await Utils.delay(1000, 2000);

          } else {
            console.warn('[TrendMaster/X] File input nem található');
          }

        } catch (imgError) {
          console.error(`[TrendMaster/X] Kép ${i + 1} feltöltési hiba:`, imgError);
        }
      }

      console.log('[TrendMaster/X] Képek feltöltve');
      return true;

    } catch (error) {
      console.error('[TrendMaster/X] Kép feltöltési hiba:', error);
      throw error;
    }
  }

  /**
   * Like végrehajtása
   */
  async function performLike(targetUrl) {
    console.log('[TrendMaster/X] Like kezdés...');

    try {
      if (targetUrl) {
        window.location.href = targetUrl;
        await Utils.delay(2500, 4000);
      }

      const likeBtn = await Utils.findElement(SELECTORS.likeButton);
      if (!likeBtn) {
        throw new Error('Like gomb nem található');
      }

      // Ellenőrizzük, nincs-e már like-olva
      const testId = likeBtn.getAttribute('data-testid');
      if (testId === 'unlike') {
        console.log('[TrendMaster/X] Már like-olva van');
        return { success: true };
      }

      await Utils.humanClick(likeBtn);
      await Utils.delay(1000, 2000);

      console.log('[TrendMaster/X] Like végrehajtva!');
      return { success: true };

    } catch (error) {
      console.error('[TrendMaster/X] Like hiba:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Retweet/Repost végrehajtása
   */
  async function performRetweet(targetUrl) {
    console.log('[TrendMaster/X] Retweet kezdés...');

    try {
      if (targetUrl) {
        window.location.href = targetUrl;
        await Utils.delay(2500, 4000);
      }

      const retweetBtn = await Utils.findElement(SELECTORS.retweetButton);
      if (!retweetBtn) {
        throw new Error('Retweet gomb nem található');
      }

      // Ellenőrizzük, nincs-e már retweet-elve
      const testId = retweetBtn.getAttribute('data-testid');
      if (testId === 'unretweet') {
        console.log('[TrendMaster/X] Már retweet-elve van');
        return { success: true };
      }

      await Utils.humanClick(retweetBtn);
      await Utils.delay(500, 1000);

      // "Repost" opció keresése a menüben
      const repostOption = await Utils.findElement([
        '[data-testid="retweetConfirm"]',
        'div[role="menuitem"]:has-text("Repost")',
        'div[role="menuitem"]:has-text("Retweet")'
      ], 3000);

      if (repostOption) {
        await Utils.humanClick(repostOption);
        await Utils.delay(1500, 2500);
      }

      console.log('[TrendMaster/X] Retweet végrehajtva!');
      return { success: true };

    } catch (error) {
      console.error('[TrendMaster/X] Retweet hiba:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Reply/Válasz írása
   */
  async function writeReply(content, targetUrl) {
    console.log('[TrendMaster/X] Reply kezdés...');

    try {
      if (targetUrl) {
        window.location.href = targetUrl;
        await Utils.delay(2500, 4000);
      }

      // Reply box keresése
      const replyBox = await Utils.findElement(SELECTORS.replyBox, 5000);
      if (!replyBox) {
        throw new Error('Reply mező nem található');
      }

      await Utils.humanClick(replyBox);
      await Utils.delay(500, 1000);

      // Képek feltöltése (ha van)
      if (content.media_urls && content.media_urls.length > 0) {
        await uploadImages(content.media_urls);
        await Utils.delay(1000, 2000);
      }

      // Szöveg beírása
      if (content.text) {
        const sanitizedText = Utils.sanitizeText(content.text);
        await Utils.humanType(replyBox, sanitizedText);
      }

      await Utils.delay(1000, 2000);

      // Reply gomb megnyomása
      const replyBtn = await Utils.findElement([
        '[data-testid="tweetButtonInline"]',
        '[data-testid="tweetButton"]',
        'button:has-text("Reply")'
      ], 3000);

      if (replyBtn) {
        await Utils.humanClick(replyBtn);
        await Utils.delay(2000, 3000);
      }

      console.log('[TrendMaster/X] Reply elküldve!');
      return { success: true };

    } catch (error) {
      console.error('[TrendMaster/X] Reply hiba:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Task handler
   */
  async function handleTask(task) {
    console.log('[TrendMaster/X] Task fogadva:', task.task_type);

    const content = task.content || { text: '', media_urls: [] };

    switch (task.task_type.toLowerCase()) {
      case 'post':
        return await createTweet(content);

      case 'like':
        return await performLike(task.target_url);

      case 'share':
      case 'retweet':
        return await performRetweet(task.target_url);

      case 'comment':
      case 'reply':
        return await writeReply(content, task.target_url);

      default:
        return { success: false, error: `Ismeretlen task típus: ${task.task_type}` };
    }
  }

  // ═══════════════════════════════════════════════════════════════════
  // MESSAGE LISTENER
  // ═══════════════════════════════════════════════════════════════════

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'EXECUTE_TASK' && message.task?.platform === 'twitter') {
      handleTask(message.task).then(sendResponse);
      return true;
    }
  });

  console.log('[TrendMaster] Twitter content script betöltve (v2 - image support)');
})();
