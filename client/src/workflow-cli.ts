import { createInterface } from 'node:readline/promises';
import { stdin, stdout } from 'node:process';
import { randomUUID } from 'node:crypto';
import { httpBridge, type Proposal, type RequestFn, type ServiceOperations } from './service-operations-v1.js';
import { project01TicketHandoff,project08RecordedWork } from './consumer-examples.js';

export async function consumerSmoke(request:RequestFn,provided?:ServiceOperations) {
  const ops=provided??httpBridge(request);
  const a=await project01TicketHandoff(ops,'A-100');
  const b=await project08RecordedWork(ops,{ticketId:'A-100',minutes:30,startedAt:'2026-10-08T09:00:00+07:00',evidence:'Synthetic technician timer: 30 minutes',description:'Demo troubleshooting session'});
  if(a.payload.internalFlag!==true || a.payload.externalFlag!==false || b.payload.actualHours!==0.5 || a.id===b.id) throw new Error('Consumer contract acceptance failed');
  const preview=await request<Proposal>(`/workflow/proposals/${a.id}`);
  if(preview.payload_hash!==a.payload_hash) throw new Error('Proposal preview mismatch');
  console.log(`Project 01 + 08 consumer contract 1.0.0 ${provided?'MCP':'HTTP bridge'} PASS (proposals only)`);
}

export async function workflowCLI(request:RequestFn,args:string[],provided?:ServiceOperations) {
  const [command,id,key]=args;
  if(!id) throw new Error('Usage: --workflow context|note|time|preview|approve|execute|verify ID [idempotency-key]');
  const ops=provided??httpBridge(request);
  const rl=createInterface({input:stdin,output:stdout});
  const answers=rl[Symbol.asyncIterator]();
  async function ask(prompt:string):Promise<string> {
    stdout.write(prompt);
    const answer=await answers.next();
    if(answer.done) throw new Error('Input closed before a response was provided');
    return answer.value;
  }
  try {
    let result:unknown;
    switch(command) {
      case 'context':result=await ops.call('cw.ticket_context',{ticket_id:id});break;
      case 'note':result=await ops.call('cw.note_prepare',{ticket_id:id,content:await ask('Internal note > ')});break;
      case 'time':result=await ops.call('cw.time_entry_prepare',{ticket_id:id,content:await ask('Work description > '),
        duration_minutes:Number(await ask('Documented minutes > ')),duration_evidence:await ask('Timer/work-log evidence > '),
        time_start:await ask('Start ISO timestamp including timezone > ')});break;
      case 'preview':result=await request(`/workflow/proposals/${encodeURIComponent(id)}`);break;
      case 'approve': {
        const p=await request<Proposal>(`/workflow/proposals/${encodeURIComponent(id)}`);
        console.log(JSON.stringify(p,null,2));
        if(await ask('Review payload and duration evidence. Type APPROVE > ')!=='APPROVE') {console.log('No approval submitted.');return;}
        result=await request(`/workflow/proposals/${encodeURIComponent(id)}/approve`,'POST',{payload_hash:p.payload_hash,confirmed:true});break;
      }
      case 'execute': {
        const requestKey=key??randomUUID();console.log(`Keep this idempotency key for retries: ${requestKey}`);
        result=await ops.call('cw.execute_approved',{proposal_id:id,idempotency_key:requestKey});break;
      }
      case 'verify':result=await ops.call('cw.operation_verify',{operation_id:id});break;
      default:throw new Error('Unknown workflow command');
    }
    console.log(JSON.stringify(result,null,2));
  } finally {rl.close();}
}
