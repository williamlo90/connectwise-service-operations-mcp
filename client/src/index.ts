import { createInterface } from 'node:readline/promises';
import { stdin, stdout } from 'node:process';
import { consumerSmoke,workflowCLI } from './workflow-cli.js';
import { assistantCLI } from './assistant-cli.js';

type Identity = {id:string;tenant_id:string;role:string;platform_mode:string};
type Ticket = {id:string;summary:string;company_name:string;status:string};
const base = new URL(process.env.API_URL ?? 'http://127.0.0.1:8030');
if (base.protocol !== 'https:' && !(base.protocol === 'http:' && ['api','localhost','127.0.0.1'].includes(base.hostname))) {
  throw new Error('Use HTTPS outside the local demo network');
}
let token: string | undefined;
async function call<T>(path: string, method='GET', body?: unknown): Promise<T> {
  const response = await fetch(new URL(path,base), {method,headers:{'Content-Type':'application/json',...(token ? {Authorization:`Bearer ${token}`} : {})},
    body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(path.startsWith('/assistant/')?110000:10000)});
  if (!response.ok) throw new Error(`Request failed (${response.status}); correlation=${response.headers.get('x-correlation-id') ?? 'unknown'}`);
  return response.status===204 ? undefined as T : await response.json() as T;
}
const username = process.env.DEMO_USERNAME ?? 'op-a';
const password = process.env.DEMO_PASSWORD;
if (!password) throw new Error('Set DEMO_PASSWORD through the local environment; never pass it as a command argument');
try {
  token = (await call<{access_token:string}>('/auth/login','POST',{username,password})).access_token;
  const identity = await call<Identity>('/me');
  console.log(`Synthetic local data | ${identity.id} | tenant ${identity.tenant_id} | ${identity.role}`);
  async function list() {
    const page = await call<{items:Ticket[]}>('/tickets');
    console.table(page.items);
    return page.items;
  }
  const rows=process.argv.includes('--ai')?[]:await list();
  if(process.argv.includes('--ai')) {
    await assistantCLI(call,process.argv.slice(process.argv.indexOf('--ai')+1));
  } else if(process.argv.includes('--consumer-smoke')) {
    await consumerSmoke(call);
  } else if(process.argv.includes('--workflow')) {
    await workflowCLI(call,process.argv.slice(process.argv.indexOf('--workflow')+1));
  } else if(process.argv.includes('--smoke')) {
    if(rows.length!==1) throw new Error('Unexpected scope result');
    const detail=await call<Ticket>(`/tickets/${encodeURIComponent(rows[0]!.id)}`);
    if(detail.id!==rows[0]!.id) throw new Error('Unexpected ticket detail');
    console.log('Reference client login/list/detail PASS');
  } else {
    const rl=createInterface({input:stdin,output:stdout});
    try {
      while(true) {
        const command=(await rl.question('Ticket ID, list, or quit > ')).trim();
        if(command==='quit') break;
        try {if(command==='list') await list(); else console.log(await call<Ticket>(`/tickets/${encodeURIComponent(command)}`));}
        catch(error) {console.error((error as Error).message);}
      }
    } finally {rl.close();}
  }
} catch(error) {console.error((error as Error).message);process.exitCode=1;}
finally {if(token) {try {await call<void>('/auth/logout','POST');} catch {console.error('Logout unavailable; session will expire.');}}}
