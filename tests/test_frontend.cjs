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
