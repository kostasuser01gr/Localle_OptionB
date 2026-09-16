// Deterministic business engine. LLM interprets; this node decides.
const inbound=$('Apply Runtime Config').item.json;
const extractedRaw=$json.output ?? $json;
// n8n 1.117.3 Code-node sandboxes do not expose structuredClone. This contract only contains JSON data, so JSON cloning is deterministic here.
const cloneJson=value=>JSON.parse(JSON.stringify(value));
const incoming=cloneJson(extractedRaw);
const existingRow=$('Lookup Request by Thread').item.json || {};
let existing={};
try { existing=existingRow.payload_json ? JSON.parse(existingRow.payload_json) : {}; } catch(e){ existing={}; }
const minConf=Number(inbound.runtime?.minimum_confidence ?? 0.85);
const REQUIRED=['customer_name','phone','pickup.date_text','return.date_text','vehicle.category'];
const HIGH=new Set(['return_before_pickup','conflicting_dates','conflicting_customer_identity','conflicting_phone','multiple_requests_in_one_message','conflicting_customer_name','conflicting_pickup_date_text','conflicting_return_date_text','conflicting_vehicle_category']);
const CORRECTABLE=new Set(['phone','email','pickup.date_text','pickup.date_iso','pickup.time_text','pickup.location','return.date_text','return.date_iso','return.time_text','return.location','vehicle.category','vehicle.category_normalized','vehicle.transmission','vehicle.model_text','competitor.price_text']);
const ALWAYS_MUTABLE=new Set(['language']);
const get=(o,p)=>p.split('.').reduce((v,k)=>v&&typeof v==='object'?v[k]:null,o);
const present=v=>!(v===null||v===undefined||(typeof v==='string'&&!v.trim()));
const neutral=(p,v)=>p==='vehicle.transmission'&&typeof v==='string'&&['unspecified','unknown','not specified'].includes(v.trim().toLowerCase());
const eq=(a,b)=>typeof a==='string'&&typeof b==='string'?a.trim().toLowerCase()===b.trim().toLowerCase():a===b;
function set(o,p,v){const z=p.split('.');let c=o;for(const k of z.slice(0,-1)){if(!c[k]||typeof c[k]!=='object')c[k]={};c=c[k];}c[z.at(-1)]=v;}
function phone(raw){if(raw==null||!String(raw).trim())return{raw:null,normalized:null,status:'missing'};const r=String(raw).trim();let c=r.replace(/(?:ext\.?|extension|x)\s*\d+/ig,'').replace(/[^\d+]/g,'');if(c.startsWith('00'))c='+'+c.slice(2);const digits=c.replace(/\D/g,'');if((c.match(/\+/g)||[]).length>1||(c.includes('+')&&!c.startsWith('+')))return{raw:r,normalized:c,status:'invalid_format'};if(digits.length<8||digits.length>15)return{raw:r,normalized:c||null,status:'invalid_length'};return{raw:r,normalized:c.startsWith('+')?'+'+digits:digits,status:'plausible'};}
const aliases={MINI:['mini','city car','kleinwagen','citadine','utilitaria','μικρό'],ECONOMY:['economy','small','small car','économique','economica','económico','οικονομικό'],COMPACT:['compact','compact car','kompakt','compacte','compatto','συμπαγές'],SUV:['suv','crossover','4x4'],SEVEN_SEATER:['7 seater','7-seater','seven seater','7 posti','7 places','7 sitzer','7θέσιο','7 θεσιο'],VAN:['van','minivan','people carrier','monovolume'],CONVERTIBLE:['convertible','cabrio','cabriolet','decapotable'],PREMIUM:['premium','luxury','executive','luxe','lusso']};
const pv=phone(incoming.phone);
incoming.phone_raw=pv.raw; incoming.phone_normalized=pv.normalized; incoming.phone_status=pv.status;
incoming.vehicle=incoming.vehicle||{};
const rawCat=String(incoming.vehicle.category||'').trim().toLowerCase();
incoming.vehicle.category_normalized=Object.entries(aliases).find(([_,v])=>v.map(x=>x.toLowerCase()).includes(rawCat))?.[0]||null;
incoming.ambiguities=Array.isArray(incoming.ambiguities)?incoming.ambiguities:[];
if(pv.status.startsWith('invalid'))incoming.ambiguities.push({code:'invalid_phone_format',severity:'medium',detail:`Phone failed plausibility: ${pv.status}`});
for(const side of ['pickup','return']){const b=incoming[side]||{};const m=String(b.date_text||'').match(/(?:^|\D)(\d{1,2})[\/.](\d{1,2})(?:\D|$)/);if(!b.date_iso&&m){const a=Number(m[1]),z=Number(m[2]);if(a>=1&&a<=12&&z>=1&&z<=12&&a!==z)incoming.ambiguities.push({code:`ambiguous_${side}_numeric_date`,severity:'medium',detail:`${side} date is numerically ambiguous`});}}
function ambiguityResolved(code,inc){const codes=new Set((inc.ambiguities||[]).filter(a=>a&&typeof a==='object').map(a=>String(a.code||'')));if(codes.has(code))return false;if(code==='invalid_phone_format')return present(inc.phone)&&!String(inc.phone_status||'').startsWith('invalid');if(code==='ambiguous_pickup_numeric_date')return present(get(inc,'pickup.date_text'))||present(get(inc,'pickup.date_iso'));if(code==='ambiguous_return_numeric_date')return present(get(inc,'return.date_text'))||present(get(inc,'return.date_iso'));if(code==='ambiguous_numeric_date')return present(get(inc,'pickup.date_text'))&&present(get(inc,'return.date_text'));return false;}
function dedupeAmbiguities(items){const out=[],seen=new Set();for(const a of items){if(!a||typeof a!=='object')continue;const k=String(a.code||'')+'\u0000'+String(a.detail||'');if(seen.has(k))continue;seen.add(k);out.push(a);}return out;}
let merged=Object.keys(existing).length?cloneJson(existing):cloneJson(incoming);const conflicts=[];
if(Object.keys(existing).length){
  const corrections=[...(existing._applied_corrections||[])];
  const isCorrection=String(incoming.message_intent||'').toLowerCase()==='correction';
  const paths=['customer_name','phone','email','language','pickup.date_text','pickup.date_iso','pickup.time_text','pickup.location','return.date_text','return.date_iso','return.time_text','return.location','vehicle.category','vehicle.category_normalized','vehicle.transmission','vehicle.model_text','competitor.price_text'];
  for(const p of paths){const a=get(merged,p),b=get(incoming,p);if(neutral(p,b)||!present(b))continue;if(ALWAYS_MUTABLE.has(p)){set(merged,p,b);continue;}if(neutral(p,a)||!present(a)){set(merged,p,b);continue;}if(eq(a,b))continue;if(isCorrection&&CORRECTABLE.has(p)){set(merged,p,b);corrections.push(p);}else conflicts.push(p);}
  merged._applied_corrections=[...new Set(corrections)];
  merged.message_intent=incoming.message_intent||existing.message_intent||'follow_up';
  merged.multiple_requests=Boolean(existing.multiple_requests)||Boolean(incoming.multiple_requests);
  merged.competitor=merged.competitor||{};
  merged.competitor.price_mentioned=Boolean(get(existing,'competitor.price_mentioned'))||Boolean(get(incoming,'competitor.price_mentioned'));
  const oc=Number(existing.confidence||0),nc=Number(incoming.confidence||0); merged.confidence=oc&&nc?Math.min(oc,nc):(nc||oc);
  if(present(incoming.phone)){merged.phone_raw=incoming.phone_raw;merged.phone_normalized=incoming.phone_normalized;merged.phone_status=incoming.phone_status;}else{merged.phone_raw=existing.phone_raw;merged.phone_normalized=existing.phone_normalized;merged.phone_status=existing.phone_status;}
  const carried=(existing.ambiguities||[]).filter(a=>a&&typeof a==='object'&&!ambiguityResolved(String(a.code||''),incoming)).map(cloneJson);
  const newest=(incoming.ambiguities||[]).filter(a=>a&&typeof a==='object').map(cloneJson);
  merged.ambiguities=[...carried,...newest];
  for(const p of conflicts)merged.ambiguities.push({code:`conflicting_${p.replaceAll('.','_')}`,severity:'high',detail:`Existing and follow-up values differ for ${p}`});
  merged.ambiguities=dedupeAmbiguities(merged.ambiguities);
}
function missing(){const m=REQUIRED.filter(p=>!present(get(merged,p)));if(present(merged.phone)&&String(merged.phone_status||'').startsWith('invalid')&&!m.includes('phone'))m.push('phone');for(const a of merged.ambiguities||[]){if(a?.code==='ambiguous_pickup_numeric_date'&&!m.includes('pickup.date_text'))m.push('pickup.date_text');if(a?.code==='ambiguous_return_numeric_date'&&!m.includes('return.date_text'))m.push('return.date_text');if(a?.code==='ambiguous_numeric_date'){if(!m.includes('pickup.date_text'))m.push('pickup.date_text');if(!m.includes('return.date_text'))m.push('return.date_text');}}return m;}
const review=[];
const pIso=get(merged,'pickup.date_iso'),rIso=get(merged,'return.date_iso');
if(/^\d{4}-\d{2}-\d{2}$/.test(pIso||'')&&/^\d{4}-\d{2}-\d{2}$/.test(rIso||'')&&rIso<pIso)review.push('return_before_pickup');
if(merged.multiple_requests)review.push('multiple_requests_in_one_message');
for(const a of merged.ambiguities||[]){if(a&&(a.severity==='high'||HIGH.has(String(a.code||'')))&&a.code&&!review.includes(a.code))review.push(a.code);}
if(Number(merged.confidence||0)<minConf)review.push('low_extraction_confidence');
let status,miss=missing(),reason='',next,autoAllowed=false;
if(review.length){status='HUMAN_REVIEW';reason=[...new Set(review)].join(',');next='human_review_before_commitment';}
else if(miss.length){status='NEEDS_INFO';next='ask_only_missing_required_fields';autoAllowed=true;}
else{status='READY';next='continue_to_availability_or_quote_step';autoAllowed=true;}
const competitor=Boolean(get(merged,'competitor.price_mentioned'));
const strategy=status==='HUMAN_REVIEW'?(inbound.runtime?.holding_reply_enabled?'SAFE_HOLDING_REPLY':'HOLD_FOR_HUMAN'):status==='NEEDS_INFO'?'ACKNOWLEDGE_CONFIRM_ASK_ONLY_MISSING':'ACKNOWLEDGE_CONFIRM_VALUE_AND_NEXT_STEP';
const requestId=String(existingRow.request_id||('REQ-'+inbound.thread_id.replace(/[^A-Za-z0-9]/g,'').slice(-10).toUpperCase().padStart(10,'0')));
const revision=Number(existingRow.revision||0)+1; const now=new Date().toISOString();
const plan={language:merged.language||'en',strategy,missing_fields:miss,confirmed:{customer_name:merged.customer_name||null,pickup_date:get(merged,'pickup.date_text'),return_date:get(merged,'return.date_text'),pickup_time:get(merged,'pickup.time_text'),pickup_location:get(merged,'pickup.location'),return_location:get(merged,'return.location'),vehicle_category:get(merged,'vehicle.category'),transmission:get(merged,'vehicle.transmission')},include_total_cost_comparison:competitor&&['READY','NEEDS_INFO'].includes(status),forbidden_claims:['availability_confirmed','booking_confirmed','exact_quote_without_source','vehicle_assignment'],must_not_attack_competitor:true};
return [{json:{...inbound,request_id:requestId,revision,payload:merged,payload_json:JSON.stringify(merged),status,missing_fields:miss,human_review_reason:reason,next_action:next,auto_send_allowed:autoAllowed,reply_plan:plan,reply_language:plan.language,reply_strategy:strategy,processed_at:now,customer_name:merged.customer_name||'',customer_email:merged.email||inbound.from,phone_raw:merged.phone_raw||merged.phone||'',phone_normalized:merged.phone_normalized||'',phone_status:merged.phone_status||'',pickup_date_text:get(merged,'pickup.date_text')||'',pickup_date_iso:get(merged,'pickup.date_iso')||'',pickup_time:get(merged,'pickup.time_text')||'',pickup_location:get(merged,'pickup.location')||'',return_date_text:get(merged,'return.date_text')||'',return_date_iso:get(merged,'return.date_iso')||'',return_time:get(merged,'return.time_text')||'',return_location:get(merged,'return.location')||'',vehicle_category_raw:get(merged,'vehicle.category')||'',vehicle_category_normalized:get(merged,'vehicle.category_normalized')||'',transmission:get(merged,'vehicle.transmission')||'',model_text:get(merged,'vehicle.model_text')||'',competitor_price_mentioned:String(competitor),competitor_price_text:get(merged,'competitor.price_text')||'',extraction_confidence:String(merged.confidence??''),first_received_at:existingRow.first_received_at||inbound.received_at,last_customer_message_at:inbound.received_at,updated_at:now}}];
