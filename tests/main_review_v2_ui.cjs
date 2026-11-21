// Execute the real inline UI handlers with a minimal DOM; synthetic_test_only.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(process.argv[2],'utf8');
const payload=html.match(/<script type="application\/json" id="payload">([\s\S]*?)<\/script>/)[1];
const script=html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
const elements=new Map();
function element(id){if(!elements.has(id))elements.set(id,{value:'',textContent:'',files:[],append(){},click(){},showModal(){},close(){}});return elements.get(id);}
element('payload').textContent=payload;
const storage=new Map();
const context=vm.createContext({document:{getElementById:element,createElement:()=>({click(){}})},localStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},Blob,URL:{createObjectURL:()=>'',revokeObjectURL(){}},setTimeout:fn=>fn()});
vm.runInContext(script,context);
const get=()=>JSON.parse(vm.runInContext('JSON.stringify(review)',context));
function form(id,observed='yes'){
  element('reviewer').value=id;
  element('translationStatus').value='approved';element('imageStatus').value='approved';element('observed').value=observed;
}
function slot(value){element('slot').value=value;element('slot').onchange();}
(async()=>{
  form('synthetic_A');element('save').onclick();
  let data=get();assert.equal(data.decisions[0].reviewer_a.image_qa.status,'approved');assert.equal(data.decisions[0].reviewer_b.image_qa.status,'pending');
  const aJson=JSON.stringify(data);
  // Unsaved edits cannot be navigated away or downloaded.
  element('translationNotes').value='synthetic unsaved';element('download').onclick();assert.match(element('notice').textContent,/Lưu/);
  element('translationNotes').value='';
  element('restore').files=[{text:async()=>aJson}];await element('restore').onchange();
  slot('reviewer_b');form('synthetic_A');element('save').onclick();assert.match(element('notice').textContent,/hai người/);
  form('synthetic_B','no');element('save').onclick();assert.match(element('notice').textContent,/chưa khớp/);
  assert.equal(get().decisions[0].reviewer_b.image_qa.status,'pending');
  // B changes VI: retain A's old round in history, require A to review again.
  form('synthetic_B');element('vi').value='synthetic_test_only_changed';element('save').onclick();
  data=get();assert.equal(data.decisions[0].reviewer_a.translation.status,'pending');assert.equal(data.decisions[0].history.length,1);
  assert.equal(data.decisions[0].history[0].review.translation.reviewed_question_vi,'synthetic_test_only');
  assert.equal(data.decisions[0].reviewer_b.translation.reviewed_question_vi,'synthetic_test_only_changed');
  // B cannot overwrite A's identity in an occupied round.
  slot('reviewer_a');form('synthetic_A');element('save').onclick();
  data=get();assert.equal(data.decisions[0].reviewer_a.image_qa.status,'approved');
  form('synthetic_C');element('save').onclick();assert.match(element('notice').textContent,/ID khác/);
  assert.equal(get().decisions[0].reviewer_a.translation.reviewer_id,'synthetic_A');
  // Wrong-schema restore must not erase current decisions.
  const bad=structuredClone(data);bad.context.schema_version='main_review_v1';
  element('restore').files=[{text:async()=>JSON.stringify(bad)}];await element('restore').onchange();
  assert.match(element('notice').textContent,/v2/);assert.deepEqual(get(),data);
  fs.writeFileSync(process.argv[3],JSON.stringify(data,null,2)+'\n');
})().catch(e=>{process.stderr.write(e.stack);process.exitCode=1;});
