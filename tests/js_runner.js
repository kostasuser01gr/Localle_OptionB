'use strict';
const fs=require('fs'); const {decideStatus,buildReplyPlan}=require('../src/engine.js');
const rows=JSON.parse(fs.readFileSync(0,'utf8')); const out=rows.map(r=>{const decision=decideStatus(r.extraction,{minimumConfidence:r.minimum_confidence,duplicateMessage:r.duplicate_message,inboundDisposition:r.inbound_disposition||'PROCESS'});return{decision,reply:buildReplyPlan(r.extraction,decision,{holdingReplyEnabled:r.holding_reply_enabled!==false})};});process.stdout.write(JSON.stringify(out));
