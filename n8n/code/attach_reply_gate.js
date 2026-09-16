const core=$('Merge + Validate + Decide').item.json;
const rendered=$('Render Customer Reply').item.json;
const raw=String(rendered.body ?? rendered.email_body ?? rendered.text ?? rendered.output ?? rendered.response ?? '').trim().replace(/\[(?:Your Company Name|Your Name)\]/gi,'Localle');
const reply=raw.replace(/^```(?:text)?\s*/i,'').replace(/```$/,'').trim();

// Ollama JSON mode is reliable, but n8n's LangChain structured-output parser
// is not for llama3.1:8b. Parse the raw response here and validate the complete
// contract. Any transport, parse, schema, or type error is fail-closed.
const requiredBooleans=['safe','language_match','claims_availability','claims_booking_confirmed','quotes_unverified_price','assigns_vehicle','attacks_competitor','exposes_internal','asks_only_allowed_fields','facts_match_plan'];
const requiredKeys=[...requiredBooleans,'reason'];
function parseVerifier(value){
  if(value && typeof value==='object' && !Array.isArray(value)) return {value,error:''};
  const text=String(value ?? '').trim().replace(/^```(?:json)?\s*/i,'').replace(/```$/,'').trim();
  if(!text || text.length>12000) return {value:null,error:'empty_or_oversized_verifier_output'};
  const start=text.indexOf('{'), end=text.lastIndexOf('}');
  if(start<0 || end<start) return {value:null,error:'verifier_json_not_found'};
  try{return {value:JSON.parse(text.slice(start,end+1)),error:''};}
  catch(_){return {value:null,error:'verifier_json_parse_failed'};}
}
const verifierTransportError=String($json.error?.message ?? $json.error ?? '').trim();
const parsed=parseVerifier($json.body ?? $json.text ?? $json.output ?? $json.response ?? ($json.error ? '' : $json));
const v=parsed.value;
const verifierValid=!verifierTransportError && !!v && Object.keys(v).length===requiredKeys.length && requiredKeys.every(k=>Object.prototype.hasOwnProperty.call(v,k)) && requiredBooleans.every(k=>typeof v[k]==='boolean') && typeof v.reason==='string' && v.reason.trim().length>0 && v.reason.length<=500;
const semanticSafe=verifierValid && v.safe===true && v.language_match===true && v.claims_availability===false && v.claims_booking_confirmed===false && v.quotes_unverified_price===false && v.assigns_vehicle===false && v.attacks_competitor===false && v.exposes_internal===false && v.asks_only_allowed_fields===true && v.facts_match_plan===true;
const reasons=[];
if(!reply)reasons.push('empty_reply');
if(reply.length>2500)reasons.push('reply_too_long');
if(/\b(?:HUMAN_REVIEW|NEEDS_INFO|NO_CHANGE|READY|extraction confidence|system prompt|internal status|automation workflow)\b/i.test(reply))reasons.push('internal_state_exposed');
if(/(?:[€$£]\s*\d)|(?:\b\d+(?:[.,]\d{1,2})?\s*(?:€|eur|euros?|usd|gbp|pounds?|dollars?)\b)/i.test(reply))reasons.push('unverified_numeric_price');
const confirms=[/\b(?:booking|reservation|availability)\b.{0,30}\b(?:confirmed|guaranteed|available)\b/i,/\b(?:buchung|reservierung|verfügbarkeit)\b.{0,30}\b(?:bestätigt|garantiert|verfügbar)\b/i,/\b(?:réservation|disponibilité)\b.{0,30}\b(?:confirmée?|garantie?|disponible)\b/i,/\b(?:prenotazione|disponibilità)\b.{0,30}\b(?:confermata|garantita|disponibile)\b/i,/\b(?:reserva|disponibilidad)\b.{0,30}\b(?:confirmada|garantizada|disponible)\b/i,/(?:κράτησ|διαθεσιμότ).{0,40}(?:επιβεβαι|διαθέσιμ|εγγυη)/i];
if(confirms.some(r=>r.test(reply)))reasons.push('booking_or_availability_claim');
if(/\b(?:your car is|we have assigned|vehicle assigned|car allocated)\b|(?:το όχημά σας είναι|σας έχει ανατεθεί όχημα)/i.test(reply))reasons.push('vehicle_assignment_claim');
if(/\b(?:scam|fraud|dishonest|cheat|fake price|rip[- ]?off)\b|(?:απάτη|απατεών|κοροϊδ)/i.test(reply))reasons.push('competitor_attack');
const verifiedFacts=JSON.stringify(core.reply_plan?.verified_business_facts ?? []).toLowerCase();
const restrictedTopics=[
  ['unsupported_deposit_or_card_policy',/\b(?:deposit|credit[- ]?card|card amount|card hold|payment)\b/i],
  ['unsupported_insurance_policy',/\binsurance\b/i],
  ['unsupported_fuel_policy',/\bfuel(?:\s+policy)?\b/i],
  ['unsupported_cancellation_policy',/\bcancell?ation\b/i],
  ['unsupported_availability_statement',/\bavailability\b/i],
];
for(const [reason,pattern] of restrictedTopics){
  if(pattern.test(reply) && !pattern.test(verifiedFacts)) reasons.push(reason);
}
if(reply.includes('```'))reasons.push('markdown_code_fence');
if(verifierTransportError)reasons.push('semantic_verifier_error');
else if(!verifierValid)reasons.push(parsed.error||'semantic_verifier_invalid_schema');
else if(!semanticSafe)reasons.push('semantic_verifier_rejected');
const safe=reasons.length===0;
const holding=core.reply_strategy==='SAFE_HOLDING_REPLY';
const logicAllows=Boolean(core.auto_send_allowed)||holding;
const send=Boolean(core.runtime?.auto_send_enabled)&&logicAllows&&safe&&core.reply_strategy!=='HOLD_FOR_HUMAN';
const reviewRequired=core.status==='HUMAN_REVIEW'||!safe;
const effectiveReason=[core.human_review_reason||'',...reasons].filter(Boolean).join(',');
const effectiveNext=!safe?'review_reply_before_send':core.next_action;
const subject=/^re:/i.test(String(core.subject||''))?String(core.subject):`Re: ${String(core.subject||'Reservation enquiry')}`;
const refs=[String(core.references||'').trim(),String(core.rfc_message_id||'').trim()].filter(Boolean).join(' ').trim();
const headers=[`To: ${String(core.from||'').replace(/[\r\n]/g,' ')}`,`Subject: ${subject.replace(/[\r\n]/g,' ')}`,'MIME-Version: 1.0','Content-Type: text/plain; charset=UTF-8'];
if(core.rfc_message_id)headers.push(`In-Reply-To: ${String(core.rfc_message_id).replace(/[\r\n]/g,' ')}`);
if(refs)headers.push(`References: ${refs.replace(/[\r\n]/g,' ')}`);
const gmail_raw=Buffer.from(`${headers.join('\r\n')}\r\n\r\n${reply}`,'utf8').toString('base64url');
return [{json:{...core,reply_body:reply,reply_preview:reply.slice(0,400),verifier_error:verifierTransportError||parsed.error||'',verifier_valid:verifierValid,verifier_verdict:verifierValid?v:null,reply_safe:safe,reply_safety_reasons:reasons,review_required:reviewRequired,effective_human_review_reason:effectiveReason,effective_next_action:effectiveNext,gmail_raw,send_now:send,delivery_state:send?'PERSISTED_PENDING_SEND':(!safe?'HELD_REPLY_SAFETY':(core.runtime?.auto_send_enabled?'HELD':'DRAFT_ONLY'))}}];
