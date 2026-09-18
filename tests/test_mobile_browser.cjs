// Optional browser regression: NODE_PATH=<Playwright modules> node tests/test_mobile_browser.cjs
// BROWSER_EXECUTABLE may point at an installed Chrome; no personal profile is used.
const assert = require('node:assert/strict');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {chromium} = require('playwright');

(async () => {
  const browser = await chromium.launch({headless:true,
    ...(process.env.BROWSER_EXECUTABLE ? {executablePath:process.env.BROWSER_EXECUTABLE} : {})});
  try {
    const context = await browser.newContext({viewport:{width:390,height:844},hasTouch:true,isMobile:true});
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(pathToFileURL(path.resolve('index.html')).href);
    const noOverflow = async () => assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    const count = async () => Number(await page.locator('#visibleCount').innerText());
    const initialCount = await count();
    for (const width of [320,390,700]) {
      await page.setViewportSize({width,height:844});
      await noOverflow();
      assert.ok(await page.locator('.ios-tab-bar').isVisible());
      assert.ok(!await page.locator('#advancedFilters').isVisible());
      assert.ok(!await page.locator('.view-switchers').isVisible());
      assert.ok(await page.locator('.filter-label').isVisible());
      const cityAll = await page.locator('.filter-row [data-value="all"]').boundingBox();
      const monthAll = await page.locator('[data-month="all"]').boundingBox();
      assert.ok(Math.abs(cityAll.x-monthAll.x)<1 && Math.abs(cityAll.width-monthAll.width)<1);
    }
    await page.setViewportSize({width:390,height:844});
    // Selection is a persistent visual state after a real touch, including multi-month choices.
    for (const theme of ['dark','light']) {
      await page.evaluate(t => document.documentElement.setAttribute('data-theme',t),theme);
      await page.locator('.filter-row [data-value="新北市"]').tap();
      assert.equal(await page.locator('.filter-row [data-value="新北市"]').getAttribute('aria-pressed'),'true');
      assert.equal(await page.locator('.filter-row [data-value="all"]').getAttribute('aria-pressed'),'false');
      await page.locator('#monthFilterOptions button').nth(1).tap();
      await page.locator('#monthFilterOptions button').nth(2).tap();
      assert.equal(await page.locator('#monthFilterOptions [aria-pressed="true"]').count(),2);
      const selection = await page.evaluate(() => {
        const city = document.querySelector('.filter-row [aria-pressed="true"]');
        const month = document.querySelector('#monthFilterOptions [aria-pressed="true"]');
        const off = document.querySelector('.filter-row [data-value="all"]');
        const style = el => {const s=getComputedStyle(el);return {bg:s.backgroundColor,color:s.color};};
        return {city:style(city),month:style(month),off:style(off),cityText:getComputedStyle(city.querySelector('.badge-city')).color,
          expected:ACTIVITIES_DATA.filter(a=>a.city==='新北市' && selectedMonths.has(taipeiDateKey(new Date(a.start_time)).slice(0,7))).length};
      });
      assert.deepEqual(selection.city,selection.month);
      assert.notEqual(selection.city.bg,selection.off.bg);
      assert.notEqual(selection.city.color,selection.off.color);
      assert.equal(selection.cityText,selection.city.color);
      assert.equal(await count(),selection.expected);
      await page.locator('#monthFilterOptions button').nth(1).tap();
      assert.equal(await page.locator('#monthFilterOptions [aria-pressed="true"]').count(),1);
      await page.locator('[data-month="all"]').tap();
      await page.locator('.filter-row [data-value="all"]').tap();
      assert.equal(await count(),initialCount);
      assert.equal(await page.locator('[data-month="all"]').getAttribute('aria-pressed'),'true');
      assert.equal(await page.locator('.filter-row [data-value="all"]').getAttribute('aria-pressed'),'true');
    }
    await page.evaluate(() => document.documentElement.setAttribute('data-theme','dark'));
    await page.locator('#mobileFilterButton').click();
    assert.ok(await page.locator('#filterModal').evaluate(el => el.open && el.matches(':modal')));
    const source = await page.locator('#sourceFilter option').nth(1).getAttribute('value');
    await page.locator('#sourceFilter').selectOption(source);
    const sourceCount = await count();
    assert.ok(sourceCount > 0 && sourceCount < initialCount);
    assert.equal(await page.locator('#mobileFilterCount').innerText(),'1');
    const selectBoxes = await page.locator('#advancedFilters select').evaluateAll(nodes => nodes.map(el => {
      const r = el.getBoundingClientRect(); return {y:r.y,width:r.width,font:getComputedStyle(el).fontSize};
    }));
    assert.ok(selectBoxes.every(r => Math.abs(r.y-selectBoxes[0].y)<1 && Math.abs(r.width-selectBoxes[0].width)<1 && r.font==='13px'));
    await page.keyboard.press('Escape');
    assert.ok(!await page.locator('#filterModal').evaluate(el => el.open));
    assert.equal(await page.evaluate(() => document.activeElement.id),'mobileFilterButton');
    assert.equal(await page.locator('#advancedFilters').evaluate(el => el.parentElement.className),'container controls-container');
    await page.locator('[data-tab="calendar"]').click();
    assert.equal(await page.locator('[data-tab="calendar"]').getAttribute('aria-pressed'),'true');
    assert.ok(await page.locator('#viewCalendar').isVisible());
    assert.equal(await count(),sourceCount);
    await page.locator('[data-tab="agenda"]').click();
    assert.ok(await page.locator('#viewAgenda').isVisible());
    await page.locator('[data-tab="grid"]').click();
    await page.locator('#mobileFilterButton').click();
    await page.locator('.filter-sheet-actions .btn').first().click();
    assert.equal(await count(),initialCount);
    assert.equal(await page.locator('#sourceFilter').inputValue(),'all');
    await page.locator('.filter-sheet-actions .btn-primary').click();
    const detail = page.locator('#viewGrid .card-detail').nth(4);
    await detail.scrollIntoViewIfNeeded();
    const position = await page.evaluate(() => scrollY);
    await detail.click();
    assert.ok(await page.locator('#eventModal').evaluate(el => el.matches(':modal')));
    assert.equal(await page.locator('body').evaluate(el => el.style.overflow),'hidden');
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('body').evaluate(el => el.style.overflow),'');
    assert.ok(Math.abs(await page.evaluate(() => scrollY)-position)<2);
    await page.locator('.ios-tab-bar [aria-controls="syncModal"]').click();
    assert.ok(await page.locator('#syncModal').evaluate(el => el.matches(':modal')));
    await page.locator('#syncModal [onclick="toggleTheme()"]').click();
    assert.equal(await page.locator('html').getAttribute('data-theme'),'light');
    await page.locator('#syncModal .modal-close').click();
    await page.reload();
    assert.equal(await page.locator('html').getAttribute('data-theme'),'light');
    await page.locator('#mobileFilterButton').click();
    await page.setViewportSize({width:1200,height:900});
    await page.waitForFunction(() => !document.getElementById('filterModal').open);
    assert.ok(await page.locator('#advancedFilters').isVisible());
    assert.ok(await page.locator('.view-switchers').isVisible());
    assert.ok(!await page.locator('.ios-tab-bar').isVisible());
    await noOverflow();
    assert.deepEqual(errors,[]);
    console.log('PASS: 320/390/700px alignment, city/month touch selection and inversion in both themes, filter sheet, tabs, modal focus/Escape, scroll restoration, theme persistence, desktop resize, no JS errors');
  } finally {
    await browser.close();
  }
})().catch(error => {console.error(error);process.exitCode=1;});
