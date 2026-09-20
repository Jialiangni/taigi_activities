// Optional browser regression: NODE_PATH=<Playwright modules> node tests/test_mobile_browser.cjs
// BROWSER_EXECUTABLE may point at an installed Chrome; no personal profile is used.
// BROWSER_ENGINE=webkit selects Safari's engine; PLAYWRIGHT_MODULE may select a compatible runtime.
const assert = require('node:assert/strict');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {chromium,webkit} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const engine = process.env.BROWSER_ENGINE==='webkit' ? webkit : chromium;
  const browser = await engine.launch({headless:true,
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
    // A fresh visit must show selection before any theme toggle or saved preference.
    const assertSelectedPaint = async (theme) => {
      const paint = await page.locator('.filter-row [aria-pressed="true"],#monthFilterOptions [aria-pressed="true"]').evaluateAll(nodes => nodes.map(el => {
        const s=getComputedStyle(el);return {bg:s.backgroundColor,color:s.color,appearance:s.appearance};
      }));
      assert.ok(paint.length>=2);
      for (const style of paint) assert.deepEqual(style,{
        bg:theme==='dark'?'rgb(255, 255, 255)':'rgb(0, 0, 0)',
        color:theme==='dark'?'rgb(0, 0, 0)':'rgb(255, 255, 255)',appearance:'none'
      });
    };
    assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
    await assertSelectedPaint('dark');
    for (const city of ['臺北市','新北市','桃園市']) {
      await page.locator(`.filter-row [data-value="${city}"]`).tap();
      await page.locator('#monthFilterOptions button').nth(1).tap();
      await assertSelectedPaint('dark');
    }
    await page.reload();
    await assertSelectedPaint('dark');
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
      const month = await page.locator('#monthFilterOptions button').nth(1).boundingBox();
      for (const city of ['臺北市','新北市','桃園市']) {
        const box = await page.locator(`.filter-row [data-value="${city}"]`).boundingBox();
        assert.ok(Math.abs(box.width-month.width)<1 && Math.abs(box.height-month.height)<1,'City and month buttons have equal dimensions');
      }
    }
    await page.setViewportSize({width:390,height:844});
    await page.setViewportSize({width:320,height:844});
    await page.locator('.filter-row [data-value="桃園市"]').tap();
    assert.equal(await page.locator('.filter-row [data-value="桃園市"]').getAttribute('aria-pressed'),'true');
    await noOverflow();
    await page.locator('.filter-row [data-value="all"]').tap();
    await page.setViewportSize({width:390,height:844});
    // The lower mobile toggle and upper desktop toggle share one filter state.
    for (const theme of ['dark','light']) {
      await page.evaluate(t=>document.documentElement.setAttribute('data-theme',t),theme);
      for (const width of [320,390,700]) {
        await page.setViewportSize({width,height:844});
        const toggle=page.locator('.ios-tab-bar [data-weekend-filter]');
        assert.ok(await toggle.isVisible());
        assert.ok(!await page.locator('.weekend-desktop').isVisible());
        const box=await toggle.boundingBox();
        assert.ok(box.y>700 && box.width>=44 && box.height>=44);
        await toggle.tap();
        assert.equal(await toggle.getAttribute('aria-pressed'),'true');
        const weekends=await page.evaluate(()=>ACTIVITIES_DATA.filter(a=>[0,6].includes(new Date(new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Taipei',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(a.start_time))+'T00:00:00Z').getUTCDay())).length);
        assert.equal(await count(),weekends);
        const paint=await toggle.evaluate(el=>getComputedStyle(el).backgroundColor);
        assert.notEqual(paint,'rgba(0, 0, 0, 0)');
        await page.locator('[data-tab="agenda"]').tap();
        assert.equal(await count(),weekends);
        assert.equal(await toggle.getAttribute('aria-pressed'),'true');
        await page.locator('[data-tab="calendar"]').tap();
        assert.ok(await page.locator('#viewCalendar').isVisible());
        assert.equal(await toggle.getAttribute('aria-pressed'),'true');
        await page.setViewportSize({width:1200,height:900});
        const desktop=page.locator('.weekend-desktop');
        assert.ok(await desktop.isVisible());
        assert.ok((await desktop.boundingBox()).y<500);
        assert.equal(await desktop.getAttribute('aria-pressed'),'true');
        await desktop.click();
        assert.equal(await count(),initialCount);
        await page.setViewportSize({width,height:844});
        assert.equal(await toggle.getAttribute('aria-pressed'),'false');
        await page.locator('[data-tab="grid"]').tap();
        await noOverflow();
      }
    }
    await page.setViewportSize({width:390,height:844});
    // Selection is a persistent visual state after a real touch, including exclusive month choices.
    for (const theme of ['dark','light']) {
      await page.evaluate(t => document.documentElement.setAttribute('data-theme',t),theme);
      await page.locator('.filter-row [data-value="新北市"]').tap();
      assert.equal(await page.locator('.filter-row [data-value="新北市"]').getAttribute('aria-pressed'),'true');
      assert.equal(await page.locator('.filter-row [data-value="all"]').getAttribute('aria-pressed'),'false');
      await page.locator('#monthFilterOptions button').nth(1).tap();
      await page.locator('#monthFilterOptions button').nth(2).tap();
      assert.equal(await page.locator('#monthFilterOptions [aria-pressed="true"]').count(),1);
      assert.equal(await page.locator('#monthFilterOptions button').nth(1).getAttribute('aria-pressed'),'false');
      assert.equal(await page.locator('#monthFilterOptions button').nth(2).getAttribute('aria-pressed'),'true');
      await assertSelectedPaint(theme);
      const selection = await page.evaluate(() => {
        const city = document.querySelector('.filter-row [aria-pressed="true"]');
        const month = document.querySelector('#monthFilterOptions [aria-pressed="true"]');
        const off = document.querySelector('.filter-row [data-value="all"]');
        const style = el => {const s=getComputedStyle(el);return {bg:s.backgroundColor,color:s.color};};
        return {city:style(city),month:style(month),off:style(off),cityText:getComputedStyle(city.querySelector('.badge-city')).color,
          expected:ACTIVITIES_DATA.filter(a=>a.city==='新北市' && selectedMonth === taipeiDateKey(new Date(a.start_time)).slice(0,7)).length};
      });
      assert.deepEqual(selection.city,selection.month);
      assert.equal(selection.city.bg,theme==='dark' ? 'rgb(255, 255, 255)' : 'rgb(0, 0, 0)');
      assert.equal(selection.city.color,theme==='dark' ? 'rgb(0, 0, 0)' : 'rgb(255, 255, 255)');
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
    // Safari does not focus buttons on pointer activation; establish keyboard focus for this check.
    await page.locator('#mobileFilterButton').focus();
    await page.keyboard.press('Enter');
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
    const cityAll = await page.locator('.filter-row [data-value="all"]').boundingBox();
    const monthAll = await page.locator('[data-month="all"]').boundingBox();
    assert.ok(Math.abs(cityAll.x-monthAll.x)<1 && Math.abs(cityAll.width-monthAll.width)<1,'Desktop all buttons align');
    await noOverflow();

    // An external-browser handoff keeps the selected activity and reopens its details.
    const activityId = await page.evaluate(() => ACTIVITIES_DATA[0].id);
    await page.goto(pathToFileURL(path.resolve('index.html')).href+'?activity='+encodeURIComponent(activityId));
    assert.ok(await page.locator('#eventModal').evaluate(el => el.open && el.matches(':modal')));
    assert.equal(await page.locator('#modalTitle').innerText(),await page.evaluate(id => {
      const act=ACTIVITIES_DATA.find(item => item.id===id); return act.title_taigi || act.title;
    },activityId));

    // LINE on iPhone gets a Safari handoff link and an exact fallback instruction.
    const lineContext = await browser.newContext({viewport:{width:390,height:844},hasTouch:true,isMobile:true,
      userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Line/15.15.0'});
    const linePage = await lineContext.newPage();
    await linePage.goto(pathToFileURL(path.resolve('index.html')).href);
    await linePage.locator('#viewGrid .card-detail').first().tap();
    assert.equal(await linePage.locator('#modalSingleIcsBtn').innerText(),'🍏 用 Safari 加到 Apple 日曆');
    assert.match(await linePage.locator('#modalSingleIcsBtn').getAttribute('href'),/^https:\/\/jialiangni\.github\.io\/taigi_activities\/\?activity=.*&openExternalBrowser=1$/);
    assert.ok(await linePage.locator('#lineCalendarHelp').isVisible());
    assert.match(await linePage.locator('#lineCalendarHelp').innerText(),/右上角「⋯」→「用預設瀏覽器開啟」/);
    await lineContext.close();
    assert.deepEqual(errors,[]);
    console.log('PASS: mobile layout, LINE iPhone Safari handoff, activity deep link, dialogs, theme persistence and no JS errors');
  } finally {
    await browser.close();
  }
})().catch(error => {console.error(error);process.exitCode=1;});
