import { createInterface } from 'node:readline/promises';
import { stdin,stdout } from 'node:process';
import { randomUUID } from 'node:crypto';
import type { RequestFn } from './service-operations-v1.js';

export async function assistantCLI(request:RequestFn,args:string[]) {
  const [command,id]=args;
  if(!id) throw new Error('Usage: --ai summary|note|time TICKET_ID, or --ai run|prepare|cancel RUN_ID');
  if(['run','prepare','cancel'].includes(command??'')) {
    console.log(JSON.stringify(await request(`/assistant/runs/${encodeURIComponent(id)}${command==='run'?'':'/'+command}`,command==='run'?'GET':'POST'),null,2));return;
  }
  const skills:Record<string,string>={summary:'summarize_service_ticket',note:'prepare_internal_note',time:'prepare_time_entry'};
  const skill=skills[command??''];if(!skill) throw new Error('Unknown AI command');
  const provider=process.env.AI_PROVIDER??'ollama';
  const body:Record<string,unknown>={request_id:randomUUID(),skill,ticket_id:id,provider,local_only:provider==='ollama'};
  const rl=createInterface({input:stdin,output:stdout});const answers=rl[Symbol.asyncIterator]();
  async function ask(prompt:string) {stdout.write(prompt);const answer=await answers.next();if(answer.done) throw new Error('Missing input');return answer.value;}
  try {
    if(command!=='summary')body.technician_notes=await ask('Technician observations > ');
    if(command==='time') {
      body.duration_minutes=Number(await ask('Documented minutes > '));
      body.duration_evidence=await ask('Timer/work-log evidence > ');
      body.time_start=await ask('Start ISO timestamp with timezone > ');
    }
    console.log(`AI request ID (retain for recovery): ${body.request_id}`);
    const result=await request('/assistant/runs','POST',body);
    console.log(JSON.stringify(result,null,2));
    console.log('Only completed drafts can become proposals. Use --ai prepare RUN_ID, then the separate approval workflow.');
  } finally {rl.close();}
}
