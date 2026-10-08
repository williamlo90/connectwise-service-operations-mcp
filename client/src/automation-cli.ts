import type { RequestFn } from './service-operations-v1.js';

export async function automationCLI(request:RequestFn,args:string[]) {
  const [command,id]=args;
  let result:unknown;
  if(command==='status')result=await request('/automation/status');
  else if(command==='jobs'){
    const offset=Number(id??0);
    if(!Number.isInteger(offset)||offset<0||offset>10000)throw new Error('Offset must be an integer from 0 to 10000');
    result=await request(`/automation/jobs?offset=${offset}`);
  }else if(command==='retry'&&id)result=await request(`/automation/jobs/${encodeURIComponent(id)}/retry`,'POST');
  else if(command==='pause'||command==='resume'){
    const current=await request<{schedule:{interval_seconds:number}|null}>('/automation/status');
    result=await request('/automation/schedule','POST',{enabled:command==='resume',interval_seconds:current.schedule?.interval_seconds??300});
  }else throw new Error('Usage: --automation status|jobs [offset]|retry JOB_ID|pause|resume');
  console.log(JSON.stringify(result,null,2));
}
