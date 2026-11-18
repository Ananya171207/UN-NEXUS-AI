import { INDICATORS } from '../../data/comparisonData';
import { formatValue, medianOf, versusIndia } from './utils';

const MARK = { better: '▲', worse: '▼', same: '=', neutral: '' };
const MARK_LABEL = { better: 'better than India', worse: 'worse than India', same: 'same as India', neutral: '' };

export default function ComparisonTable({ india, others, sampleSet }) {
  return (
    <div className="iw-table-wrap">
      <table className="iw-table">
        <thead>
          <tr>
            <th scope="col">Indicator</th>
            <th scope="col" className="india-col">India</th>
            {others.map((c) => <th scope="col" key={c.id}>{c.name}</th>)}
            <th scope="col">Sample median</th>
          </tr>
        </thead>
        <tbody>
          {INDICATORS.map((indicator) => {
            const indiaValue = indicator.get(india);
            return (
              <tr key={indicator.id}>
                <th scope="row">
                  {indicator.label}
                  <small>{indicator.unit}</small>
                </th>
                <td className="india-col">{formatValue(indicator, indiaValue)}</td>
                {others.map((c) => {
                  const value = indicator.get(c);
                  const state = versusIndia(indicator, value, indiaValue);
                  return (
                    <td key={c.id}>
                      {formatValue(indicator, value)}
                      {state !== 'neutral' && <span className={`iw-mark ${state}`} role="img" aria-label={MARK_LABEL[state]}>{MARK[state]}</span>}
                    </td>
                  );
                })}
                <td className="muted">{formatValue(indicator, Number(medianOf(indicator, sampleSet).toFixed(1)))}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="fine-print">▲ better than India · ▼ worse than India · = equal. Size indicators (GDP, population, urban share) are not marked. Sample data.</p>
    </div>
  );
}
