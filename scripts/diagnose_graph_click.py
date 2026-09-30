"""One focused, read-only diagnosis of the relationship SVG click on 8769."""

from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1500, "height": 980})
        page.on("pageerror", lambda error: print("PAGE_ERROR", str(error)))
        page.on("console", lambda message: print("CONSOLE", message.type, message.text)
                if message.type == "error" else None)
        page.on("request", lambda request: print("REQUEST", request.url)
                if "/api/actors/" in request.url else None)
        page.on("response", lambda response: print("RESPONSE", response.status, response.url)
                if "/api/actors/" in response.url else None)
        page.on("requestfailed", lambda request: print("FAILED", request.url, request.failure))
        page.goto("http://127.0.0.1:8769", wait_until="domcontentloaded")
        page.wait_for_function("window.mosswood?.ready && window.mosswood?.person")
        page.evaluate("() => window.mosswood.configure({overlay:'relationships'})")
        if page.locator('#relation-type option').count() > 1:
            page.locator('#relation-type').select_option(index=1)
            page.locator('#relation-type').select_option(index=0)
        node = page.locator("#relation-graph .relation-node").first
        target = node.get_attribute("data-graph-person")
        print("BEFORE", page.evaluate("""() => ({selected:window.mosswood.renderer.selected,
          person:window.mosswood.person?.id,open:document.querySelector('#relationships-dialog').open})"""))
        print("TARGET", target)
        node.click()
        print("IMMEDIATE", page.evaluate("""() => ({selected:window.mosswood.renderer.selected,
          person:window.mosswood.person?.id,open:document.querySelector('#relationships-dialog').open,
          toast:document.getElementById('toast').textContent})"""))
        page.wait_for_timeout(2500)
        print("AFTER_2_5S", page.evaluate("""() => ({selected:window.mosswood.renderer.selected,
          person:window.mosswood.person?.id,open:document.querySelector('#relationships-dialog').open,
          toast:document.getElementById('toast').textContent})"""))
        browser.close()


if __name__ == "__main__":
    main()
