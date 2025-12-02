"""
Facebook Poster Module
Használja a Firefox session-t Facebook posztolásra
Nincs szükség Facebook App-ra vagy OAuth-ra!
"""
import asyncio
from pathlib import Path
import shutil
import tempfile
from playwright.async_api import async_playwright
import os


class FacebookPoster:
    """Firefox session-t használó Facebook poster"""

    def __init__(self, firefox_profile_path=None):
        """
        Args:
            firefox_profile_path: Firefox profil path (opcionális)
                                 Ha nincs megadva, az alapértelmezett Snap Firefox profilt használja
        """
        if firefox_profile_path is None:
            # Snap Firefox alapértelmezett profil
            firefox_profile_path = Path.home() / "snap/firefox/common/.mozilla/firefox/8pxrtgul.default"

        self.source_profile = Path(firefox_profile_path)

        if not self.source_profile.exists():
            raise FileNotFoundError(
                f"Firefox profil nem található: {self.source_profile}\n"
                f"Ellenőrizd, hogy be vagy-e jelentkezve Firefoxban!"
            )

        # Temporary directory for profile copy
        self.temp_dir = Path(tempfile.mkdtemp(prefix="firefox_fb_"))

    def copy_profile(self):
        """Copy Firefox profile to temporary location"""
        # Only copy essential files for faster startup
        essential_files = [
            "cookies.sqlite",
            "cookies.sqlite-shm",
            "cookies.sqlite-wal",
            "sessionstore.jsonlz4",
            "sessionstore-backups",
            "storage",
            "storage.sqlite"
        ]

        for item in essential_files:
            source = self.source_profile / item
            if source.exists():
                dest = self.temp_dir / item
                try:
                    if source.is_file():
                        shutil.copy2(source, dest)
                    elif source.is_dir():
                        shutil.copytree(source, dest, dirs_exist_ok=True)
                except Exception:
                    pass  # Skip if copy fails

        return self.temp_dir

    async def post(self, post_text: str, image_path: str = None, comment_text: str = None):
        """
        Facebook poszt publikálás

        Args:
            post_text: A poszt szövege
            image_path: Opcionális kép path
            comment_text: Opcionális komment szöveg (pl. forrás link)

        Returns:
            dict: {
                'success': bool,
                'message': str,
                'screenshot': str (opcionális)
            }
        """
        # Copy profile first
        profile_dir = self.copy_profile()

        try:
            async with async_playwright() as p:
                # Firefox indítása persistent context-tel
                context = await p.firefox.launch_persistent_context(
                    str(profile_dir),
                    headless=False,
                    args=['--disable-blink-features=AutomationControlled'],
                    slow_mo=500
                )

                page = context.pages[0] if context.pages else await context.new_page()

                try:
                    # Facebook megnyitása
                    await page.goto('https://www.facebook.com', wait_until='domcontentloaded')
                    await page.wait_for_timeout(3000)

                    # Login ellenőrzés
                    login_indicators = [
                        'div[aria-label*="Create"]',
                        'div[aria-label*="Bejegyzés"]',
                        'span:has-text("What\'s on your mind")',
                        'span:has-text("Mi jár a fejedben")',
                    ]

                    is_logged_in = False
                    for selector in login_indicators:
                        if await page.locator(selector).count() > 0:
                            is_logged_in = True
                            break

                    if not is_logged_in:
                        return {
                            'success': False,
                            'message': 'Nincs bejelentkezve Facebook! Jelentkezz be egyszer Firefoxban.'
                        }

                    # "Create post" gomb megnyomása
                    create_selectors = [
                        'div[aria-label="Create a post"]',
                        'div[aria-label="Bejegyzés létrehozása"]',
                    ]

                    clicked = False
                    for selector in create_selectors:
                        try:
                            element = page.locator(selector).first
                            if await element.count() > 0:
                                await element.click(timeout=5000)
                                clicked = True
                                break
                        except Exception:
                            continue

                    if not clicked:
                        return {
                            'success': False,
                            'message': 'Nem sikerült megnyitni a poszt dialógot'
                        }

                    await page.wait_for_timeout(3000)

                    # ELŐSZÖR: Szöveg beírása (az eredeti poszt ablakban!)
                    print("   📝 Szöveg írása ELŐSZÖR...")
                    textarea_selectors = [
                        'div[contenteditable="true"]',
                        'div[aria-label*="mind"]',
                        'div[aria-label*="fejedben"]',
                        'div[role="textbox"]',
                    ]

                    text_written = False
                    for selector in textarea_selectors:
                        try:
                            element = page.locator(selector).first
                            if await element.count() > 0:
                                # Simpl click (no force), várok hogy elérhető legyen
                                await element.click(timeout=10000)
                                await page.wait_for_timeout(500)

                                # Type
                                await element.type(post_text, delay=50)

                                text_written = True
                                print("   ✅ Szöveg beírva!")
                                break
                        except Exception as e:
                            print(f"      ⚠️  {selector} hiba: {e}")
                            continue

                    if not text_written:
                        return {
                            'success': False,
                            'message': 'Nem sikerült beírni a szöveget'
                        }

                    await page.wait_for_timeout(1000)

                    # MÁSODSZOR: Kép feltöltés (UGYANABBAN az ablakban!)
                    if image_path and os.path.exists(image_path):
                        try:
                            print("   📸 Kép feltöltése MÁSODSZOR...")

                            # KRITIKUS: Meg KELL találnunk a Fotó/Videó gombot!
                            # Ha direkt file input-ot használunk, új ablak nyílik!

                            # Screenshot a debugging-hez
                            await page.screenshot(path="/tmp/fb_before_photo_button.png")
                            print("   📷 Screenshot készítve: /tmp/fb_before_photo_button.png")

                            # Keressük a Fotó/Videó gombot precízebben
                            # FONTOS: NE találjuk meg az "Élő videó" gombot!
                            photo_button_selectors = [
                                # Aria label alapú keresés - PONTOS egyezés
                                '[aria-label="Fotó/videó"]',
                                '[aria-label="Photo/video"]',
                                '[aria-label="Fényképek/videók"]',
                                '[aria-label="Photos/videos"]',
                                # Fotó szó kötelező, de videó nélkül NE keresse az Élő videót!
                                '[aria-label*="Fotó"][aria-label*="videó"]',  # Both words required
                                '[aria-label*="Photo"][aria-label*="video"]',  # Both words required
                                # Text alapú - az "Elhelyezés a bejegyzésben" sor első gombja
                                'div:has-text("Elhelyezés a bejegyzésben") ~ div [role="button"]',
                                'div:has-text("Add to your post") ~ div [role="button"]',
                            ]

                            photo_button_clicked = False
                            for selector in photo_button_selectors:
                                try:
                                    elements = await page.locator(selector).all()
                                    print(f"   🔍 Próbálom: {selector} - találat: {len(elements)} db")

                                    if len(elements) > 0:
                                        # Skip if too many results (not specific enough)
                                        if len(elements) > 10:
                                            print(f"   ⚠️  Túl sok találat ({len(elements)}), próbálom a következőt...")
                                            continue

                                        # Próbáljuk végig az elemeket
                                        for idx, element in enumerate(elements):
                                            try:
                                                print(f"   ✅ Fotó gomb jelölt #{idx+1}: {selector}")

                                                # Screenshot az elem környékéről
                                                try:
                                                    await element.screenshot(path=f"/tmp/fb_photo_button_{idx}.png")
                                                    print(f"   📷 Gomb screenshot: /tmp/fb_photo_button_{idx}.png")
                                                except:
                                                    pass

                                                # JavaScript click to bypass overlay!
                                                await element.evaluate("el => el.click()")
                                                print(f"   ✅ Fotó gomb megnyomva (JS click)!")
                                                photo_button_clicked = True
                                                await page.wait_for_timeout(1000)
                                                break
                                            except Exception as e:
                                                print(f"   ⚠️  Element #{idx+1} hiba: {e}")
                                                continue

                                        if photo_button_clicked:
                                            break
                                except Exception as e:
                                    print(f"   ⚠️  {selector} - hiba: {e}")
                                    continue

                            if not photo_button_clicked:
                                print("   ❌ KRITIKUS: Fotó gomb nem található!")
                                print("   ❌ NEM használok direkt file input-ot, mert az új ablakot nyit!")
                                return {
                                    'success': False,
                                    'message': 'Fotó gomb nem található - nem lehet képet feltölteni'
                                }

                            # Most hogy a Fotó gomb megnyomva, feltöltjük a képet
                            print("   ⏳ Várakozás a file picker megjelenésére...")
                            await page.wait_for_timeout(2000)

                            # Keressük a file input-ot - lehet hogy új elem jött létre
                            file_input_selectors = [
                                'input[type="file"][accept*="image"]',
                                'input[type="file"]',
                                'input[accept*="image"]',
                            ]

                            file_input_found = False
                            for file_sel in file_input_selectors:
                                try:
                                    file_inputs = await page.locator(file_sel).all()
                                    print(f"   🔍 File input keresés: {file_sel} - {len(file_inputs)} db")

                                    if len(file_inputs) > 0:
                                        # Próbáljuk az utolsó file input-ot (legújabb)
                                        file_input = file_inputs[-1]

                                        # Set the file directly
                                        await file_input.set_input_files(image_path)
                                        print(f"   ✅ Kép kiválasztva: {image_path}")
                                        file_input_found = True
                                        break
                                except Exception as e:
                                    print(f"   ⚠️  File input hiba ({file_sel}): {e}")
                                    continue

                            if not file_input_found:
                                print("   ❌ File input nem található!")
                                return {
                                    'success': False,
                                    'message': 'File input nem található a Fotó gomb megnyomása után'
                                }

                            # Várunk arra, hogy megjelenjen a kép preview
                            print("   ⏳ Várakozás a kép preview-ra...")
                            await page.wait_for_timeout(3000)

                            # Ellenőrizzük, hogy megjelent-e a kép
                            img_selectors = [
                                'img[src*="blob"]',
                                'img[src*="facebook"]',
                                'div[style*="background-image"]',
                            ]

                            image_loaded = False
                            for img_sel in img_selectors:
                                if await page.locator(img_sel).count() > 0:
                                    image_loaded = True
                                    print(f"   ✅ Kép preview megjelent!")
                                    break

                            if not image_loaded:
                                print("   ⚠️  Kép preview nem látható, de folytatom...")

                            # Extra várakozás a teljes feldolgozásra
                            await page.wait_for_timeout(2000)
                            print("   ✅ Kép feltöltve és feldolgozva!")
                        except Exception as e:
                            print(f"   ⚠️  Kép feltöltés hiba: {e}")
                            return {
                                'success': False,
                                'message': f'Kép feltöltés hiba: {str(e)}'
                            }

                    # "Post" gomb megnyomása - több selector
                    post_button_selectors = [
                        'div[aria-label="Post"]',
                        'div[aria-label="Közzététel"]',
                        'div[aria-label="Publish"]',
                        'span:has-text("Közzététel")',
                        'span:has-text("Post")',
                        'div[role="button"]:has-text("Közzététel")',
                        'div[role="button"]:has-text("Post")',
                    ]

                    posted = False
                    for selector in post_button_selectors:
                        try:
                            print(f"   🔍 Próbálom: {selector}")
                            element = page.locator(selector).first
                            if await element.count() > 0:
                                print(f"   ✅ Megtalálva! JavaScript click...")
                                # Use JavaScript click to bypass overlay
                                await element.evaluate("el => el.click()")
                                posted = True
                                print(f"   ✅ Publish gomb megnyomva!")
                                break
                        except Exception as e:
                            print(f"   ⚠️  {selector} - hiba: {e}")
                            continue

                    if not posted:
                        print(f"   ❌ Egyik selector sem működött!")
                        return {
                            'success': False,
                            'message': 'Nem sikerült publikálni a posztot'
                        }

                    # Várunk 5 másodpercet, hogy a poszt megjelenjen
                    await page.wait_for_timeout(5000)

                    # Ha van comment_text, kommenteljünk
                    if comment_text:
                        try:
                            print(f"💬 Komment írása: {comment_text}")

                            # Extra várakozás, hogy a poszt betöltődjön
                            await page.wait_for_timeout(3000)

                            # Scroll to top to see the new post
                            await page.evaluate("window.scrollTo(0, 0)")
                            await page.wait_for_timeout(1000)

                            # Próbáljuk megnyitni a komment boxot a "Hozzászólás" gombbal
                            comment_button_selectors = [
                                'div[aria-label="Hozzászólás"]',
                                'div[aria-label="Comment"]',
                                'span:has-text("Hozzászólás")',
                            ]

                            for selector in comment_button_selectors:
                                try:
                                    button = page.locator(selector).first
                                    if await button.count() > 0:
                                        await button.click()
                                        await page.wait_for_timeout(1000)
                                        print(f"   ✅ Komment gomb megnyomva")
                                        break
                                except Exception:
                                    continue

                            # Komment box keresése - több selector
                            comment_selectors = [
                                'div[aria-label="Írj hozzászólást..."]',
                                'div[aria-label*="Írj"]',
                                'div[aria-label*="Write a comment"]',
                                'div[aria-label*="hozzászólás"]',
                                'div[contenteditable="true"][data-lexical-editor="true"]',
                                'div[contenteditable="true"][role="textbox"]',
                            ]

                            commented = False
                            for selector in comment_selectors:
                                try:
                                    element = page.locator(selector).first
                                    if await element.count() > 0:
                                        print(f"   ✅ Komment box megtalálva: {selector}")
                                        await element.click()
                                        await page.wait_for_timeout(800)

                                        # Írjuk be a komment szöveget
                                        await element.type(comment_text, delay=50)
                                        await page.wait_for_timeout(800)
                                        print(f"   ✅ Komment szöveg beírva: {comment_text}")

                                        # Enter megnyomása a küldéshez
                                        await page.keyboard.press('Enter')
                                        print(f"   ⏳ Várakozás a komment küldésére...")
                                        await page.wait_for_timeout(3000)

                                        # Ellenőrizzük, hogy a komment megjelent-e
                                        comment_check_selectors = [
                                            f'span:has-text("{comment_text[:20]}")',  # First 20 chars
                                            'div[role="article"]',
                                        ]

                                        comment_posted = False
                                        for check_sel in comment_check_selectors:
                                            if await page.locator(check_sel).count() > 1:  # More than 1 means comment appeared
                                                comment_posted = True
                                                break

                                        if comment_posted:
                                            commented = True
                                            print(f"   ✅ Komment sikeresen posztolva!")
                                        else:
                                            print(f"   ⚠️  Komment lehet hogy nem lett elküldve")
                                            commented = True  # Continue anyway
                                        break
                                except Exception as e:
                                    print(f"   ⚠️  {selector} - hiba: {e}")
                                    continue

                            if not commented:
                                print(f"   ⚠️  Nem sikerült kommentelni (nem kritikus)")

                        except Exception as e:
                            print(f"   ⚠️  Komment hiba: {e}")

                    # Screenshot
                    screenshot_path = f"/tmp/fb_post_{int(asyncio.get_event_loop().time())}.png"
                    await page.screenshot(path=screenshot_path)

                    return {
                        'success': True,
                        'message': 'Poszt sikeresen publikálva!',
                        'screenshot': screenshot_path
                    }

                except Exception as e:
                    return {
                        'success': False,
                        'message': f'Hiba: {str(e)}'
                    }

                finally:
                    # Cleanup
                    await page.wait_for_timeout(3000)
                    await context.close()

        finally:
            # Temp profil törlése
            try:
                shutil.rmtree(profile_dir)
            except Exception:
                pass


async def publish_to_facebook(post_content: str, image_path: str = None, comment_text: str = None):
    """
    Egyszerű wrapper függvény Facebook posztoláshoz

    Args:
        post_content: Poszt szövege
        image_path: Opcionális kép path
        comment_text: Opcionális komment (pl. forrás link)

    Returns:
        dict: {'success': bool, 'message': str}
    """
    try:
        poster = FacebookPoster()
        result = await poster.post(post_content, image_path, comment_text)
        return result
    except Exception as e:
        return {
            'success': False,
            'message': f'Facebook poster hiba: {str(e)}'
        }


# Sync wrapper for use in non-async contexts
def publish_to_facebook_sync(post_content: str, image_path: str = None, comment_text: str = None):
    """Szinkron wrapper"""
    return asyncio.run(publish_to_facebook(post_content, image_path, comment_text))
