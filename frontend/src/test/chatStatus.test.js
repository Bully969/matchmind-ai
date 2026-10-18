import { expect, test } from 'vitest';
import { formatChatAnswer } from '../chatStatus';
test('provider failure is visibly distinguished from a generated answer',()=>{
  expect(formatChatAnswer({answer:'Sintesi',provider:'template',fallback:true,fallback_reason:'AUTHENTICATION_FAILED'})).toContain('Autenticazione del provider AI non riuscita.');
});
test('legacy responses remain compatible',()=>{
  expect(formatChatAnswer({answer:'Sintesi',provider:'template',fallback:true})).toBe('Sintesi\n\nMotore: template · risposta di riserva');
});
test('unknown server error details are not echoed',()=>{
  expect(formatChatAnswer({answer:'Sintesi',provider:'template',fallback:true,fallback_reason:'secret-value'})).not.toContain('secret-value');
});
test('successful generation is not labelled fallback',()=>{
  expect(formatChatAnswer({answer:'Risposta',provider:'openai_compatible',fallback:false})).toBe('Risposta\n\nMotore: openai_compatible');
});
