import { expect, test } from 'vitest';
import { formatFixtureDate } from '../dates';
test('unknown kickoff preserves source date and never renders synthetic noon', () => {
  const label = formatFixtureDate({kickoff:'2026-10-17T12:00:00+14:00',kickoff_time_known:false});
  expect(label).toContain('17');expect(label).toContain('orario da confermare');expect(label).not.toContain('12:00');
});
test('known kickoff uses Europe/Rome with DST', () => {
  expect(formatFixtureDate({kickoff:'2026-10-17T18:45:00Z',kickoff_time_known:true})).toContain('20:45');
  expect(formatFixtureDate({kickoff:'2026-12-17T18:45:00Z',kickoff_time_known:true})).toContain('19:45');
});
test('missing kickoff remains unavailable',()=>expect(formatFixtureDate({})).toBe('Data non disponibile'));
