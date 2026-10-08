import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { fileURLToPath } from 'node:url';
import { CONTRACT_VERSION, type ServiceOperations, type Inputs, type Outputs } from './service-operations-v1.js';

export async function connectMCP(token:string,options:{url?:string;timeout?:number}={}) {
  const transport=new StdioClientTransport({command:process.execPath,args:[fileURLToPath(new URL('./mcp-server.js',import.meta.url))],env:{API_URL:options.url??process.env.API_URL??'http://127.0.0.1:8030',MCP_ACCESS_TOKEN:token,MCP_TIMEOUT_MS:String(options.timeout??10000)},stderr:'pipe'});
  const client=new Client({name:'service-ops-reference-assistant',version:'1.0.0'});
  let stderr='';transport.stderr?.on('data',(chunk:Buffer)=>{stderr=(stderr+chunk.toString()).slice(-4096);});
  try{await client.connect(transport);}catch(error){await transport.close();throw error;}
  const ops:ServiceOperations={contractVersion:CONTRACT_VERSION,async call<K extends keyof Inputs>(name:K,input:Inputs[K]):Promise<Outputs[K]>{
    const result=await client.callTool({name,arguments:input},undefined,{timeout:15000});
    if(result.isError)throw new Error((result.content as {text:string}[])[0]?.text??'MCP failed');
    return (result.structuredContent as {data:Outputs[K]}).data;
  }};
  return {client,ops,stderr:()=>stderr,close:()=>client.close()};
}
