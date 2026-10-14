// Unknown kickoff times are calendar dates, never instants at an invented noon.
export function formatFixtureDate(fixture) {
  if (!fixture?.kickoff) return 'Data non disponibile';
  if (fixture.kickoff_time_known === false) {
    const date = fixture.kickoff_date || fixture.kickoff.slice(0, 10);
    const value = new Date(`${date}T12:00:00Z`);
    if (Number.isNaN(value.getTime())) return 'Data non disponibile · orario da confermare';
    return `${value.toLocaleDateString('it-IT', {day:'2-digit',month:'short',timeZone:'UTC'})} · orario da confermare`;
  }
  const value = new Date(fixture.kickoff);
  return Number.isNaN(value.getTime()) ? 'Data non disponibile' : value.toLocaleString('it-IT', {day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',timeZone:'Europe/Rome'});
}
