import { SAMPLE_SCORES, SERIES_END_YEAR, SERIES_START_YEAR, STATUS_BANDS } from '../../data/sdgProgress';

export function statusFor(score) {
  return STATUS_BANDS.find((band) => score >= band.min) || STATUS_BANDS[STATUS_BANDS.length - 1];
}

export function scoreFor(scopeId, goalNumber) {
  return SAMPLE_SCORES[scopeId]?.[goalNumber - 1] ?? null;
}

export const average = (list) => (list.length ? list.reduce((sum, n) => sum + n, 0) / list.length : 0);

// Straight-line path between the 2015 and 2024 values with a small, fixed
// wobble so the sample charts look like real series. Deterministic: the same
// inputs always give the same chart.
export function buildSeries([from, to], seed) {
  const years = SERIES_END_YEAR - SERIES_START_YEAR;
  const span = Math.abs(to - from);
  return Array.from({ length: years + 1 }, (_, i) => {
    const t = i / years;
    const wobble = i === 0 || i === years ? 0 : Math.sin(i * 1.7 + seed) * span * 0.04;
    return { year: String(SERIES_START_YEAR + i), value: Number((from + (to - from) * t + wobble).toFixed(1)) };
  });
}

// Plain-language reading of an indicator: which way it moved and how far the
// 2024 value still is from the target.
export function describeIndicator(indicator, pair) {
  const [from, to] = pair;
  const change = Number((to - from).toFixed(1));
  const improving = indicator.better === 'higher' ? change > 0 : change < 0;
  const flat = change === 0;
  let gap = null;
  if (indicator.target !== null) {
    const raw = indicator.better === 'higher' ? indicator.target - to : to - indicator.target;
    gap = raw <= 0 ? 0 : Number(raw.toFixed(1));
  }
  return { change, flat, improving, gap };
}

export function sortGoals(goals, sort, scopeId) {
  const list = [...goals];
  if (sort === 'score-desc') list.sort((a, b) => scoreFor(scopeId, b.number) - scoreFor(scopeId, a.number));
  if (sort === 'score-asc') list.sort((a, b) => scoreFor(scopeId, a.number) - scoreFor(scopeId, b.number));
  return list;
}
