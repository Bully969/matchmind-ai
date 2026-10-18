const configuredApiUrl = (import.meta.env.VITE_API_URL || '').trim();
// Hosted builds use the same-origin Vercel rewrite; local dev keeps its explicit API URL.
const API = (import.meta.env.PROD ? '' : configuredApiUrl || 'http://localhost:8000').replace(/\/+$/, '');

export const isApiConfigured = import.meta.env.PROD || Boolean(API);
export const apiBaseUrl = API;

async function request(path, options = {}) {
  try {
    return await requestOnce(path, options);
  } catch (error) {
    // A sleeping backend can outlast the first request. Never repeat writes.
    if ((options.method || 'GET') === 'GET' && error.retryable) {
      return requestOnce(path, options);
    }
    throw error;
  }
}

function temporaryError(message) {
  return Object.assign(new Error(message), {retryable: true});
}

async function requestOnce(path, options = {}) {
  if (!isApiConfigured) {
    const error = new Error('API non configurata in produzione. Imposta VITE_API_URL con l’origine pubblica del backend FastAPI e ridistribuisci il frontend.');
    error.code = 'API_NOT_CONFIGURED';
    throw error;
  }

  const { timeoutMs = 30000, ...fetchOptions } = options;
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${API}${path}`, {
      ...fetchOptions,
      signal: controller.signal,
      headers: {'Content-Type': 'application/json', ...(options.headers || {})},
    });
    if ([502,503,504].includes(response.status)) {
      throw temporaryError(`Backend temporaneamente non disponibile (${response.status}). Riprova tra poco.`);
    }
    let payload;
    try { payload = await response.json(); }
    catch (error) {
      if (controller.signal.aborted) throw error;
      throw new Error(`Risposta API non valida (${response.status}). Riprova tra poco.`);
    }
    if (!response.ok) {
      const detail = typeof payload.detail === 'string' ? payload.detail : `Richiesta fallita (${response.status})`;
      throw new Error(detail);
    }
    return payload;
  } catch (error) {
    if (controller.signal.aborted) throw temporaryError(`Il backend non ha risposto entro ${timeoutMs / 1000} secondi. Potrebbe essere in avvio: riprova tra poco.`);
    if (error instanceof TypeError) throw temporaryError(`Impossibile raggiungere il backend ${API}. Verifica la connessione e riprova.`);
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
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
export const askAnalyst = (message, fixture, analysis) => request('/api/chat', { timeoutMs: 45000, method: 'POST', body: JSON.stringify({ message, fixture, fixture_id: fixture.id, competition_id: fixture.competition_id, fixture_date: fixture.kickoff_date || fixture.kickoff?.slice(0,10) }) });
export const getPredictions = () => request('/api/predictions?limit=10');
export const getRecommendations = (from, to, competition, limit = 20) => {
  const p = new URLSearchParams({ date_from: from, date_to: to, limit: String(limit) });
  if (competition) p.set('competition_id', competition);
  return request(`/api/recommendations?${p.toString()}`);
};
