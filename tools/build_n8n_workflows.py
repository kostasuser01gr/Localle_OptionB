from __future__ import annotations
import json, uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCHEMA=(ROOT/'schemas'/'extraction.schema.json').read_text(encoding='utf-8')
EXTRACT_PROMPT=(ROOT/'prompts'/'extraction_system.md').read_text(encoding='utf-8')
REPLY_PROMPT=(ROOT/'prompts'/'reply_system.md').read_text(encoding='utf-8')
SHEET_ID='1j1hSY__8sCy7Ic4qHPaya3tzUqwQscEzlnKBv7JfbNc'

# Keep all external writes behind explicit gates. Credentials intentionally omitted.

def nid(): return str(uuid.uuid4())
def node(name, typ, ver, pos, params, **kw):
    d={'id':nid(),'name':name,'type':typ,'typeVersion':ver,'position':list(pos),'parameters':params}
    d.update(kw); return d

def sticky(name, pos, text, w=520, h=300, color=7):
    return node(name,'n8n-nodes-base.stickyNote',1,pos,{'content':text,'width':w,'height':h,'color':color})

def sheet_locator(name):
    return {'__rl':True,'mode':'name','value':name,'cachedResultName':name,'cachedResultUrl':f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit'}
def doc_locator():
    return {'__rl':True,'mode':'id','value':SHEET_ID,'cachedResultName':'Localle Reservation Intake — Requests','cachedResultUrl':f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit'}

def col_schema(names, matchable=()):
    return [{'id':x,'displayName':x,'required':False,'defaultMatch':False,'display':True,'type':'string','canBeUsedToMatch':x in set(matchable),'removed':False} for x in names]

NORMALIZE_JS=r'''// Security boundary + email normalization. Customer email is DATA, never instructions.
const j = $json;
const lowerHeaders = {};
for (const [k,v] of Object.entries(j.headers || {})) lowerHeaders[String(k).toLowerCase()] = String(v ?? '');
const subject = String(j.subject || lowerHeaders.subject || '');
const sender = String(j.from || lowerHeaders.from || '');
const autoSubmitted=(lowerHeaders['auto-submitted']||'').trim().toLowerCase();
const precedence=(lowerHeaders['precedence']||'').trim().toLowerCase();
const autoSubject=/^(automatic reply|auto.?reply|out of office|away from office|réponse automatique|abwesenheitsnotiz|risposta automatica|respuesta automática|αυτόματη απάντηση)/i;
const bounceSender=/(mailer-daemon|postmaster|delivery-status)/i;
let disposition='PROCESS', disposition_reason='customer_message_candidate';
if (autoSubmitted && autoSubmitted !== 'no') {disposition='IGNORE_AUTO'; disposition_reason='auto_submitted_header';}
else if (['bulk','junk','list'].includes(precedence)) {disposition='IGNORE_AUTO'; disposition_reason=`precedence_${precedence}`;}
else if (bounceSender.test(sender)) {disposition='IGNORE_BOUNCE'; disposition_reason='bounce_sender';}
else if (autoSubject.test(subject.trim())) {disposition='IGNORE_AUTO'; disposition_reason='auto_reply_subject';}
let body=String(j.text || j.body_text || j.textPlain || '');
if (!body.trim()) body=String(j.html || j.body_html || '').replace(/<br\s*\/?\s*>/gi,'\n').replace(/<\/p>/gi,'\n').replace(/<[^>]+>/g,' ').replace(/&nbsp;/gi,' ').replace(/&amp;/gi,'&').replace(/&lt;/gi,'<').replace(/&gt;/gi,'>');
const lines=body.replace(/\r\n?/g,'\n').split('\n');
const out=[];
const separators=[/^on .+wrote:$/i,/^-{2,}\s*original message\s*-{2,}$/i,/^from:\s/i,/^de:\s/i,/^von:\s/i,/^da:\s/i,/^από:\s/i];
const sig=[/^--\s*$/, /^sent from my iphone/i,/^sent from my android/i,/^get outlook for/i,/^envoyé de mon iphone/i,/^gesendet von meinem/i,/^inviato da/i];
for (const line of lines){const s=line.trim();if(s.startsWith('>')) continue;if(separators.some(r=>r.test(s))) break;if(sig.some(r=>r.test(s))) break;out.push(line);}
let clean=out.join('\n').replace(/[ \t]+/g,' ').replace(/\n{3,}/g,'\n\n').trim();
if(disposition==='PROCESS'&&!clean){disposition='IGNORE_EMPTY';disposition_reason='empty_after_normalization';}
return [{json:{
  message_id:String(j.id || j.message_id || j.messageId || ''),
  thread_id:String(j.threadId || j.thread_id || ''),
  from:sender,to:String(j.to || lowerHeaders.to || ''),subject,
  received_at:String(j.date || j.received_at || new Date().toISOString()),
  normalized_customer_message:clean, disposition, disposition_reason,
  runtime:{auto_send_enabled:false,minimum_confidence:0.85,holding_reply_enabled:true}
}}];'''

DUP_GATE_JS=r'''const original=$('Normalize Inbound').item.json;
const found=String($json.message_id || '').trim() !== '';
const replySent=String($json.reply_sent || '').toLowerCase()==='true' || Number($json.reply_sent||0)===1;
return [{json:{...original,is_duplicate:found,prior_reply_sent:replySent,prior_delivery_state:String($json.delivery_state||''),recovery_needed:found&&!replySent}}];'''

MERGE_DECISION_JS=r'''// Deterministic business engine. LLM interprets; this node decides.
const inbound=$('Normalize Inbound').item.json;
const extractedRaw=$json.output ?? $json;
const incoming=structuredClone(extractedRaw);
const existingRow=$('Lookup Request by Thread').item.json || {};
let existing={};
try { existing=existingRow.payload_json ? JSON.parse(existingRow.payload_json) : {}; } catch(e){ existing={}; }
const minConf=Number(inbound.runtime?.minimum_confidence ?? 0.85);
const REQUIRED=['customer_name','phone','pickup.date_text','return.date_text','vehicle.category'];
const HIGH=new Set(['return_before_pickup','conflicting_dates','conflicting_customer_identity','conflicting_phone','multiple_requests_in_one_message','conflicting_pickup_date_text','conflicting_return_date_text','conflicting_vehicle_category']);
const get=(o,p)=>p.split('.').reduce((v,k)=>v&&typeof v==='object'?v[k]:null,o);
const present=v=>!(v===null||v===undefined||(typeof v==='string'&&!v.trim()));
const neutral=(p,v)=>p==='vehicle.transmission'&&typeof v==='string'&&['unspecified','unknown','not specified'].includes(v.trim().toLowerCase());
const eq=(a,b)=>typeof a==='string'&&typeof b==='string'?a.trim().toLowerCase()===b.trim().toLowerCase():a===b;
function set(o,p,v){const z=p.split('.');let c=o;for(const k of z.slice(0,-1)){if(!c[k]||typeof c[k]!=='object')c[k]={};c=c[k];}c[z.at(-1)]=v;}
function phone(raw){if(raw==null||!String(raw).trim())return{raw:null,normalized:null,status:'missing'};const r=String(raw).trim();let c=r.replace(/(?:ext\.?|extension|x)\s*\d+/ig,'').replace(/[^\d+]/g,'');if(c.startsWith('00'))c='+'+c.slice(2);const digits=c.replace(/\D/g,'');if((c.match(/\+/g)||[]).length>1||(c.includes('+')&&!c.startsWith('+')))return{raw:r,normalized:c,status:'invalid_format'};if(digits.length<8||digits.length>15)return{raw:r,normalized:c||null,status:'invalid_length'};return{raw:r,normalized:c.startsWith('+')?'+'+digits:digits,status:'plausible'};}
const aliases={MINI:['mini','city car','kleinwagen','citadine','utilitaria','μικρό'],ECONOMY:['economy','small','small car','économique','economica','económico','οικονομικό'],COMPACT:['compact','compact car','kompakt','compacte','compatto','συμπαγές'],SUV:['suv','crossover','4x4'],SEVEN_SEATER:['7 seater','7-seater','seven seater','7 posti','7 places','7 sitzer','7θέσιο','7 θεσιο'],VAN:['van','minivan','people carrier','monovolume'],CONVERTIBLE:['convertible','cabrio','cabriolet','decapotable'],PREMIUM:['premium','luxury','executive','luxe','lusso']};
const pv=phone(incoming.phone);incoming.phone_raw=pv.raw;incoming.phone_normalized=pv.normalized;incoming.phone_status=pv.status;incoming.vehicle=incoming.vehicle||{};const rawCat=String(incoming.vehicle.category||'').trim().toLowerCase();incoming.vehicle.category_normalized=Object.entries(aliases).find(([_,v])=>v.map(x=>x.toLowerCase()).includes(rawCat))?.[0]||null;incoming.ambiguities=Array.isArray(incoming.ambiguities)?incoming.ambiguities:[];if(pv.status.startsWith('invalid'))incoming.ambiguities.push({code:'invalid_phone_format',severity:'medium',detail:`Phone failed plausibility: ${pv.status}`});for(const side of ['pickup','return']){const b=incoming[side]||{};const m=String(b.date_text||'').match(/(?:^|\D)(\d{1,2})[\/.](\d{1,2})(?:\D|$)/);if(!b.date_iso&&m){const a=Number(m[1]),z=Number(m[2]);if(a>=1&&a<=12&&z>=1&&z<=12&&a!==z)incoming.ambiguities.push({code:`ambiguous_${side}_numeric_date`,severity:'medium',detail:`${side} date is numerically ambiguous`});}}
let merged=Object.keys(existing).length?structuredClone(existing):structuredClone(incoming);const conflicts=[];
if(Object.keys(existing).length){const paths=['customer_name','phone','email','language','pickup.date_text','pickup.date_iso','pickup.time_text','pickup.location','return.date_text','return.date_iso','return.time_text','return.location','vehicle.category','vehicle.category_normalized','vehicle.transmission','vehicle.model_text','competitor.price_text'];for(const p of paths){const a=get(merged,p),b=get(incoming,p);if(neutral(p,b)||!present(b))continue;if(neutral(p,a)||!present(a))set(merged,p,b);else if(!eq(a,b))conflicts.push(p);}merged.multiple_requests=Boolean(existing.multiple_requests)||Boolean(incoming.multiple_requests);merged.competitor=merged.competitor||{};merged.competitor.price_mentioned=Boolean(get(existing,'competitor.price_mentioned'))||Boolean(get(incoming,'competitor.price_mentioned'));merged.confidence=Number(incoming.confidence ?? existing.confidence ?? 0);merged.phone_raw=incoming.phone_raw||existing.phone_raw;merged.phone_normalized=incoming.phone_normalized||existing.phone_normalized;merged.phone_status=(incoming.phone_status&&incoming.phone_status!=='missing')?incoming.phone_status:existing.phone_status;merged.ambiguities=[...(existing.ambiguities||[]).filter(a=>a&&String(a.code||'').startsWith('conflicting_')),...(incoming.ambiguities||[])];for(const p of conflicts)merged.ambiguities.push({code:`conflicting_${p.replaceAll('.','_')}`,severity:'high',detail:`Existing and follow-up values differ for ${p}`});}
function missing(){const m=REQUIRED.filter(p=>!present(get(merged,p)));if(present(merged.phone)&&String(merged.phone_status||'').startsWith('invalid')&&!m.includes('phone'))m.push('phone');for(const a of merged.ambiguities||[]){if(a?.code==='ambiguous_pickup_numeric_date'&&!m.includes('pickup.date_text'))m.push('pickup.date_text');if(a?.code==='ambiguous_return_numeric_date'&&!m.includes('return.date_text'))m.push('return.date_text');if(a?.code==='ambiguous_numeric_date'){if(!m.includes('pickup.date_text'))m.push('pickup.date_text');if(!m.includes('return.date_text'))m.push('return.date_text');}}return m;}
const review=[];const pIso=get(merged,'pickup.date_iso'),rIso=get(merged,'return.date_iso');if(/^\d{4}-\d{2}-\d{2}$/.test(pIso||'')&&/^\d{4}-\d{2}-\d{2}$/.test(rIso||'')&&rIso<pIso)review.push('return_before_pickup');if(merged.multiple_requests)review.push('multiple_requests_in_one_message');for(const a of merged.ambiguities||[]){if(a&&(a.severity==='high'||HIGH.has(String(a.code||'')))&&a.code&&!review.includes(a.code))review.push(a.code);}if(Number(merged.confidence||0)<minConf)review.push('low_extraction_confidence');
let status,miss=missing(),reason='',next,autoAllowed=false;if(review.length){status='HUMAN_REVIEW';reason=[...new Set(review)].join(',');next='human_review_before_commitment';}else if(miss.length){status='NEEDS_INFO';next='ask_only_missing_required_fields';autoAllowed=true;}else{status='READY';next='continue_to_availability_or_quote_step';autoAllowed=true;}
const competitor=Boolean(get(merged,'competitor.price_mentioned'));const strategy=status==='HUMAN_REVIEW'?(inbound.runtime?.holding_reply_enabled?'SAFE_HOLDING_REPLY':'HOLD_FOR_HUMAN'):status==='NEEDS_INFO'?'ACKNOWLEDGE_CONFIRM_ASK_ONLY_MISSING':'ACKNOWLEDGE_CONFIRM_VALUE_AND_NEXT_STEP';
const requestId=String(existingRow.request_id||('REQ-'+inbound.thread_id.replace(/[^A-Za-z0-9]/g,'').slice(-10).toUpperCase().padStart(10,'0')));const revision=Number(existingRow.revision||0)+1;const now=new Date().toISOString();
const plan={language:merged.language||'en',strategy,missing_fields:miss,confirmed:{customer_name:merged.customer_name||null,pickup_date:get(merged,'pickup.date_text'),return_date:get(merged,'return.date_text'),pickup_time:get(merged,'pickup.time_text'),pickup_location:get(merged,'pickup.location'),return_location:get(merged,'return.location'),vehicle_category:get(merged,'vehicle.category'),transmission:get(merged,'vehicle.transmission')},include_total_cost_comparison:competitor&&['READY','NEEDS_INFO'].includes(status),forbidden_claims:['availability_confirmed','booking_confirmed','exact_quote_without_source','vehicle_assignment'],must_not_attack_competitor:true};
return [{json:{...inbound,request_id:requestId,revision,payload:merged,payload_json:JSON.stringify(merged),status,missing_fields:miss,human_review_reason:reason,next_action:next,auto_send_allowed:autoAllowed,reply_plan:plan,reply_language:plan.language,reply_strategy:strategy,processed_at:now,customer_name:merged.customer_name||'',customer_email:merged.email||inbound.from,phone_raw:merged.phone_raw||merged.phone||'',phone_normalized:merged.phone_normalized||'',phone_status:merged.phone_status||'',pickup_date_text:get(merged,'pickup.date_text')||'',pickup_date_iso:get(merged,'pickup.date_iso')||'',pickup_time:get(merged,'pickup.time_text')||'',pickup_location:get(merged,'pickup.location')||'',return_date_text:get(merged,'return.date_text')||'',return_date_iso:get(merged,'return.date_iso')||'',return_time:get(merged,'return.time_text')||'',return_location:get(merged,'return.location')||'',vehicle_category_raw:get(merged,'vehicle.category')||'',vehicle_category_normalized:get(merged,'vehicle.category_normalized')||'',transmission:get(merged,'vehicle.transmission')||'',model_text:get(merged,'vehicle.model_text')||'',competitor_price_mentioned:String(competitor),competitor_price_text:get(merged,'competitor.price_text')||'',extraction_confidence:String(merged.confidence??''),first_received_at:existingRow.first_received_at||inbound.received_at,last_customer_message_at:inbound.received_at,updated_at:now}}];'''

ATTACH_REPLY_JS=r'''const core=$('Merge + Validate + Decide').item.json;const raw=String($json.text ?? $json.output ?? $json.response ?? '').trim();const reply=raw.replace(/^```(?:text)?\s*/i,'').replace(/```$/,'').trim();const safe=reply.length>0 && !/booking (is )?confirmed|availability (is )?confirmed/i.test(reply);const send=Boolean(core.runtime?.auto_send_enabled)&&Boolean(core.auto_send_allowed)&&safe&&core.reply_strategy!=='HOLD_FOR_HUMAN';return [{json:{...core,reply_body:reply,reply_preview:reply.slice(0,400),reply_safe:safe,send_now:send,delivery_state:send?'PERSISTED_PENDING_SEND':(core.runtime?.auto_send_enabled?'HELD':'DRAFT_ONLY')}}];'''

RECOVERY_JS=r'''const n=$('Normalize Inbound').item.json;const prev=$json;return [{json:{...n,status:'HUMAN_REVIEW',request_id:String(prev.request_id||''),human_review_reason:'previous_processing_persisted_without_confirmed_reply',next_action:'inspect_gmail_sent_and_reply_manually_if_needed',reply_strategy:'HOLD_FOR_HUMAN',reply_body:'',send_now:false,processed_at:new Date().toISOString(),delivery_state:'RECOVERY_NEEDED'}}];'''

# Request sheet columns
REQ_COLS=['request_id','thread_id','last_message_id','revision','first_received_at','last_customer_message_at','updated_at','customer_name','customer_email','phone_raw','phone_normalized','phone_status','language','pickup_date_text','pickup_date_iso','pickup_time','pickup_location','return_date_text','return_date_iso','return_time','return_location','vehicle_category_raw','vehicle_category_normalized','transmission','model_text','competitor_price_mentioned','competitor_price_text','missing_fields','status','human_review_reason','extraction_confidence','reply_language','reply_strategy','next_action','reply_preview','payload_json']
PROC_COLS=['message_id','thread_id','request_id','processed_at','result_status','reply_sent','delivery_state','execution_id','reply_preview']
AUD_COLS=['timestamp','message_id','thread_id','request_id','event','status','detail','execution_id']
REVIEW_COLS=['request_id','thread_id','priority','customer_name','customer_email','reason','next_action','latest_message','suggested_reply','received_at','waiting_since','status']

nodes=[]
nodes += [sticky('00 — Safety & scope',(-1100,-720),'# Localle Reservation Intake v1.0\n**Default safe mode: AUTO SEND = OFF.**\n\nFlow: unread Gmail → normalize → durable duplicate check → structured AI extraction → deterministic validation/state machine → Google Sheet UPSERT → constrained multilingual reply → optional same-thread Gmail reply → audit → mark read.\n\nDo not activate before binding credentials and completing the setup checklist.',620,440,5)]
nodes += [node('Gmail Trigger','n8n-nodes-base.gmailTrigger',1.4,(-1080,-120),{'pollTimes':{'item':[{'mode':'everyX','value':1,'unit':'minutes'}]},'event':'messageReceived','simple':False,'maxResults':20,'filters':{'includeSpamTrash':False,'includeDrafts':False,'readStatus':'unread','q':'in:inbox'},'options':{}})]
nodes += [node('Normalize Inbound','n8n-nodes-base.code',2,(-840,-120),{'jsCode':NORMALIZE_JS})]
nodes += [node('Should Process?','n8n-nodes-base.if',2.3,(-600,-120),{'conditions':{'options':{'caseSensitive':True,'leftValue':'','typeValidation':'strict','version':2},'conditions':[{'id':nid(),'leftValue':'={{ $json.disposition }}','rightValue':'PROCESS','operator':{'type':'string','operation':'equals'}}],'combinator':'and'},'options':{}})]
# ignored path persistence
nodes += [node('Log Ignored Event','n8n-nodes-base.googleSheets',4.7,(-360,160),{'operation':'append','documentId':doc_locator(),'sheetName':sheet_locator('Processed_Messages'),'columns':{'mappingMode':'defineBelow','value':{'message_id':'={{ $json.message_id }}','thread_id':'={{ $json.thread_id }}','request_id':'','processed_at':'={{ $now.toISO() }}','result_status':'NO_CHANGE','reply_sent':'false','delivery_state':'IGNORED','execution_id':'={{ $execution.id }}','reply_preview':'={{ $json.disposition_reason }}'},'matchingColumns':[],'schema':col_schema(PROC_COLS),'attemptToConvertTypes':False,'convertFieldsToString':False},'options':{}})]
nodes += [node('Mark Ignored Read','n8n-nodes-base.gmail',2.2,(-100,160),{'operation':'markAsRead','messageId':'={{ $(\'Normalize Inbound\').item.json.message_id }}'})]
# process path duplicate ledger
nodes += [node('Lookup Processed Message','n8n-nodes-base.googleSheets',4.7,(-360,-220),{'documentId':doc_locator(),'sheetName':sheet_locator('Processed_Messages'),'filtersUI':{'values':[{'lookupColumn':'message_id','lookupValue':'={{ $json.message_id }}'}]},'options':{'returnFirstMatch':True}},alwaysOutputData=True)]
nodes += [node('Duplicate / Recovery Gate','n8n-nodes-base.code',2,(-100,-220),{'jsCode':DUP_GATE_JS})]
nodes += [node('Already Processed?','n8n-nodes-base.if',2.3,(140,-220),{'conditions':{'options':{'caseSensitive':True,'leftValue':'','typeValidation':'strict','version':2},'conditions':[{'id':nid(),'leftValue':'={{ $json.is_duplicate }}','rightValue':True,'operator':{'type':'boolean','operation':'true','singleValue':True}}],'combinator':'and'},'options':{}})]
nodes += [node('Was Reply Confirmed?','n8n-nodes-base.if',2.3,(380,-360),{'conditions':{'options':{'caseSensitive':True,'leftValue':'','typeValidation':'strict','version':2},'conditions':[{'id':nid(),'leftValue':'={{ $json.prior_reply_sent }}','rightValue':True,'operator':{'type':'boolean','operation':'true','singleValue':True}}],'combinator':'and'},'options':{}})]
nodes += [node('Mark Duplicate Read','n8n-nodes-base.gmail',2.2,(640,-460),{'operation':'markAsRead','messageId':'={{ $(\'Normalize Inbound\').item.json.message_id }}'})]
nodes += [node('Build Recovery Review','n8n-nodes-base.code',2,(640,-260),{'jsCode':RECOVERY_JS})]
nodes += [node('Upsert Recovery Review','n8n-nodes-base.googleSheets',4.7,(900,-260),{'operation':'appendOrUpdate','documentId':doc_locator(),'sheetName':sheet_locator('Human_Review'),'columns':{'mappingMode':'defineBelow','value':{'request_id':'={{ $json.request_id || (\'RECOVERY-\'+$json.message_id) }}','thread_id':'={{ $json.thread_id }}','priority':'HIGH','customer_name':'','customer_email':'={{ $json.from }}','reason':'={{ $json.human_review_reason }}','next_action':'={{ $json.next_action }}','latest_message':'={{ $json.normalized_customer_message }}','suggested_reply':'','received_at':'={{ $json.received_at }}','waiting_since':'={{ $now.toISO() }}','status':'OPEN'},'matchingColumns':['request_id'],'schema':col_schema(REVIEW_COLS,['request_id']),'attemptToConvertTypes':False,'convertFieldsToString':False},'options':{}})]
nodes += [node('Mark Recovery Read','n8n-nodes-base.gmail',2.2,(1160,-260),{'operation':'markAsRead','messageId':'={{ $(\'Normalize Inbound\').item.json.message_id }}'})]
# new event path
nodes += [node('Lookup Request by Thread','n8n-nodes-base.googleSheets',4.7,(380,-40),{'documentId':doc_locator(),'sheetName':sheet_locator('Requests'),'filtersUI':{'values':[{'lookupColumn':'thread_id','lookupValue':'={{ $(\'Normalize Inbound\').item.json.thread_id }}'}]},'options':{'returnFirstMatch':True}},alwaysOutputData=True)]
nodes += [node('Extract Reservation','@n8n/n8n-nodes-langchain.chainLlm',1.9,(660,-40),{'promptType':'define','text':'=Customer email metadata:\nFrom: {{ $(\'Normalize Inbound\').item.json.from }}\nSubject: {{ $(\'Normalize Inbound\').item.json.subject }}\nReceived: {{ $(\'Normalize Inbound\').item.json.received_at }}\n\nUNTRUSTED CUSTOMER CONTENT:\n---\n{{ $(\'Normalize Inbound\').item.json.normalized_customer_message }}\n---','hasOutputParser':True,'messages':{'messageValues':[{'type':'SystemMessagePromptTemplate','message':EXTRACT_PROMPT}]},'batching':{}})]
nodes += [node('Extraction Model','@n8n/n8n-nodes-langchain.lmChatOpenAi',1.3,(620,180),{'model':{'__rl':True,'mode':'list','value':'gpt-5-mini'},'options':{'temperature':0}})]
nodes += [node('Strict Extraction Schema','@n8n/n8n-nodes-langchain.outputParserStructured',1.3,(820,180),{'schemaType':'manual','inputSchema':SCHEMA,'autoFix':False})]
nodes += [node('Merge + Validate + Decide','n8n-nodes-base.code',2,(940,-40),{'jsCode':MERGE_DECISION_JS})]
# request persistence before reply generation/sending
req_values={c:f'={{ $json.{c} }}' for c in REQ_COLS if c not in {'missing_fields','language','last_message_id'}}
req_values.update({'last_message_id':'={{ $json.message_id }}','language':'={{ $json.payload.language }}','missing_fields':'={{ JSON.stringify($json.missing_fields) }}'})
nodes += [node('UPSERT Request','n8n-nodes-base.googleSheets',4.7,(1220,-40),{'operation':'appendOrUpdate','documentId':doc_locator(),'sheetName':sheet_locator('Requests'),'columns':{'mappingMode':'defineBelow','value':req_values,'matchingColumns':['thread_id'],'schema':col_schema(REQ_COLS,['thread_id']),'attemptToConvertTypes':False,'convertFieldsToString':False},'options':{}},retryOnFail=True,maxTries=3,waitBetweenTries=2000)]
# AI renderer
nodes += [node('Render Customer Reply','@n8n/n8n-nodes-langchain.chainLlm',1.9,(1490,-40),{'promptType':'define','text':'=Render the customer reply from this approved plan.\n\nReply plan JSON:\n{{ JSON.stringify($(\'Merge + Validate + Decide\').item.json.reply_plan) }}\n\nVerified business facts available for value framing ONLY:\n- Reference price in the exercise: 35 EUR/day for a small car in July. Do NOT quote this as a live price.\n- Full insurance with no excess\n- Second driver included\n- Airport delivery/pickup included\n- Full-to-full fuel policy\n- 24/7 support\n- No credit-card amount hold\n\nOriginal customer language: {{ $(\'Merge + Validate + Decide\').item.json.reply_language }}\nOriginal customer message:\n{{ $(\'Merge + Validate + Decide\').item.json.normalized_customer_message }}','hasOutputParser':False,'messages':{'messageValues':[{'type':'SystemMessagePromptTemplate','message':REPLY_PROMPT}]},'batching':{}})]
nodes += [node('Reply Model','@n8n/n8n-nodes-langchain.lmChatOpenAi',1.3,(1460,180),{'model':{'__rl':True,'mode':'list','value':'gpt-5-mini'},'options':{'temperature':0.2}})]
nodes += [node('Attach Reply + Send Gate','n8n-nodes-base.code',2,(1760,-40),{'jsCode':ATTACH_REPLY_JS})]
# persist ledger BEFORE any external reply attempt
proc_values={'message_id':'={{ $json.message_id }}','thread_id':'={{ $json.thread_id }}','request_id':'={{ $json.request_id }}','processed_at':'={{ $json.processed_at }}','result_status':'={{ $json.status }}','reply_sent':'false','delivery_state':'={{ $json.delivery_state }}','execution_id':'={{ $execution.id }}','reply_preview':'={{ $json.reply_preview }}'}
nodes += [node('Persist Event Ledger','n8n-nodes-base.googleSheets',4.7,(2020,-40),{'operation':'appendOrUpdate','documentId':doc_locator(),'sheetName':sheet_locator('Processed_Messages'),'columns':{'mappingMode':'defineBelow','value':proc_values,'matchingColumns':['message_id'],'schema':col_schema(PROC_COLS,['message_id']),'attemptToConvertTypes':False,'convertFieldsToString':False},'options':{}},retryOnFail=True,maxTries=3,waitBetweenTries=2000)]
# human review upsert branch for review cases (side branch before send decision)
nodes += [node('Needs Human Review?','n8n-nodes-base.if',2.3,(2280,120),{'conditions':{'options':{'caseSensitive':True,'leftValue':'','typeValidation':'strict','version':2},'conditions':[{'id':nid(),'leftValue':'={{ $(\'Attach Reply + Send Gate\').item.json.status }}','rightValue':'HUMAN_REVIEW','operator':{'type':'string','operation':'equals'}}],'combinator':'and'},'options':{}})]
nodes += [node('UPSERT Human Review','n8n-nodes-base.googleSheets',4.7,(2540,180),{'operation':'appendOrUpdate','documentId':doc_locator(),'sheetName':sheet_locator('Human_Review'),'columns':{'mappingMode':'defineBelow','value':{'request_id':'={{ $(\'Attach Reply + Send Gate\').item.json.request_id }}','thread_id':'={{ $(\'Attach Reply + Send Gate\').item.json.thread_id }}','priority':'HIGH','customer_name':'={{ $(\'Attach Reply + Send Gate\').item.json.customer_name }}','customer_email':'={{ $(\'Attach Reply + Send Gate\').item.json.customer_email }}','reason':'={{ $(\'Attach Reply + Send Gate\').item.json.human_review_reason }}','next_action':'={{ $(\'Attach Reply + Send Gate\').item.json.next_action }}','latest_message':'={{ $(\'Attach Reply + Send Gate\').item.json.normalized_customer_message }}','suggested_reply':'={{ $(\'Attach Reply + Send Gate\').item.json.reply_body }}','received_at':'={{ $(\'Attach Reply + Send Gate\').item.json.received_at }}','waiting_since':'={{ $now.toISO() }}','status':'OPEN'},'matchingColumns':['request_id'],'schema':col_schema(REVIEW_COLS,['request_id']),'attemptToConvertTypes':False,'convertFieldsToString':False},'options':{}})]
# send gate main branch
nodes += [node('AUTO SEND enabled + safe?','n8n-nodes-base.if',2.3,(2280,-80),{'conditions':{'options':{'caseSensitive':True,'leftValue':'','typeValidation':'strict','version':2},'conditions':[{'id':nid(),'leftValue':'={{ $(\'Attach Reply + Send Gate\').item.json.send_now }}','rightValue':True,'operator':{'type':'boolean','operation':'true','singleValue':True}}],'combinator':'and'},'options':{}})]
nodes += [node('Reply in Same Gmail Thread','n8n-nodes-base.gmail',2.2,(2540,-180),{'operation':'reply','messageId':'={{ $(\'Attach Reply + Send Gate\').item.json.message_id }}','emailType':'text','message':'={{ $(\'Attach Reply + Send Gate\').item.json.reply_body }}','options':{'appendAttribution':False,'replyToSenderOnly':True}},retryOnFail=False,onError='continueErrorOutput')]
# After successful reply, update ledger reply_sent true
sent_values=dict(proc_values);sent_values.update({'reply_sent':'true','delivery_state':'SENT'})
nodes += [node('Confirm Reply Sent in Ledger','n8n-nodes-base.googleSheets',4.7,(2810,-220),{'operation':'appendOrUpdate','documentId':doc_locator(),'sheetName':sheet_locator('Processed_Messages'),'columns':{'mappingMode':'defineBelow','value':sent_values,'matchingColumns':['message_id'],'schema':col_schema(PROC_COLS,['message_id']),'attemptToConvertTypes':False,'convertFieldsToString':False},'options':{}},retryOnFail=True,maxTries=3,waitBetweenTries=2000)]
# send error -> human review (do not blind retry uncertain send)
nodes += [node('Build Send-Uncertain Review','n8n-nodes-base.code',2,(2810,-80),{'jsCode':"const x=$('Attach Reply + Send Gate').item.json;return [{json:{...x,status:'HUMAN_REVIEW',human_review_reason:'gmail_reply_failed_or_delivery_uncertain',next_action:'inspect_sent_mail_before_retry',delivery_state:'SEND_UNCERTAIN'}}];"})]
nodes += [node('UPSERT Send-Uncertain Review','n8n-nodes-base.googleSheets',4.7,(3070,-80),{'operation':'appendOrUpdate','documentId':doc_locator(),'sheetName':sheet_locator('Human_Review'),'columns':{'mappingMode':'defineBelow','value':{'request_id':'={{ $json.request_id }}','thread_id':'={{ $json.thread_id }}','priority':'CRITICAL','customer_name':'={{ $json.customer_name }}','customer_email':'={{ $json.customer_email }}','reason':'={{ $json.human_review_reason }}','next_action':'={{ $json.next_action }}','latest_message':'={{ $json.normalized_customer_message }}','suggested_reply':'={{ $json.reply_body }}','received_at':'={{ $json.received_at }}','waiting_since':'={{ $now.toISO() }}','status':'OPEN'},'matchingColumns':['request_id'],'schema':col_schema(REVIEW_COLS,['request_id']),'attemptToConvertTypes':False,'convertFieldsToString':False},'options':{}})]
# no-send draft path: mark read after persistence; for actual Localle demo enable flag, this path won't be used.
nodes += [node('Mark Draft/Test Read','n8n-nodes-base.gmail',2.2,(2540,0),{'operation':'markAsRead','messageId':'={{ $(\'Attach Reply + Send Gate\').item.json.message_id }}'})]
nodes += [node('Mark Replied Read','n8n-nodes-base.gmail',2.2,(3070,-220),{'operation':'markAsRead','messageId':'={{ $(\'Attach Reply + Send Gate\').item.json.message_id }}'})]
# audit append nodes for terminal states
nodes += [node('Audit Success','n8n-nodes-base.googleSheets',4.7,(3320,-220),{'operation':'append','documentId':doc_locator(),'sheetName':sheet_locator('Audit'),'columns':{'mappingMode':'defineBelow','value':{'timestamp':'={{ $now.toISO() }}','message_id':'={{ $(\'Attach Reply + Send Gate\').item.json.message_id }}','thread_id':'={{ $(\'Attach Reply + Send Gate\').item.json.thread_id }}','request_id':'={{ $(\'Attach Reply + Send Gate\').item.json.request_id }}','event':'REPLY_SENT','status':'={{ $(\'Attach Reply + Send Gate\').item.json.status }}','detail':'same-thread reply sent and message marked read','execution_id':'={{ $execution.id }}'},'matchingColumns':[],'schema':col_schema(AUD_COLS),'attemptToConvertTypes':False,'convertFieldsToString':False},'options':{}})]
nodes += [node('Audit Draft','n8n-nodes-base.googleSheets',4.7,(2810,0),{'operation':'append','documentId':doc_locator(),'sheetName':sheet_locator('Audit'),'columns':{'mappingMode':'defineBelow','value':{'timestamp':'={{ $now.toISO() }}','message_id':'={{ $(\'Attach Reply + Send Gate\').item.json.message_id }}','thread_id':'={{ $(\'Attach Reply + Send Gate\').item.json.thread_id }}','request_id':'={{ $(\'Attach Reply + Send Gate\').item.json.request_id }}','event':'DRAFT_ONLY','status':'={{ $(\'Attach Reply + Send Gate\').item.json.status }}','detail':'auto-send disabled; reply generated but not sent','execution_id':'={{ $execution.id }}'},'matchingColumns':[],'schema':col_schema(AUD_COLS),'attemptToConvertTypes':False,'convertFieldsToString':False},'options':{}})]
nodes += [node('Audit Send Uncertain','n8n-nodes-base.googleSheets',4.7,(3320,-80),{'operation':'append','documentId':doc_locator(),'sheetName':sheet_locator('Audit'),'columns':{'mappingMode':'defineBelow','value':{'timestamp':'={{ $now.toISO() }}','message_id':'={{ $(\'Attach Reply + Send Gate\').item.json.message_id }}','thread_id':'={{ $(\'Attach Reply + Send Gate\').item.json.thread_id }}','request_id':'={{ $(\'Attach Reply + Send Gate\').item.json.request_id }}','event':'SEND_UNCERTAIN','status':'HUMAN_REVIEW','detail':'Gmail reply failed/uncertain; blind resend suppressed','execution_id':'={{ $execution.id }}'},'matchingColumns':[],'schema':col_schema(AUD_COLS),'attemptToConvertTypes':False,'convertFieldsToString':False},'options':{}})]
nodes += [sticky('99 — Activation gate',(2140,-620),'# Before enabling AUTO SEND\n1. Bind Gmail, Google Sheets and OpenAI credentials.\n2. Run the included Manual Replay Harness and regression suite.\n3. Send test emails from a separate mailbox.\n4. Verify same-thread replies + same-row updates.\n5. Confirm business facts with the owner.\n6. Change `auto_send_enabled` to `true` **only in Normalize Inbound**.\n\nIf Gmail reply returns an error, this workflow does **not** blindly resend; it routes to Human_Review because delivery may be uncertain.',640,480,4)]

connections={}
def conn(src,dst,src_index=0,typ='main'):
    connections.setdefault(src,{}).setdefault(typ,[])
    while len(connections[src][typ])<=src_index: connections[src][typ].append([])
    connections[src][typ][src_index].append({'node':dst,'type':typ if typ!='main' else 'main','index':0})
# main
conn('Gmail Trigger','Normalize Inbound')
conn('Normalize Inbound','Should Process?')
# IF output 0=true,1=false
conn('Should Process?','Lookup Processed Message',0)
conn('Should Process?','Log Ignored Event',1)
conn('Log Ignored Event','Mark Ignored Read')
conn('Lookup Processed Message','Duplicate / Recovery Gate')
conn('Duplicate / Recovery Gate','Already Processed?')
conn('Already Processed?','Was Reply Confirmed?',0)
conn('Already Processed?','Lookup Request by Thread',1)
conn('Was Reply Confirmed?','Mark Duplicate Read',0)
conn('Was Reply Confirmed?','Build Recovery Review',1)
conn('Build Recovery Review','Upsert Recovery Review')
conn('Upsert Recovery Review','Mark Recovery Read')
conn('Lookup Request by Thread','Extract Reservation')
# AI aux
connections['Extraction Model']={'ai_languageModel':[[{'node':'Extract Reservation','type':'ai_languageModel','index':0}]]}
connections['Strict Extraction Schema']={'ai_outputParser':[[{'node':'Extract Reservation','type':'ai_outputParser','index':0}]]}
conn('Extract Reservation','Merge + Validate + Decide')
conn('Merge + Validate + Decide','UPSERT Request')
conn('UPSERT Request','Render Customer Reply')
connections['Reply Model']={'ai_languageModel':[[{'node':'Render Customer Reply','type':'ai_languageModel','index':0}]]}
conn('Render Customer Reply','Attach Reply + Send Gate')
conn('Attach Reply + Send Gate','Persist Event Ledger')
# two side decisions from ledger; n8n main fanout allowed
conn('Persist Event Ledger','AUTO SEND enabled + safe?')
conn('Persist Event Ledger','Needs Human Review?')
conn('Needs Human Review?','UPSERT Human Review',0)
conn('AUTO SEND enabled + safe?','Reply in Same Gmail Thread',0)
conn('AUTO SEND enabled + safe?','Mark Draft/Test Read',1)
# Gmail Reply regular out 0 / error out 1 with continueErrorOutput
conn('Reply in Same Gmail Thread','Confirm Reply Sent in Ledger',0)
conn('Reply in Same Gmail Thread','Build Send-Uncertain Review',1)
conn('Confirm Reply Sent in Ledger','Mark Replied Read')
conn('Mark Replied Read','Audit Success')
conn('Build Send-Uncertain Review','UPSERT Send-Uncertain Review')
conn('UPSERT Send-Uncertain Review','Audit Send Uncertain')
conn('Mark Draft/Test Read','Audit Draft')

workflow={'name':'Localle — AI Reservation Intake v1.0 (SAFE DEFAULT)','nodes':nodes,'connections':connections,'pinData':{},'active':False,'settings':{'executionOrder':'v1','saveManualExecutions':True,'callerPolicy':'workflowsFromSameOwner'},'versionId':str(uuid.uuid4()),'meta':{'templateCredsSetupCompleted':False},'tags':[]}
(ROOT/'n8n'/'localle_reservation_intake_v1.n8n.json').write_text(json.dumps(workflow,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

# Credential-free logic replay workflow: useful for reviewer/demo without touching mailbox.
demo_nodes=[
 sticky('README',(-900,-500),'# Credential-free regression replay\nRuns representative extracted reservation cases through the deterministic state machine. It **never sends email or writes external data**.',520,260,6),
 node('Manual Trigger','n8n-nodes-base.manualTrigger',1,(-820,-80),{}),
 node('Generate Scenarios','n8n-nodes-base.code',2,(-580,-80),{'jsCode':r'''const base={language:'en',customer_name:'John Smith',phone:'+44 7700 123456',email:'john@example.com',pickup:{date_text:'18 July',date_iso:null,time_text:'10:00',location:'Kos Airport'},return:{date_text:'23 July',date_iso:null,time_text:null,location:null},vehicle:{category:'small',transmission:'automatic',model_text:null},competitor:{price_mentioned:false,price_text:null},multiple_requests:false,ambiguities:[],confidence:.98};const cases=[['complete',base],['missing-name-phone',{...structuredClone(base),customer_name:null,phone:null}],['low-confidence',{...structuredClone(base),confidence:.4}],['competitor',{...structuredClone(base),competitor:{price_mentioned:true,price_text:'8 EUR/day'}}],['multiple',{...structuredClone(base),multiple_requests:true}],['bad-phone',{...structuredClone(base),phone:'123'}]];return cases.map(([case_name,extraction],i)=>({json:{case_name,extraction,message_id:'demo-'+i,thread_id:'thread-'+i}}));'''}),
 node('Decision Engine','n8n-nodes-base.code',2,(-300,-80),{'jsCode':r'''const x=structuredClone($json.extraction);const required=['customer_name','phone','pickup.date_text','return.date_text','vehicle.category'];const get=(o,p)=>p.split('.').reduce((v,k)=>v&&typeof v==='object'?v[k]:null,o);const present=v=>!(v==null||(typeof v==='string'&&!v.trim()));const digits=String(x.phone||'').replace(/\D/g,'');x.phone_status=!x.phone?'missing':(digits.length>=8&&digits.length<=15?'plausible':'invalid_length');const missing=required.filter(p=>!present(get(x,p)));if(x.phone_status.startsWith('invalid')&&!missing.includes('phone'))missing.push('phone');const review=[];if(x.multiple_requests)review.push('multiple_requests_in_one_message');if(Number(x.confidence||0)<.85)review.push('low_extraction_confidence');for(const a of x.ambiguities||[])if(a?.severity==='high')review.push(a.code);let status=review.length?'HUMAN_REVIEW':missing.length?'NEEDS_INFO':'READY';return [{json:{...$json,status,missing_fields:missing,human_review_reason:[...new Set(review)].join(','),competitor_price_mentioned:Boolean(x.competitor?.price_mentioned),PASS:['READY','NEEDS_INFO','HUMAN_REVIEW'].includes(status)}}];'''}),
 node('Summarize','n8n-nodes-base.code',2,(-20,-80),{'jsCode':"return $input.all().map(i=>({json:{case:i.json.case_name,status:i.json.status,missing_fields:i.json.missing_fields,human_review_reason:i.json.human_review_reason,pass:i.json.PASS}}));"})
]
demo_con={'Manual Trigger':{'main':[[{'node':'Generate Scenarios','type':'main','index':0}]]},'Generate Scenarios':{'main':[[{'node':'Decision Engine','type':'main','index':0}]]},'Decision Engine':{'main':[[{'node':'Summarize','type':'main','index':0}]]}}
demo={'name':'Localle — Reservation Logic Replay (NO CREDENTIALS)','nodes':demo_nodes,'connections':demo_con,'pinData':{},'active':False,'settings':{'executionOrder':'v1'},'versionId':str(uuid.uuid4()),'meta':{'templateCredsSetupCompleted':True},'tags':[]}
(ROOT/'n8n'/'localle_reservation_logic_demo.n8n.json').write_text(json.dumps(demo,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('built',len(nodes),'production nodes and',len(demo_nodes),'demo nodes')
