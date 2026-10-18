import { beforeEach, expect, test, vi } from 'vitest';
import { act, render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import * as api from '../api';
vi.mock('../api', () => ({
  isApiConfigured: true, getHealth: vi.fn(), getCompetitions: vi.fn(),
  getFixtures: vi.fn(), getPredictions: vi.fn(), getRecommendations: vi.fn(),
  analyzeMatch: vi.fn(), askAnalyst: vi.fn(),
}));
const fixture = {id:'fixture-test',home_team:'Casa Test',away_team:'Ospiti Test',competition_id:'test',competition_name:'Test League',kickoff:'2026-10-17T20:00:00+02:00',kickoff_time_known:true,status:'SCHEDULED',source:'test'};
beforeEach(() => {
  vi.clearAllMocks();
  api.getHealth.mockResolvedValue({status:'ok',data_provider:'test',ai_provider:'template'});
  api.getCompetitions.mockResolvedValue({items:[{id:'test',name:'Test League'}]});
  api.getFixtures.mockResolvedValue({items:[fixture]});
  api.getPredictions.mockResolvedValue({items:[]});
  api.getRecommendations.mockResolvedValue({items:[],ranked_candidates:[]});
});
async function ready() {render(<App/>);await waitFor(()=>expect(screen.queryByRole('status')).not.toBeInTheDocument());}
test('settings renders provider status without crashing',async()=>{
  await ready();await userEvent.click(screen.getByRole('button',{name:/⚙.*Impostazioni/}));
  expect(screen.getByRole('heading',{name:'Impostazioni',level:1})).toBeVisible();
  expect(screen.getByText('Motore AI: Non verificato')).toBeVisible();
  expect(screen.getByText('Provider dichiarato dal backend: template')).toBeVisible();
});
test('live unavailable page navigates back to calendar',async()=>{
  await ready();const nav=within(screen.getByRole('navigation',{name:'Navigazione principale'}));
  await userEvent.click(nav.getByRole('button',{name:/Diretta/}));
  await userEvent.click(screen.getByRole('button',{name:'Vai al calendario'}));
  expect(screen.getByRole('heading',{name:'Calendario partite'})).toBeVisible();
});
test('all sidebar destinations render and return home',async()=>{
  await ready();const nav=within(screen.getByRole('navigation',{name:'Navigazione principale'}));
  for (const name of ['Calendario','Diretta','Pronostici AI','Quote & Mercati','Report giornalieri','Archivio pronostici','Performance Lab','Simulatore','Impostazioni']) {
    const button=name==='Impostazioni'?screen.getByRole('button',{name:/⚙.*Impostazioni/}):nav.getByRole('button',{name:new RegExp(name)});
    await userEvent.click(button);expect(screen.getByRole('heading',{level:1,name})).toBeVisible();
    await userEvent.click(screen.getByRole('button',{name:'Torna alla Home'}));
  }
});
test('mobile more menu opens settings and closes',async()=>{
  await ready();await userEvent.click(within(screen.getByRole('navigation',{name:'Navigazione mobile'})).getByRole('button',{name:/Altro/}));
  await userEvent.click(screen.getAllByRole('button',{name:/Impostazioni/}).at(-1));
  expect(screen.getByRole('heading',{name:'Impostazioni',level:1})).toBeVisible();
  expect(screen.queryByText('Altre sezioni')).not.toBeInTheDocument();
});
test('calendar failure clears stale matches; retry restores data',async()=>{
  await ready();await userEvent.click(within(screen.getByRole('navigation',{name:'Navigazione principale'})).getByRole('button',{name:/Calendario/}));
  expect(screen.getByText('Casa Test')).toBeVisible();
  api.getFixtures.mockRejectedValueOnce(new Error('offline'));
  await userEvent.click(screen.getByRole('button',{name:/Sincronizza/}));
  expect(await screen.findByRole('alert')).toHaveTextContent('calendario partite');
  expect(screen.queryByText('Casa Test')).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('button',{name:/Sincronizza/}));
  expect(await screen.findByText('Casa Test')).toBeVisible();
});
test('older response cannot overwrite a newer calendar request',async()=>{
  let resolveOld;api.getFixtures.mockReturnValueOnce(new Promise(resolve=>{resolveOld=resolve;}));
  render(<App/>);expect(screen.getByRole('status')).toBeVisible();
  await userEvent.click(screen.getByRole('button',{name:/Aggiorna connessione/}));
  await waitFor(()=>expect(screen.queryByRole('status')).not.toBeInTheDocument());
  await act(async()=>resolveOld({items:[{...fixture,id:'old',home_team:'Stale Team'}]}));
  await waitFor(()=>expect(api.getFixtures).toHaveBeenCalledTimes(2));
  expect(screen.queryByText('Stale Team')).not.toBeInTheDocument();
});

test('match center tabs render unavailable data honestly',async()=>{
  await ready();
  for (const [tab, text] of [['Statistiche','Metriche non disponibili per questa fonte'],['Formazioni','Formazioni ufficiali'],['Stats giocatore','Statistiche giocatori'],['Sintesi','Analisi contestuale da completare']]) {
    await userEvent.click(screen.getByRole('button',{name:tab,exact:true}));
    expect(screen.getByText(text)).toBeVisible();
  }
});
test('late chat answer is discarded when the selected context changes',async()=>{
  let resolveAnswer;api.askAnalyst.mockReturnValueOnce(new Promise(resolve=>{resolveAnswer=resolve;}));
  await ready();await userEvent.click(screen.getByRole('button',{name:/Invia domanda/}));
  expect(api.askAnalyst).toHaveBeenCalled();
  await userEvent.click(screen.getByRole('button',{name:/Domani/}));
  api.getFixtures.mockResolvedValueOnce({items:[]});
  await userEvent.click(screen.getByRole('button',{name:/Aggiorna connessione/}));
  await act(async()=>resolveAnswer({answer:'OLD CONTEXT ANSWER',provider:'template'}));
  expect(screen.queryByText(/OLD CONTEXT ANSWER/)).not.toBeInTheDocument();
});

test('regression: initial calendar preserves the seven-day window',async()=>{
  await ready();
  const [from,to]=api.getFixtures.mock.calls[0];
  const days=(new Date(`${to}T12:00:00Z`)-new Date(`${from}T12:00:00Z`))/86400000;
  expect(days).toBe(7);
});
test('regression: refreshing keeps the selected second match',async()=>{
  const second={...fixture,id:'second',home_team:'Second Home',away_team:'Second Away'};
  api.getFixtures.mockResolvedValue({items:[fixture,second]});
  await ready();
  await userEvent.click(screen.getByRole('button',{name:/Test League.*Second Home.*Second Away/}));
  expect(screen.getByRole('heading',{name:'Second Home'})).toBeVisible();
  await userEvent.click(screen.getByRole('button',{name:/Aggiorna connessione/}));
  await waitFor(()=>expect(screen.queryByRole('status')).not.toBeInTheDocument());
  expect(screen.getByRole('heading',{name:'Second Home'})).toBeVisible();
});
