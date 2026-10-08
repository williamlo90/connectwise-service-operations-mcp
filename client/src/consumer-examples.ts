import { CONTRACT_VERSION, type ServiceOperations } from './service-operations-v1.js';

// Project 01 assistant: scoped context -> deterministic internal-note proposal.
export async function project01TicketHandoff(ops:ServiceOperations,ticketId:string) {
  if(ops.contractVersion!==CONTRACT_VERSION) throw new Error('Contract version mismatch');
  const context=await ops.call('cw.ticket_context',{ticket_id:ticketId});
  return ops.call('cw.note_prepare',{ticket_id:ticketId,visibility:'internal',
    content:`Handoff: ${context.summary}\nNeeds confirmation: ${context.missing_information.join(' ')}`});
}

// Project 08 workflow: technician evidence -> time-entry proposal; never guess elapsed work.
export async function project08RecordedWork(ops:ServiceOperations,work:{ticketId:string;minutes:number;startedAt:string;evidence:string;description:string}) {
  if(ops.contractVersion!==CONTRACT_VERSION) throw new Error('Contract version mismatch');
  return ops.call('cw.time_entry_prepare',{ticket_id:work.ticketId,content:work.description,
    duration_minutes:work.minutes,duration_evidence:work.evidence,time_start:work.startedAt});
}
// Both return a preview. Neither consumer fabricates approval nor executes automatically.
