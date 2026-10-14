import { afterEach, expect, test, vi } from 'vitest';
import { getHealth, askAnalyst } from '../api';
afterEach(()=>{vi.unstubAllGlobals();vi.useRealTimers();});
test('network failure is actionable',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new TypeError('network')));
  await expect(getHealth()).rejects.toThrow('Verifica la connessione');
});
test('validation errors are readable, not object Object',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:422,json:async()=>({detail:[{msg:'invalid'}]})}));
  await expect(getHealth()).rejects.toThrow('Richiesta fallita (422)');
});
test('invalid API payload is reported',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,status:200,json:async()=>{throw new SyntaxError();}}));
  await expect(getHealth()).rejects.toThrow('Risposta API non valida');
});
test('slow request aborts and can be retried',async()=>{
  vi.useFakeTimers();
  vi.stubGlobal('fetch',vi.fn((_,{signal})=>new Promise((_,reject)=>signal.addEventListener('abort',()=>reject(new DOMException('aborted','AbortError'))))));
  const result=expect(getHealth()).rejects.toThrow('30 secondi');
  await vi.advanceTimersByTimeAsync(30000);await result;
  fetch.mockResolvedValue({ok:true,json:async()=>({status:'ok'})});
  await expect(getHealth()).resolves.toEqual({status:'ok'});
});

test('chat sends identifiers rather than browser-supplied facts',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>({answer:'ok'})}));
  await askAnalyst('Contesto?',{id:'match',competition_id:'test',kickoff:'2026-10-17T12:00:00Z',home_team:'FORGED'}, {probabilities:{home:1}});
  const payload=JSON.parse(fetch.mock.calls[0][1].body);
  expect(payload).toEqual({message:'Contesto?',fixture_id:'match',competition_id:'test',fixture_date:'2026-10-17'});
});
