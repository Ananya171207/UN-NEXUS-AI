// Number and date formatting shared by all pages.

export function formatPopulation(millions) {
  if (millions >= 1000) return `${(millions / 1000).toFixed(2)} billion`;
  const rounded = millions >= 100 ? Math.round(millions) : Number(millions.toFixed(1));
  return `${rounded} million`;
}

export function formatGdp(billions) {
  if (billions >= 1000) return `$${(billions / 1000).toFixed(2)} trillion`;
  return `$${Math.round(billions)} billion`;
}

export function gdpPerCapita(country) {
  return Math.round((country.gdpB * 1e9) / (country.populationM * 1e6));
}

export function formatUsd(value) {
  return `$${value.toLocaleString('en-US')}`;
}

export function formatRelative(iso, nowMs = Date.now()) {
  const minutes = Math.max(0, Math.round((nowMs - new Date(iso).getTime()) / 60000));
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  return `${days} d ago`;
}

export function formatTime(iso) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function formatDateTime(iso) {
  return new Date(iso).toLocaleString([], {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function startOfDay(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
}

export function dayLabel(iso, nowMs = Date.now()) {
  const diff = Math.round((startOfDay(new Date(nowMs)) - startOfDay(new Date(iso))) / 86400000);
  if (diff === 0) return 'Today';
  if (diff === 1) return 'Yesterday';
  return new Date(iso).toLocaleDateString([], { weekday: 'short', day: 'numeric', month: 'short' });
}
