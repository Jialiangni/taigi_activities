// Run after python3 main.py. No npm packages needed.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('index.html', 'utf8');
const elements = new Map();
const element = id => {
  if (!elements.has(id)) elements.set(id, {innerHTML:'', innerText:'', textContent:'', style:{}, parentElement:{style:{}}, classList:{add(){},remove(){},toggle(){}}, showModal(){this.open=true},close(){this.open=false},querySelector:()=>({scrollTop:0}),appendChild(child){child.parentElement=this}});
  const result = elements.get(id);
  result.focus = () => { result.focused = true; };
  result.removeAttribute = name => {delete result[name]};
  return result;
};
let download;
const context = vm.createContext({window:{scrollTo(){}},Intl, Date, Blob, URLSearchParams, navigator:{userAgent:'Mozilla/5.0 (iPhone) Version/18.0 Mobile Safari/604.1'}, location:{protocol:'https:',origin:'https://example.test',pathname:'/taigi_activities/',search:''}, setTimeout: fn=>fn(), URL:{createObjectURL: b=>{download=b;return 'blob:test'},revokeObjectURL(){}}, document:{
  addEventListener(){},querySelectorAll:()=>[],querySelector:element,getElementById:element,body:{style:{},appendChild(){},removeChild(){}},
  createElement:()=>({click(){}})
}});
for (const [,script] of html.matchAll(/<script>([\s\S]*?)<\/script>/g)) vm.runInContext(script,context);
const run = code => vm.runInContext(code,context);
// Fresh visits and unavailable/invalid storage start dark; explicit preferences persist.
let theme, savedTheme=null;
context.document.documentElement={setAttribute:(key,value)=>{theme=value},getAttribute:()=>theme};
context.localStorage={getItem:()=>savedTheme,setItem:(key,value)=>{savedTheme=value}};
assert.match(html, /<html[^>]+data-theme="dark"/);
run('initTheme()');assert.equal(theme,'dark');
run('toggleTheme()');assert.equal(theme,'light');assert.equal(savedTheme,'light');
run('initTheme()');assert.equal(theme,'light');
run('toggleTheme()');assert.equal(theme,'dark');assert.equal(savedTheme,'dark');
savedTheme='invalid';run('initTheme()');assert.equal(theme,'dark');
context.localStorage={getItem(){throw Error('blocked')},setItem(){throw Error('blocked')}};
run('initTheme()');assert.equal(theme,'dark');run('toggleTheme()');assert.equal(theme,'light');
for(const [i,label] of ['拜一','拜二','拜三','拜四','拜五','拜六','禮拜'].entries()){
  const date=`2026-09-${14+i}T14:00:00+08:00`;
  assert.ok(run(`formatDateDisplay('${date}')`).includes(` ${label} `));
}
assert.equal(run("formatDateDisplay('2026-09-19T10:00:00+08:00')"),'2026∙09∙19 拜六 10:00');
assert.equal(run("formatDateDisplay('2026-09-20T16:05:00Z')"),'2026∙09∙21 拜一 00:05');
assert.equal(run("formatEventTime('2026-10-04T13:00:00+08:00','2026-10-04T17:30:00+08:00')"),'2026∙10∙04 禮拜 13:00 - 17:30');
assert.equal(run("formatEventTime('2026-10-04T23:00:00+08:00','2026-10-05T01:00:00+08:00')"),'2026∙10∙04 禮拜 23:00 - 2026∙10∙05 拜一 01:00');
const data = JSON.parse(run('JSON.stringify(ACTIVITIES_DATA)'));
const sessionEditions=['accupass','opentix'].flatMap(source=>JSON.parse(fs.readFileSync(`data/${source}_editorial.json`,'utf8')));
for (const edition of sessionEditions) {
  const activity=data.find(a=>a.id===edition.activity_id);
  if (!activity) continue;
  assert.equal(activity.summary_taigi,edition.summary_taigi);
  assert.equal(activity.description_taigi,edition.description_taigi);
  run(`renderGrid([ACTIVITIES_DATA.find(a=>a.id===${JSON.stringify(activity.id)})]);openModal(${JSON.stringify(activity.id)})`);
  assert.ok(element('viewGrid').innerHTML.includes(edition.summary_taigi));
  assert.ok(element('modalDesc').innerText.startsWith(edition.description_taigi));
}
const priorityAudit=JSON.parse(fs.readFileSync('data/audit/2026-09-19-accupass-primary.json','utf8'));
for (const [directoryId, decision] of Object.entries(priorityAudit.decisions)) {
  assert.ok(!data.some(a=>a.id===directoryId),'Directory duplicate or unverified primary must not be published');
  const primary=data.find(a=>a.id===decision.primary_activity_id);
  if (primary) {
    assert.equal(primary.source_url,decision.primary_url);
    assert.ok(primary.raw_metadata.supplemental_description);
    assert.ok(primary.description_taigi.length>primary.summary_taigi.length);
  }
}
for(const event of data.filter(a=>a.title_taigi!==a.title)){
  run(`renderGrid([ACTIVITIES_DATA.find(a=>a.id===${JSON.stringify(event.id)})]);renderAgenda([ACTIVITIES_DATA.find(a=>a.id===${JSON.stringify(event.id)})]);openModal(${JSON.stringify(event.id)})`);
  assert.ok(element('viewGrid').innerHTML.includes(event.title_taigi));
  assert.ok(element('viewAgenda').innerHTML.includes(event.title_taigi));
  assert.equal(element('modalTitle').innerText,event.title_taigi);
  for(const title of [event.title,event.title_taigi]){
    run(`searchQuery=${JSON.stringify(title.toLowerCase())}`);
    assert.ok(run('getFilteredActivities()').some(a=>a.id===event.id));
  }
}
run("searchQuery=''");
run(`renderAgenda([{...ACTIVITIES_DATA[0],start_time:'2026-09-20T16:30:00Z'}])`);
assert.match(element('viewAgenda').innerHTML,/2026∙09∙21 拜一/);
assert.equal(run('getFilteredActivities().length'),data.length);
run("currentPrice='free'");
assert.equal(run('getFilteredActivities().length'),data.filter(a=>a.is_free===true).length);
run("currentPrice='paid'");
assert.equal(run('getFilteredActivities().length'),data.filter(a=>a.is_free===false).length);
run("currentPrice='all';currentCity='臺北市'");
run('renderGrid(getFilteredActivities())');
if (!data.some(a=>a.city==='臺北市')) assert.match(element('viewGrid').innerHTML,/猶無核實的場次/);
run("currentCity='all';renderGrid(getFilteredActivities())");
assert.equal((element('viewGrid').innerHTML.match(/class="event-card"/g)||[]).length,data.length);
assert.match(run("formatDateDisplay('2026-09-20T14:00:00+08:00')"),/14:00/);
if (data.length) {
  run('openModal(ACTIVITIES_DATA[0].id)');
  assert.equal(element('modalTicketLink').href,data[0].source_url);
  assert.equal(element('modalPrice').innerText,data[0].price_info_taigi);
  assert.ok(element('modalDesc').innerText.startsWith(data[0].description_taigi));
  assert.match(element('modalDesc').innerText,/官方資料確認/);
  assert.doesNotMatch(element('modalTime').innerText,/～/);
  assert.equal(element('modalTicketLink').textContent,'🌐 活動公告 ↗');
  assert.equal(element('modalGoogleSearchLink').innerHTML,'🔍 Google 揣報名／買票 ↗');
}
// Missing translation must retain the supplied description, including literal markup.
run(`
  const fallbackBase = ACTIVITIES_DATA[0];
  ACTIVITIES_DATA.push({...fallbackBase, id:'intro-fallback-test', description_taigi:'',
    description:'官方提供的活動介紹 <不可變成 HTML>'});
  openModal('intro-fallback-test');
`);
assert.ok(element('modalDesc').innerText.startsWith('簡介原文：官方提供的活動介紹 <不可變成 HTML>'));
assert.doesNotMatch(element('modalDesc').innerText,/猶待整理/);
run("ACTIVITIES_DATA.pop()");
const registrationEvent=data.find(a=>a.source_platform==='台語站' && a.registration_url);
for (const event of data.filter(a=>a.source_platform==='台語站' && a.summary_taigi && a.summary_taigi!==a.description_taigi)) {
  run(`renderGrid([ACTIVITIES_DATA.find(a=>a.id===${JSON.stringify(event.id)})]);openModal(${JSON.stringify(event.id)})`);
  assert.ok(element('viewGrid').innerHTML.includes(event.summary_taigi));
  assert.ok(element('modalDesc').innerText.startsWith(event.description_taigi));
  assert.ok(event.description_taigi.length>event.summary_taigi.length);
  assert.doesNotMatch(event.description_taigi,/台語站收錄的台語活動/);
}
assert.ok(registrationEvent);
run(`openModal(${JSON.stringify(registrationEvent.id)})`);
assert.equal(element('modalRegistrationLink').href,registrationEvent.registration_url);
assert.equal(element('modalRegistrationLink').hidden,false);
assert.equal(element('modalTicketLink').href,registrationEvent.source_url);
// Poster is the verified original, can open full size, and never leaves a broken image.
const posterEvent = data.find(a=>a.source_platform==='台語站' && a.cover_image);
assert.ok(posterEvent);
run(`openModal(${JSON.stringify(posterEvent.id)})`);
assert.equal(element('modalImg').src,posterEvent.cover_image);
assert.equal(element('modalPosterLink').href,posterEvent.cover_image);
assert.equal(element('modalPosterLink').style.display,'block');
for (const event of data.filter(a=>a.cover_image)) {
  run(`openModal(${JSON.stringify(event.id)})`);
  assert.equal(element('modalImg').src,event.cover_image);
  assert.equal(element('modalPosterLink').href,event.cover_image);
  assert.equal(element('modalPosterLink').style.display,'block');
}
element('modalImg').onerror();
assert.equal(element('modalPosterLink').style.display,'none');
run(`openModal(${JSON.stringify(posterEvent.id)})`);
assert.equal(element('modalPosterLink').style.display,'block');
const noPosterEvent = data.find(a=>!a.cover_image);
run(`openModal(${JSON.stringify(noPosterEvent.id)})`);
assert.equal(element('modalPosterLink').style.display,'none');
assert.equal(element('modalImg').src,undefined);
assert.equal(element('modalPosterLink').href,undefined);
// Month selection is exclusive; selecting the same month keeps it selected.
assert.equal(run("monthLabel('2026-09')"),'2026∙09');
run('renderMonthFilters()');
assert.match(element('monthFilterOptions').innerHTML, /攏選/);
const monthKeys=[...new Set(data.map(a=>a.start_time.slice(0,7)))].sort();
for (const key of monthKeys) assert.ok(element('monthFilterOptions').innerHTML.includes(key));
if (monthKeys.length) {
  run(`setMonth('${monthKeys[0]}')`);
  assert.equal(run('getFilteredActivities().length'),data.filter(a=>a.start_time.startsWith(monthKeys[0])).length);
  if (monthKeys.length>1) {
    const last=monthKeys[monthKeys.length-1];
    run(`setMonth('${last}')`);
    assert.equal(run('selectedMonth'),last);
    assert.equal(run('getFilteredActivities().length'),data.filter(a=>a.start_time.startsWith(last)).length);
    assert.equal(run('calDate.toISOString().slice(0,7)'),last);
    run(`setMonth('${last}')`);
    assert.equal(run('selectedMonth'),last);
  }
  run("currentCity='臺北市'");
  assert.equal(run('getFilteredActivities().length'),data.filter(a=>a.city==='臺北市' && a.start_time.startsWith(run('selectedMonth'))).length);
  run("currentCity='all';setMonth('all')");
  assert.equal(run('selectedMonth'),'');
  assert.equal(run('getFilteredActivities().length'),data.length);
}
for (const view of ['calendar','grid','calendar','agenda']) {
  run(`switchView('${view}')`);
  assert.equal(element('filterSummary').style.display,view==='calendar'?'none':'flex');
}
assert.doesNotMatch(element('calWeekSummary').innerText,/臺北時間/);
assert.doesNotMatch(html,/aria-label="城市顏色圖例"|會當揀幾若个月/);
assert.match(html,/<span class="filter-label">城市<\/span>/);
console.log('PASS: exclusive month selection, repeat selection, city intersection, calendar alignment, clear and view-specific summary');
// A crowded weekend must retain every event, including long titles and all cities.
run(`
  globalThis.originalActivities = ACTIVITIES_DATA.slice();
  const base = ACTIVITIES_DATA[0];
  const crowded = Array.from({length: 14}, (_, i) => ({...base,
    id: 'week-test-' + i, title: '週末活動 ' + i + ' 完整長標題 <不可當作標籤>', title_taigi: '',
    city: ['臺北市', '新北市', '桃園市'][i % 3],
    start_time: '2026-09-20T' + String(8 + Math.floor(i / 2)).padStart(2, '0') + ':00:00+08:00',
    end_time: null
  }));
  ACTIVITIES_DATA.splice(0, ACTIVITIES_DATA.length, ...crowded.reverse(),
    {...base, id: 'next-week', start_time: '2026-09-21T09:00:00+08:00'},
    {...base, id: 'prior-week', start_time: '2026-09-13T09:00:00+08:00'});
  currentCity = currentPrice = currentCategory = currentPlatform = 'all';
  searchQuery = '';
  calDate = new Date('2026-09-20T00:00:00Z');
  renderCalendar();
`);
let week = element('calGridDays').innerHTML;
assert.equal((week.match(/class="cal-cell /g)||[]).length, 7);
assert.equal((week.match(/data-activity-id=/g)||[]).length, 14);
assert.match(week, /week-test-13/);
assert.doesNotMatch(week, /next-week|prior-week/);
assert.match(week, /&lt;不可當作標籤&gt;/);
assert.match(week, /city-taipei/);
assert.match(week, /city-newtaipei/);
assert.match(week, /city-taoyuan/);
assert.ok(week.indexOf('week-test-0"') < week.indexOf('week-test-13"'));
assert.equal(element('calCurrentWeekLabel').innerText, '2026∙09∙14 – 2026∙09∙20');
assert.match(element('calWeekSummary').innerText, /這禮拜 14 場/);
assert.equal((element('calWeekDays').innerHTML.match(/aria-pressed=/g)||[]).length,7);
run("selectCalendarDay('2026-09-20')");
assert.equal((element('calGridDays').innerHTML.match(/class=\"cal-cell /g)||[]).length,1);
assert.equal((element('calGridDays').innerHTML.match(/data-activity-id=/g)||[]).length,14);
assert.match(element('calWeekDays').innerHTML,/id="cal-pick-2026-09-20" aria-pressed="true"/);
assert.equal(element('cal-pick-2026-09-20').focused,true);
run("selectCalendarDay('2026-09-14')");
assert.match(element('calGridDays').innerHTML,/selected-day/);
assert.match(element('calGridDays').innerHTML,/這工猶無合條件/);
assert.match(element('calWeekSummary').innerText,/0 場/);
run("selectCalendarDay('2026-09-21')");
assert.equal(run('selectedCalendarDay'),'2026-09-14');
run("selectCalendarDay('2026-09-14')");
assert.equal(run('selectedCalendarDay'),'');
assert.equal((element('calGridDays').innerHTML.match(/class=\"cal-cell /g)||[]).length,7);
run("currentCity='臺北市';renderCalendar()");
assert.equal((element('calGridDays').innerHTML.match(/data-activity-id=/g)||[]).length, 5);
run("selectCalendarDay('2026-09-20');currentCity='all';nextWeek()");
assert.equal(run('selectedCalendarDay'),'');
assert.match(element('calGridDays').innerHTML, /next-week/);
assert.doesNotMatch(element('calGridDays').innerHTML, /week-test-/);
run('prevWeek()');
assert.equal(element('calCurrentWeekLabel').innerText, '2026∙09∙14 – 2026∙09∙20');
run("calDate=new Date('2027-01-01T00:00:00Z');renderCalendar()");
assert.equal(element('calCurrentWeekLabel').innerText, '2026∙12∙28 – 2027∙01∙03');
assert.match(element('calWeekSummary').innerText, /這禮拜猶無合條件/);
run('nextWeek()');
assert.equal(element('calCurrentWeekLabel').innerText, '2027∙01∙04 – 2027∙01∙10');
run("calDate=new Date('2028-02-29T00:00:00Z');renderCalendar()");
assert.equal(element('calCurrentWeekLabel').innerText, '2028∙02∙28 – 2028∙03∙05');
assert.equal(run("taipeiDateKey(new Date('2026-09-20T16:30:00Z'))"), '2026-09-21');
run('goToToday()');
assert.equal(run('calDate.toISOString().slice(0,10)'), run('taipeiDateKey()'));
assert.doesNotMatch(html, /max-height:\s*60px|prevMonth|nextMonth|月曆檢視/);
assert.match(html, /white-space:\s*normal/);
run(`
  ACTIVITIES_DATA.splice(0, ACTIVITIES_DATA.length,
    {id:'year-2026', start_time:'2026-01-01T10:00:00+08:00'},
    {id:'year-2027', start_time:'2027-01-01T10:00:00+08:00'},
    {id:'taipei-october', start_time:'2026-09-30T16:30:00Z'});
  selectedMonth='2026-10';
`);
assert.equal(run("getFilteredActivities().map(a=>a.id).join(',')"),'taipei-october');
run("selectedMonth='2027-01'");
assert.equal(run('getFilteredActivities().length'),1);
assert.ok(!run("getFilteredActivities().some(a=>a.id==='year-2026')"));
run("selectedMonth=''");
run('ACTIVITIES_DATA.splice(0, ACTIVITIES_DATA.length, ...originalActivities)');
console.log('PASS: crowded week (14 events), city colors/filter, full titles, week navigation, year/leap boundaries, Taipei dates, empty week');
(async()=>{
  // Source selection must affect the cards, week, count and exported ICS together.
  const sources=[...new Set(data.map(a=>a.source_platform))];
  for(const source of sources){
    run(`setPlatformFilter(${JSON.stringify(source)})`);
    assert.equal(run('getFilteredActivities().length'),data.filter(a=>a.source_platform===source).length);
    assert.equal((element('viewGrid').innerHTML.match(/class="event-card"/g)||[]).length,data.filter(a=>a.source_platform===source).length);
    run('exportCalendarFile()');
    assert.equal(((await download.text()).match(/BEGIN:VEVENT/g)||[]).length,data.filter(a=>a.source_platform===source).length);
  }
  run("setPlatformFilter('all')");
  run('exportCalendarFile()');
  assert.equal(await download.text(),fs.readFileSync('taigi_activities.ics','utf8'));
  if(data.length){
    run(`setMonth('${monthKeys[0]}');exportCalendarFile()`);
    assert.equal(((await download.text()).match(/BEGIN:VEVENT/g)||[]).length,data.filter(a=>a.start_time.startsWith(monthKeys[0])).length);
    run("selectedMonth=''");
    // Every details link opens its own hosted ICS; no blob or forced download.
    const anchor = html.match(/<a id="modalSingleIcsBtn"[^>]*>/)[0];
    assert.doesNotMatch(anchor,/\bdownload\b|\bonclick\b|\btarget\b/);
    for(const event of data){
      run(`openModal(${JSON.stringify(event.id)})`);
      assert.equal(element('modalSingleIcsBtn').href,event.ics_path+'?v=plain-notes-2');
      assert.match(event.ics_path,/^calendar-events\/[a-f0-9]{64}\.ics$/);
      const raw=fs.readFileSync(event.ics_path,'utf8');
      assert.equal((raw.match(/BEGIN:VEVENT/g)||[]).length,1);
      assert.ok(raw.includes(event.ics_event));
      assert.ok(!raw.replace(/\r\n /g,'').includes('第一步：先看預覽'));
    }
    context.navigator.userAgent='Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Line/15.15.0';
    run(`openModal(${JSON.stringify(data[0].id)})`);
    assert.equal(element('modalSingleIcsBtn').href,'https://example.test/taigi_activities/?activity='+encodeURIComponent(data[0].id)+'&openExternalBrowser=1');
    assert.equal(element('modalSingleIcsBtn').textContent,'🍏 用 Safari 加到 Apple 日曆');
    assert.equal(element('lineCalendarHelp').hidden,false);
    context.navigator.userAgent='Mozilla/5.0 (iPhone) Version/18.0 Mobile Safari/604.1';
    context.location.protocol='file:';
    run(`openModal(${JSON.stringify(data[0].id)})`);
    assert.equal(element('modalSingleIcsBtn').href,'https://jialiangni.github.io/taigi_activities/'+data[0].ics_path+'?v=plain-notes-2');
  }
  console.log('PASS: JS syntax, filters, Taipei time, official links, filtered ICS and hosted single-event ICS links');
})().catch(e=>{console.error(e);process.exitCode=1});
