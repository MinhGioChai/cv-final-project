// Execute actual inline handlers with a minimal DOM. Synthetic_test_only; no real human decisions.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(process.argv[2],'utf8');
const payload=html.match(/<script type="application\/json" id="payload">([\s\S]*?)<\/script>/)[1];
const script=html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
const elements=new Map();
function element(id){if(!elements.has(id)){let value='';const e={textContent:'',checked:false,hidden:false,files:[],append(o){if(o.id)elements.set(o.id,o);},click(){}};Object.defineProperty(e,'value',{get:()=>value,set:v=>{value=String(v);}});elements.set(id,e);}return elements.get(id);}
element('payload').textContent=payload;
const storage=new Map(),downloads=[];
const sandbox={document:{getElementById:element,createElement:()=>({value:'',textContent:'',click(){}})},window:{},
 localStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},structuredClone,Blob,
 URL:{createObjectURL:b=>{downloads.push(b);return 'blob:synthetic';},revokeObjectURL(){}},setTimeout:fn=>fn()};
const ctx=vm.createContext(sandbox);vm.runInContext(script,ctx);
const get=()=>JSON.parse(vm.runInContext('JSON.stringify(review)',ctx));
function setForm(label,status='resolved'){element('reviewer').value='synthetic_test_only_user';element('finalLabel').value=label;
 element('status').value=status;element('translationChecked').checked=true;element('imageChecked').checked=true;}
(async()=>{
 assert.equal(get().decisions.filter(d=>d.status==='resolved').length,0);
 setForm('no');element('save').onclick();assert.match(element('notice').textContent,/lý do/);assert.equal(get().decisions[0].status,'pending');
 element('notes').value='synthetic label correction';element('imageChecked').checked=false;element('save').onclick();assert.match(element('notice').textContent,/hai ô/);
 element('imageChecked').checked=true;element('save').onclick();let saved=get();assert.equal(saved.decisions[0].resolved_ground_truth,'no');assert.equal(saved.decisions[0].status,'resolved');
 element('vi').value='unsaved synthetic';element('next').onclick();assert.match(element('notice').textContent,/chưa lưu/);assert.equal(vm.runInContext('index',ctx),0);
 element('download').onclick();assert.equal(downloads.length,0);
 element('vi').value=saved.decisions[0].question_vi;element('download').onclick();assert.equal(downloads.length,1);const partial=await downloads[0].text();
 const bad=JSON.parse(partial);bad.context.policy='wrong';element('restore').files=[{text:async()=>JSON.stringify(bad)}];await element('restore').onchange();assert.deepEqual(get(),saved);
 element('restore').files=[{text:async()=>partial}];await element('restore').onchange();assert.deepEqual(get(),saved);
 // Changing a recorded decision retains its actual prior record in history.
 element('useSource').onclick();element('notes').value='synthetic kept source after recheck';element('save').onclick();
 assert.equal(get().decisions[0].resolved_ground_truth,'yes');assert.equal(get().decisions[0].history[0].resolved_ground_truth,'no');
 element('next').onclick();assert.equal(vm.runInContext('index',ctx),1);
 setForm('-1');element('save').onclick();assert.match(element('notice').textContent,/số nguyên/);
 setForm('0');element('notes').value='synthetic counted zero';element('save').onclick();assert.equal(get().decisions[1].resolved_ground_truth,0);
 assert.equal(get().decisions.filter(d=>d.status==='resolved').length,2);
 // Storage failure must still permit a validated JSON download.
 vm.runInContext('localStorage.setItem=()=>{throw Error("synthetic storage denied")}',ctx);
 element('notes').value='synthetic zero rechecked';assert.equal(element('save').onclick(),true,element('notice').textContent);assert.match(element('storageNote').textContent,/Không lưu tạm/);
 element('download').onclick();assert.equal(downloads.length,2);const complete=JSON.parse(await downloads[1].text());
 fs.writeFileSync(process.argv[3],JSON.stringify(complete,null,2)+'\n');
})().catch(e=>{process.stderr.write(e.stack);process.exitCode=1;});
