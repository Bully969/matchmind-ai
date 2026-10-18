"""Resolve a match from the provider, never from browser-supplied facts."""
from datetime import date, datetime, timezone
from fastapi import HTTPException


async def verified_match_context(provider, body):
    legacy = body.fixture or {}
    fixture_id = body.fixture_id or legacy.get('id')
    competition_id = body.competition_id or legacy.get('competition_id')
    match_date = body.fixture_date
    if match_date is None:
        try:
            match_date = date.fromisoformat(str(legacy.get('kickoff', ''))[:10])
        except ValueError:
            pass
    if not isinstance(fixture_id, str) or not fixture_id or not isinstance(competition_id, str) or not competition_id or match_date is None:
        raise HTTPException(status_code=422, detail='Servono identificativo, competizione e data della partita.')
    try:
        fixtures = await provider.fixtures(match_date, match_date, competition_id)
    except Exception:
        raise HTTPException(status_code=502, detail='Non è stato possibile verificare la partita presso la fonte.')
    fixture = next((item for item in fixtures if str(item.get('id')) == fixture_id and str(item.get('competition_id')) == competition_id), None)
    if fixture is None:
        raise HTTPException(status_code=404, detail='Partita non trovata nella fonte selezionata.')
    if provider.is_demo or fixture.get('is_demo'):
        raise HTTPException(status_code=422, detail='Il contesto richiede una partita proveniente da una fonte reale.')
    # Allowlist prevents unknown provider fields becoming instructions or facts.
    keys = ('id', 'competition_id', 'competition_name', 'season', 'home_team', 'away_team',
            'kickoff', 'kickoff_date', 'kickoff_time_known', 'status', 'home_score', 'away_score')
    verified = {key: fixture.get(key) for key in keys}
    verified['source'] = provider.name
    verified['verified_at'] = datetime.now(timezone.utc).isoformat()
    return verified
