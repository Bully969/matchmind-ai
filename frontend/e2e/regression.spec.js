import { test, expect } from '@playwright/test';
// Synthetic fixtures are confined to this test harness, never deployed as product data.
const fixtures = ['Alpha Test','Beta Test'].map((home_team,i)=>({id:`test-${i}`,home_team,away_team:'Visitor Test',competition_id:'test',competition_name:'Test League',kickoff:'2026-10-17T18:00:00Z',kickoff_time_known:false,status:'SCHEDULED',source:'test'}));
let unavailable, empty;
test.beforeEach(async({page})=>{
  unavailable=false;empty=false;
  await page.route('**/api/**',async route=>{
    const path=new URL(route.request().url()).pathname;
    if(unavailable) return route.fulfill({status:503,contentType:'application/json',body:'{"detail":"offline test"}'});
    const body=path.endsWith('/health')?{status:'ok',data_provider:'test',ai_provider:'gemini'}:
      path.endsWith('/competitions')?{items:[{id:'test',name:'Test League'}]}:
      path.endsWith('/fixtures')?{items:empty?[]:fixtures}:{items:[],ranked_candidates:[]};
    await route.fulfill({json:body});
  });
});
async function navigate(page,label,isMobile){
  if(isMobile){
    const nav=page.getByRole('navigation',{name:'Navigazione mobile'});
    if(['Home','Calendario','Diretta','Pronostici'].includes(label)) await nav.getByRole('button',{name:new RegExp(label)}).click();
    else {await nav.getByRole('button',{name:/Altro/}).click();await page.locator('.mobile-more-menu').getByRole('button',{name:new RegExp(label)}).click();}
  }else await page.locator('aside').getByRole('button',{name:new RegExp(label)}).click();
}
test('navigation, settings and live to calendar do not crash',async({page,isMobile})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/');await expect(page.getByRole('heading',{name:'Alpha Test',exact:true})).toBeVisible();
  for(const label of ['Calendario','Diretta','Quote & Mercati','Report giornalieri','Archivio pronostici','Performance Lab','Simulatore','Impostazioni']){
    await navigate(page,label,isMobile);await expect(page.getByRole('heading',{name:label,level:1})).toBeVisible();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  }
  await expect(page.getByText('Motore AI: Non verificato')).toBeVisible();
  await navigate(page,'Diretta',isMobile);await page.getByRole('button',{name:'Vai al calendario'}).click();
  await expect(page.getByRole('heading',{name:'Calendario partite'})).toBeVisible();
  expect(errors).toEqual([]);
});
test('selected match survives refresh and missing time remains unknown',async({page})=>{
  await page.goto('/');await page.locator('.fixture-mini').filter({hasText:'Beta Test'}).click();
  await page.getByRole('button',{name:'↻ Aggiorna dati',exact:true}).click();
  await expect(page.getByRole('status')).toHaveCount(0);
  await expect(page.getByRole('heading',{name:'Beta Test',exact:true})).toBeVisible();
  await expect(page.locator('.fixture-mini').first()).toContainText('confermare');
});
test('API outage, retry, empty results and reload',async({page,isMobile})=>{
  await page.goto('/');await expect(page.getByRole('heading',{name:'Alpha Test',exact:true})).toBeVisible();
  unavailable=true;await page.getByRole('button',{name:'↻ Aggiorna dati',exact:true}).click();
  await expect(page.getByRole('alert')).toBeVisible();await expect(page.getByRole('heading',{name:'Nessuna partita selezionata'})).toBeVisible();
  unavailable=false;await page.getByRole('button',{name:'↻ Aggiorna dati',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Alpha Test',exact:true})).toBeVisible();
  await navigate(page,'Calendario',isMobile);empty=true;
  await page.getByLabel('Dal',{exact:true}).fill('2026-10-18');
  await page.getByLabel('Al',{exact:true}).fill('2026-10-18');
  await page.getByLabel('Campionato',{exact:true}).selectOption('test');
  await expect(page.getByText('Nessuna partita nell’intervallo selezionato')).toBeVisible();
  empty=false;await page.reload();await expect(page.getByRole('heading',{name:'Alpha Test',exact:true})).toBeVisible();
});
test('chat labels provider failures and subsequent successful response',async({page})=>{
  let fallback=true;
  await page.route('**/api/chat',route=>route.fulfill({json:fallback
    ? {answer:'Sintesi dei dati verificati.',provider:'template',fallback:true,fallback_reason:'AUTHENTICATION_FAILED'}
    : {answer:'La fonte è test.',provider:'openai_compatible',fallback:false}}));
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Alpha Test',exact:true})).toBeVisible();
  await page.getByPlaceholder('Fai una domanda sulla partita selezionata…').fill('Qual è la fonte?');
  await page.getByRole('button',{name:'Invia domanda ↗'}).click();
  await expect(page.locator('.analyst-answer')).toContainText('Autenticazione del provider AI non riuscita.');
  fallback=false;
  await page.getByRole('button',{name:'Invia domanda ↗'}).click();
  await expect(page.locator('.analyst-answer')).toContainText('Motore: openai_compatible');
  await expect(page.locator('.analyst-answer')).not.toContainText('risposta di riserva');
});

test('mobile calendar and chat have readable fields and touch targets',async({page,isMobile})=>{
  test.skip(!isMobile, 'Mobile-specific typography and touch contract');
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Alpha Test',exact:true})).toBeVisible();
  for (const locator of [page.locator('.global-search input'),page.locator('.analyst-chat-form textarea')]) {
    expect(await locator.evaluate(el=>parseFloat(getComputedStyle(el).fontSize))).toBeGreaterThanOrEqual(16);
  }
  await navigate(page,'Calendario',isMobile);
  for (const locator of [page.getByLabel('Dal',{exact:true}),page.getByLabel('Al',{exact:true}),page.getByLabel('Campionato',{exact:true})]) {
    expect(await locator.evaluate(el=>parseFloat(getComputedStyle(el).fontSize))).toBeGreaterThanOrEqual(16);
    expect((await locator.boundingBox()).height).toBeGreaterThanOrEqual(44);
  }
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
});
