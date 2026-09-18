// Run after python3 main.py. No npm packages needed.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('index.html', 'utf8');
const elements = new Map();
const element = id => {
  if (!elements.has(id)) elements.set(id, {innerHTML:'', innerText:'', textContent:'', style:{}, parentElement:{style:{}}, classList:{add(){},remove(){},toggle(){}}, showModal(){this.open=true},close(){this.open=false},querySelector:()=>({scrollTop:0}),appendChild(child){child.parentElement=this}});
  return elements.get(id);
};
let download;
const context = vm.createContext({Intl, Date, Blob, setTimeout: fn=>fn(), URL:{createObjectURL: b=>{download=b;return 'blob:test'},revokeObjectURL(){}}, document:{
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
  assert.ok(run(`formatDateDisplay('${date}')`).includes(`（${label}）`));
}
const data = JSON.parse(run('JSON.stringify(ACTIVITIES_DATA)'));
run(`renderAgenda([{...ACTIVITIES_DATA[0],start_time:'2026-09-20T16:30:00Z'}])`);
assert.match(element('viewAgenda').innerHTML,/2026年 9月 21日 \(拜一\)/);
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
  assert.match(element('modalDesc').innerText,/官方資料核對/);
  assert.match(element('modalTime').innerText,/～/);
}
// Month selection is a union of year-months, intersected with all other filters.
run('renderMonthFilters()');
assert.match(element('monthFilterOptions').innerHTML, /攏總/);
const monthKeys=[...new Set(data.map(a=>a.start_time.slice(0,7)))].sort();
for (const key of monthKeys) assert.ok(element('monthFilterOptions').innerHTML.includes(key));
if (monthKeys.length) {
  run(`toggleMonth('${monthKeys[0]}')`);
  assert.equal(run('getFilteredActivities().length'),data.filter(a=>a.start_time.startsWith(monthKeys[0])).length);
  if (monthKeys.length>1) {
    run(`toggleMonth('${monthKeys[monthKeys.length-1]}')`);
    assert.equal(run('getFilteredActivities().length'),data.filter(a=>[monthKeys[0],monthKeys[monthKeys.length-1]].includes(a.start_time.slice(0,7))).length);
    run(`toggleMonth('${monthKeys[0]}')`);
    assert.equal(run('getFilteredActivities().length'),data.filter(a=>a.start_time.startsWith(monthKeys[monthKeys.length-1])).length);
    assert.equal(run('calDate.toISOString().slice(0,7)'),monthKeys[monthKeys.length-1]);
  }
  run("currentCity='臺北市'");
  assert.equal(run('getFilteredActivities().length'),data.filter(a=>a.city==='臺北市' && JSON.parse(run('JSON.stringify([...selectedMonths])')).includes(a.start_time.slice(0,7))).length);
  run("currentCity='all';toggleMonth('all')");
  assert.equal(run('getFilteredActivities().length'),data.length);
  run(`toggleMonth('${monthKeys[0]}');toggleMonth('${monthKeys[0]}')`);
  assert.equal(run('selectedMonths.size'),0);
}
console.log('PASS: single/multiple month selection, year-month labels, city intersection, calendar alignment, clear and deselect');
// A crowded weekend must retain every event, including long titles and all cities.
run(`
  globalThis.originalActivities = ACTIVITIES_DATA.slice();
  const base = ACTIVITIES_DATA[0];
  const crowded = Array.from({length: 14}, (_, i) => ({...base,
    id: 'week-test-' + i, title: '週末活動 ' + i + ' 完整長標題 <不可當作標籤>',
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
assert.equal(element('calCurrentWeekLabel').innerText, '2026/9/14 – 2026/9/20');
assert.match(element('calWeekSummary').innerText, /這禮拜 14 場/);
run("currentCity='臺北市';renderCalendar()");
assert.equal((element('calGridDays').innerHTML.match(/data-activity-id=/g)||[]).length, 5);
run("currentCity='all';nextWeek()");
assert.match(element('calGridDays').innerHTML, /next-week/);
assert.doesNotMatch(element('calGridDays').innerHTML, /week-test-/);
run('prevWeek()');
assert.equal(element('calCurrentWeekLabel').innerText, '2026/9/14 – 2026/9/20');
run("calDate=new Date('2027-01-01T00:00:00Z');renderCalendar()");
assert.equal(element('calCurrentWeekLabel').innerText, '2026/12/28 – 2027/1/3');
assert.match(element('calWeekSummary').innerText, /這禮拜猶無合條件/);
run('nextWeek()');
assert.equal(element('calCurrentWeekLabel').innerText, '2027/1/4 – 2027/1/10');
run("calDate=new Date('2028-02-29T00:00:00Z');renderCalendar()");
assert.equal(element('calCurrentWeekLabel').innerText, '2028/2/28 – 2028/3/5');
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
  selectedMonths.add('2026-10');
`);
assert.equal(run("getFilteredActivities().map(a=>a.id).join(',')"),'taipei-october');
run("selectedMonths.add('2027-01')");
assert.equal(run('getFilteredActivities().length'),2);
assert.ok(!run("getFilteredActivities().some(a=>a.id==='year-2026')"));
run('selectedMonths.clear()');
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
    run(`selectedMonths.add('${monthKeys[0]}');exportCalendarFile()`);
    assert.equal(((await download.text()).match(/BEGIN:VEVENT/g)||[]).length,data.filter(a=>a.start_time.startsWith(monthKeys[0])).length);
    run('selectedMonths.clear()');
    run('downloadSingleIcs()');
    assert.equal(((await download.text()).match(/BEGIN:VEVENT/g)||[]).length,1);
    assert.ok((await download.text()).includes(data[0].ics_event));
  }
  console.log('PASS: JS syntax, filters, empty state, Taipei time, official link, review date, full/single ICS downloads');
})().catch(e=>{console.error(e);process.exitCode=1});
