const STATUS_LABELS = {
  available: 'Available',
  no_data: 'Not reported by the World Bank',
  pending: 'Still loading — retry shortly',
  error: 'Unavailable',
};

export function statusText(entryOrStatus) {
  const status = typeof entryOrStatus === 'string'
    ? entryOrStatus
    : entryOrStatus?.status;
  return STATUS_LABELS[status] || 'Not available';
}

export function formatValue(indicator, entryOrValue) {
  if (entryOrValue === null || entryOrValue === undefined) return '—';

  let value = entryOrValue;
  if (typeof entryOrValue === 'object') {
    if (entryOrValue.status && entryOrValue.status !== 'available') {
      return statusText(entryOrValue);
    }
    value = entryOrValue.value;
  }

  if (value === null || value === undefined || typeof value !== 'number' || !Number.isFinite(value)) {
    return '—';
  }

  const format = indicator?.format || {};
  const decimals = Number.isInteger(format.decimals) ? format.decimals : 2;
  const options = {
    maximumFractionDigits: decimals,
    minimumFractionDigits: 0,
  };

  if (format.kind === 'currency') {
    return new Intl.NumberFormat('en-US', {
      ...options,
      style: 'currency',
      currency: 'USD',
      notation: format.compact ? 'compact' : 'standard',
      maximumFractionDigits: format.compact ? Math.min(decimals || 1, 1) : decimals,
    }).format(value);
  }

  if (format.kind === 'count') {
    return new Intl.NumberFormat('en-US', {
      ...options,
      notation: format.compact ? 'compact' : 'standard',
    }).format(value);
  }

  const number = new Intl.NumberFormat('en-US', options).format(value);
  if (format.kind === 'percent') return `${number}%`;
  if (format.kind === 'years') return `${number} years`;
  if (format.kind === 'tonnes_per_capita') return `${number} t CO₂e/person`;
  if (format.kind === 'concentration') return `${number} µg/m³`;

  return `${format.prefix || ''}${number}${format.suffix || ''}`;
}

export function formatDifference(indicator, value) {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  const decimals = Number.isInteger(indicator?.format?.decimals)
    ? indicator.format.decimals
    : 2;
  const formatted = new Intl.NumberFormat('en-US', {
    maximumFractionDigits: decimals,
    minimumFractionDigits: 0,
  }).format(Math.abs(value));
  const sign = value > 0 ? '+' : value < 0 ? '−' : '';
  return `${sign}${formatted} ${indicator?.differenceUnit || indicator?.unit || ''}`.trim();
}
