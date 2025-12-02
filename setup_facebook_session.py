"""
Facebook Session Setup Tool
Extracts Firefox session cookies for Railway deployment
"""

import asyncio
import json
import base64
import os
from pathlib import Path
from playwright.async_api import async_playwright


async def extract_facebook_session():
    """
    Launch Firefox, wait for user to login to Facebook,
    then extract and save session cookies
    """

    print("🔧 Facebook Session Setup Tool")
    print("=" * 50)
    print()
    print("Ez a tool segít beállítani a Facebook session-t Railway deployment-hez.")
    print()
    print("LÉPÉSEK:")
    print("1. Firefox böngésző fog megnyílni")
    print("2. Jelentkezz be Facebookra (Lili fiókjával!)")
    print("3. Várj, amíg teljesen betölt a Facebook")
    print("4. Nyomj ENTER-t ebben a terminálban")
    print("5. A session cookie-k automatikusan el lesznek mentve")
    print()
    input("Nyomj ENTER-t a folytatáshoz...")

    profile_path = "/tmp/firefox_profile"
    Path(profile_path).mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        print("\n🌐 Firefox indítása...")

        browser = await p.firefox.launch(
            headless=False,
            args=[f'--user-data-dir={profile_path}']
        )

        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800}
        )

        page = await context.new_page()

        print("✅ Firefox elindult!")
        print("\n📱 Facebook megnyitása...")

        await page.goto('https://www.facebook.com')
        await page.wait_for_load_state('networkidle')

        print("\n⏳ Kérlek jelentkezz be Facebookra a megnyílt böngészőben!")
        print("   (Használd Lili fiókját!)")
        print()
        print("Ha kész vagy, nyomj ENTER-t ebben a terminálban...")

        input()

        print("\n🍪 Session cookie-k kinyerése...")

        # Get all cookies
        cookies = await context.cookies()

        # Filter for Facebook cookies
        fb_cookies = [c for c in cookies if 'facebook.com' in c.get('domain', '')]

        if not fb_cookies:
            print("\n❌ HIBA: Nem találtam Facebook cookie-kat!")
            print("   Biztos, hogy be vagy jelentkezve?")
            await browser.close()
            return False

        print(f"✅ {len(fb_cookies)} Facebook cookie találva!")

        # Save cookies to file
        cookies_file = 'facebook_session_cookies.json'
        with open(cookies_file, 'w') as f:
            json.dump(fb_cookies, f, indent=2)

        print(f"\n💾 Cookie-k elmentve: {cookies_file}")

        # Create base64 encoded version for Railway env variable
        cookies_b64 = base64.b64encode(json.dumps(fb_cookies).encode()).decode()

        env_file = 'railway_env_variables.txt'
        with open(env_file, 'w') as f:
            f.write("# Railway Environment Variables\n")
            f.write("# Másold be ezeket a Railway dashboard-ba!\n\n")
            f.write(f"MULTI_USER_MODE=false\n")
            f.write(f"DEFAULT_USER_ID=lili\n")
            f.write(f"FACEBOOK_SESSION_COOKIES={cookies_b64}\n")

        print(f"📝 Railway env variables elmentve: {env_file}")

        print("\n" + "=" * 50)
        print("✨ SIKERES SETUP!")
        print("=" * 50)
        print()
        print("KÖVETKEZŐ LÉPÉSEK:")
        print()
        print("1. Nyisd meg: railway_env_variables.txt")
        print("2. Másold át a változókat a Railway dashboard-ba:")
        print("   https://railway.app/project/[PROJECT_ID]/variables")
        print()
        print("3. Deploy az app-ot:")
        print("   railway up")
        print()
        print("4. KÉSZ! Az app már használja Lili Facebook session-jét! 🚀")
        print()

        await browser.close()

        return True


async def test_session():
    """Test if saved session works"""

    cookies_file = 'facebook_session_cookies.json'

    if not os.path.exists(cookies_file):
        print("❌ Nincs mentett session! Futtasd először: extract_facebook_session()")
        return False

    print("\n🧪 Session teszt...")

    with open(cookies_file, 'r') as f:
        cookies = json.load(f)

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False)
        context = await browser.new_context()

        # Add saved cookies
        await context.add_cookies(cookies)

        page = await context.new_page()
        await page.goto('https://www.facebook.com')
        await page.wait_for_load_state('networkidle')

        # Check if we're logged in
        try:
            # If we see the logout button, we're logged in
            await page.wait_for_selector('[aria-label*="Account"]', timeout=5000)
            print("✅ Session működik! Be vagy jelentkezve!")

            await asyncio.sleep(3)
            await browser.close()
            return True

        except:
            print("❌ Session NEM működik! Cookie-k lejártak vagy érvénytelenek.")
            await browser.close()
            return False


async def main():
    """Main menu"""

    print("\n" + "=" * 50)
    print("  FACEBOOK SESSION SETUP - TrendHub")
    print("=" * 50)
    print()
    print("Válassz:")
    print("1. ÚJ session létrehozása (login szükséges)")
    print("2. Meglévő session tesztelése")
    print("3. Kilépés")
    print()

    choice = input("Választás (1-3): ").strip()

    if choice == '1':
        await extract_facebook_session()
    elif choice == '2':
        await test_session()
    else:
        print("Viszlát! 👋")


if __name__ == '__main__':
    asyncio.run(main())
