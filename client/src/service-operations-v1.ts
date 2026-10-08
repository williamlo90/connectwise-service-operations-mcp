/** Consumer contract 1.0.0. Phase 2 HTTP bridge; MCP transport arrives in Phase 4. */
export const CONTRACT_VERSION = '1.0.0' as const;
export type Ticket = {id:string;summary:string;status:string};
export type Context = {
  ticket:{id:number;summary:string}; summary:string; source_hash:string;
  facts:{field:string;value:unknown;source:string}[]; missing_information:string[];
  notes:Record<string,unknown>[]; contract_version:typeof CONTRACT_VERSION;
};
export type Proposal = {
  id:string;payload:Record<string,unknown>;payload_hash:string;
  evidence:Record<string,unknown>;expires_at:string;
};
export type Receipt = {
  id:string;proposal_id:string;status:'dispatched'|'unknown'|'verified'|'review';
  external_id:number|null;error_code:string|null;created_at:string;verified_at:string|null;
};
export type Inputs = {
  'cw.ticket_search':{q?:string;limit?:number;offset?:number};
  'cw.ticket_context':{ticket_id:string};
  'cw.note_prepare':{ticket_id:string;content:string;visibility?:'internal'};
  'cw.time_entry_prepare':{ticket_id:string;content:string;duration_minutes:number;duration_evidence:string;time_start:string};
  'cw.execute_approved':{proposal_id:string;idempotency_key:string};
  'cw.operation_verify':{operation_id:string};
};
export type Outputs = {
  'cw.ticket_search':{items:Ticket[]};
  'cw.ticket_context':Context;
  'cw.note_prepare':Proposal;
  'cw.time_entry_prepare':Proposal;
  'cw.execute_approved':Receipt;
  'cw.operation_verify':Receipt;
};
export interface ServiceOperations {
  readonly contractVersion:typeof CONTRACT_VERSION;
  call<K extends keyof Inputs>(name:K,input:Inputs[K]):Promise<Outputs[K]>;
}
export type RequestFn = <T>(path:string,method?:string,body?:unknown)=>Promise<T>;

/** Auth, scope, validation and approval remain in Python; no client-side authorization. */
export function httpBridge(request:RequestFn):ServiceOperations {
  return {contractVersion:CONTRACT_VERSION,async call<K extends keyof Inputs>(name:K,input:Inputs[K]):Promise<Outputs[K]> {
    const v=input as unknown as Record<string,unknown>;
    switch(name) {
      case 'cw.ticket_search': {
        const query=new URLSearchParams();
        for(const k of ['q','limit','offset']) if(v[k]!==undefined) query.set(k,String(v[k]));
        return request(`/tickets?${query}`);
      }
      case 'cw.ticket_context':return request(`/workflow/tickets/${encodeURIComponent(String(v.ticket_id))}/context`);
      case 'cw.note_prepare':return request('/workflow/proposals','POST',{...input,kind:'note'});
      case 'cw.time_entry_prepare':return request('/workflow/proposals','POST',{...input,kind:'time'});
      case 'cw.execute_approved':return request(`/workflow/proposals/${encodeURIComponent(String(v.proposal_id))}/execute`,'POST',{idempotency_key:v.idempotency_key});
      case 'cw.operation_verify':return request(`/workflow/operations/${encodeURIComponent(String(v.operation_id))}/verify`,'POST');
      default:throw new Error('Unsupported service operation');
    }
  }};
}
