// Run after python3 main.py. No npm packages needed.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('index.html', 'utf8');
const elements = new Map();
const element = id => {
  if (!elements.has(id)) elements.set(id, {innerHTML:'', innerText:'', textContent:'', style:{}, parentElement:{style:{}}, classList:{add(){},remove(){}}});
  return elements.get(id);
};
let download;
const context = vm.createContext({Intl, Date, Blob, setTimeout: fn=>fn(), URL:{createObjectURL: b=>{download=b;return 'blob:test'},revokeObjectURL(){}}, document:{
  addEventListener(){},getElementById:element,body:{style:{},appendChild(){},removeChild(){}},
  createElement:()=>({click(){}})
}});
for (const [,script] of html.matchAll(/<script>([\s\S]*?)<\/script>/g)) vm.runInContext(script,context);
const run = code => vm.runInContext(code,context);
const data = JSON.parse(run('JSON.stringify(ACTIVITIES_DATA)'));
assert.equal(run('getFilteredActivities().length'),data.length);
run("currentPrice='free'");
assert.equal(run('getFilteredActivities().length'),data.filter(a=>a.is_free===true).length);
run("currentPrice='paid'");
assert.equal(run('getFilteredActivities().length'),data.filter(a=>a.is_free===false).length);
run("currentPrice='all';currentCity='臺北市'");
run('renderGrid(getFilteredActivities())');
if (!data.some(a=>a.city==='臺北市')) assert.match(element('viewGrid').innerHTML,/沒有已核實場次/);
run("currentCity='all';renderGrid(getFilteredActivities())");
assert.equal((element('viewGrid').innerHTML.match(/class="event-card"/g)||[]).length,data.length);
assert.match(run("formatDateDisplay('2026-09-20T14:00:00+08:00')"),/14:00/);
if (data.length) {
  run('openModal(ACTIVITIES_DATA[0].id)');
  assert.equal(element('modalTicketLink').href,data[0].source_url);
  assert.match(element('modalDesc').innerText,/官方資料核對/);
  assert.match(element('modalTime').innerText,/～/);
}
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
assert.match(element('calWeekSummary').innerText, /本週 14 場/);
run("currentCity='臺北市';renderCalendar()");
assert.equal((element('calGridDays').innerHTML.match(/data-activity-id=/g)||[]).length, 5);
run("currentCity='all';nextWeek()");
assert.match(element('calGridDays').innerHTML, /next-week/);
assert.doesNotMatch(element('calGridDays').innerHTML, /week-test-/);
run('prevWeek()');
assert.equal(element('calCurrentWeekLabel').innerText, '2026/9/14 – 2026/9/20');
run("calDate=new Date('2027-01-01T00:00:00Z');renderCalendar()");
assert.equal(element('calCurrentWeekLabel').innerText, '2026/12/28 – 2027/1/3');
assert.match(element('calWeekSummary').innerText, /本週無符合條件/);
run('nextWeek()');
assert.equal(element('calCurrentWeekLabel').innerText, '2027/1/4 – 2027/1/10');
run("calDate=new Date('2028-02-29T00:00:00Z');renderCalendar()");
assert.equal(element('calCurrentWeekLabel').innerText, '2028/2/28 – 2028/3/5');
assert.equal(run("taipeiDateKey(new Date('2026-09-20T16:30:00Z'))"), '2026-09-21');
run('goToToday()');
assert.equal(run('calDate.toISOString().slice(0,10)'), run('taipeiDateKey()'));
assert.doesNotMatch(html, /max-height:\s*60px|prevMonth|nextMonth|月曆檢視/);
assert.match(html, /white-space: normal/);
run('ACTIVITIES_DATA.splice(0, ACTIVITIES_DATA.length, ...originalActivities)');
console.log('PASS: crowded week (14 events), city colors/filter, full titles, week navigation, year/leap boundaries, Taipei dates, empty week');
(async()=>{
  run('exportCalendarFile()');
  assert.equal(await download.text(),fs.readFileSync('taigi_activities.ics','utf8'));
  if(data.length){
    run('downloadSingleIcs()');
    assert.equal(((await download.text()).match(/BEGIN:VEVENT/g)||[]).length,1);
    assert.ok((await download.text()).includes(data[0].ics_event));
  }
  console.log('PASS: JS syntax, filters, empty state, Taipei time, official link, review date, full/single ICS downloads');
})().catch(e=>{console.error(e);process.exitCode=1});
