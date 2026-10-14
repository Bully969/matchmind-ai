const configuredApiUrl = (import.meta.env.VITE_API_URL || '').trim();
const API = (configuredApiUrl || (import.meta.env.DEV ? 'http://localhost:8000' : '')).replace(/\/+$/, '');

export const isApiConfigured = Boolean(API);
export const apiBaseUrl = API;

async function request(path, options = {}) {
  if (!API) {
    const error = new Error('API non configurata in produzione. Imposta VITE_API_URL con l’origine pubblica del backend FastAPI e ridistribuisci il frontend.');
    error.code = 'API_NOT_CONFIGURED';
    throw error;
  }

  let response;
  try {
    response = await fetch(`${API}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    });
  } catch {
    throw new Error(`Impossibile raggiungere il backend ${API}. Verifica che il servizio sia online e che CORS autorizzi il dominio del frontend.`);
  }

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || `Richiesta fallita (${response.status})`);
  return payload;
}

export const getHealth = () => request('/api/health');
export const getCompetitions = () => request('/api/competitions');
export const getFixtures = (from, to, competition) => {
  const p = new URLSearchParams({ date_from: from, date_to: to });
  if (competition) p.set('competition_id', competition);
  return request(`/api/fixtures?${p.toString()}`);
};
export const analyzeMatch = (fixture, odds) => request('/api/analyze', { method: 'POST', body: JSON.stringify({
  fixture_id: fixture.id, competition_id: fixture.competition_id, competition_name: fixture.competition_name,
  season: fixture.season, kickoff: fixture.kickoff, home_team: fixture.home_team, away_team: fixture.away_team,
  home_team_id: fixture.home_team_id, away_team_id: fixture.away_team_id,
  is_demo: fixture.is_demo, odds_home: odds.home ? Number(odds.home) : null,
  odds_draw: odds.draw ? Number(odds.draw) : null, odds_away: odds.away ? Number(odds.away) : null
}) });
export const askAnalyst = (message, fixture, analysis) => request('/api/chat', { method: 'POST', body: JSON.stringify({ message, fixture, analysis }) });
export const getPredictions = () => request('/api/predictions?limit=10');
export const getRecommendations = (from, to, competition, limit = 20) => {
  const p = new URLSearchParams({ date_from: from, date_to: to, limit: String(limit) });
  if (competition) p.set('competition_id', competition);
  return request(`/api/recommendations?${p.toString()}`);
};
