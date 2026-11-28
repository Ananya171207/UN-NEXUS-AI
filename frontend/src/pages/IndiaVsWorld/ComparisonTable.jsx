import { formatDifference, formatValue, statusText } from './utils';

const MARKS = {
  better: { symbol: '↑', label: 'Better than baseline', className: 'better' },
  worse: { symbol: '↓', label: 'Worse than baseline', className: 'worse' },
  same: { symbol: '=', label: 'Same as baseline', className: 'same' },
};

export default function ComparisonTable({ comparison, indicators }) {
  const codes = comparison?.countries || Object.keys(comparison?.comparison || {});
  const baseline = comparison?.baseline?.country;

  const orderedCodes = [
    baseline,
    ...codes.filter((code) => code !== baseline),
  ].filter(Boolean);

  return (
    <div className="iw-table-wrap">
      <table className="iw-table">
        <thead>
          <tr>
            <th scope="col">Indicator</th>

            {orderedCodes.map((code) => {
              const country = comparison.countryMetadata?.[code];

              return (
                <th
                  scope="col"
                  key={code}
                  className={code === baseline ? 'india-col' : undefined}
                >
                  <div className="iw-country-heading">
                    <span className="iw-country-name">
                      {country?.flagEmoji ? `${country.flagEmoji} ` : ''}
                      {country?.name || code}
                    </span>

                    {code === baseline && (
                      <span className="iw-baseline-label">Baseline</span>
                    )}
                  </div>
                </th>
              );
            })}
          </tr>
        </thead>

        <tbody>
          {indicators.map((indicator) => {
            const analytics = comparison.analytics?.[indicator.key];

            const analyticsByCountry = new Map(
              (analytics?.values || []).map((row) => [
                row.country,
                row,
              ])
            );

            return (
              <tr key={indicator.key}>
                <th scope="row">
                  <div className="iw-indicator-cell">
                    <strong>{indicator.label}</strong>
                    <small>{indicator.unit}</small>
                    <small className="iw-indicator-code">
                      {indicator.worldBankCode}
                    </small>
                  </div>
                </th>

                {orderedCodes.map((code) => {
                  const entry =
                    comparison.comparison?.[code]?.[indicator.key];

                  const analysis = analyticsByCountry.get(code);

                  const mark = analysis?.performanceVsBaseline
                    ? MARKS[analysis.performanceVsBaseline]
                    : null;

                  const contextualComparison =
                    analysis?.comparedWithBaseline;

                  const isBaseline = code === baseline;

                  return (
                    <td
                      key={code}
                      className={isBaseline ? 'india-col' : undefined}
                    >
                      <div className="iw-cell">
                        <div className="iw-cell-main">
                          <strong className="iw-cell-value">
                            {formatValue(indicator, entry)}
                          </strong>

                          {entry?.year && (
                            <span className="iw-cell-year">
                              Reporting year: {entry.year}
                            </span>
                          )}
                        </div>

                        {entry?.stale && (
                          <span className="iw-cell-note">
                            Cached observation
                          </span>
                        )}

                        {entry?.status &&
                          entry.status !== 'available' && (
                            <span className="iw-cell-status">
                              {statusText(entry)}
                            </span>
                          )}

                        {!isBaseline && analysis?.usable && (
                          <div className="iw-cell-comparison">
                            {analysis.absoluteDifference != null && (
                              <div className="iw-difference-row">
                                <span>Difference</span>
                                <strong>
                                  {formatDifference(
                                    indicator,
                                    analysis.absoluteDifference
                                  )}
                                </strong>
                              </div>
                            )}

                            {analysis.percentDifference != null && (
                              <div className="iw-difference-row">
                                <span>vs baseline</span>
                                <strong className="iw-percent-value">
                                  {analysis.percentDifference > 0 ? '+' : ''}
                                  {analysis.percentDifference}%
                                </strong>
                              </div>
                            )}
                          </div>
                        )}

                        {!isBaseline && mark && (
                          <span
                            className={`iw-mark ${mark.className}`}
                            role="img"
                            aria-label={mark.label}
                          >
                            {mark.symbol} {mark.label}
                          </span>
                        )}

                        {!isBaseline && !mark && contextualComparison && (
                          <span className="iw-cell-note">
                            {contextualComparison === 'equal'
                              ? 'Equal to baseline'
                              : `${contextualComparison === 'higher' ? 'Above' : 'Below'} baseline`}
                          </span>
                        )}
                      </div>
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>

      <p className="fine-print iw-table-footnote">
        Differences are measured against the selected baseline.
        Higher-is-better and lower-is-better interpretations follow
        the indicator metadata. Contextual indicators are not
        automatically classified as better or worse. All values are
        from World Bank Open Data.
      </p>
    </div>
  );
}
