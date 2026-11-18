import { AlertTriangle, Info } from 'lucide-react';
import Accordion from '../../components/common/Accordion';
import useAsync from '../../hooks/useAsync';
import { getResearchStatus } from '../../services/researchService';

const loadStatus = () => getResearchStatus();

// Always visible: says plainly whether the research backend is reachable and configured.
export default function ModeBanner() {
  const { data, error, loading, reload } = useAsync(loadStatus);

  if (loading) {
    return (
      <div className="mode-banner live" role="status">
        <Info size={15} />
        <div><strong>Checking the research service…</strong></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mode-banner demo" role="alert">
        <AlertTriangle size={15} />
        <div>
          <strong>Research service unavailable</strong>
          <p>{error.message}</p>
          <button type="button" className="btn" onClick={reload}>Check again</button>
        </div>
      </div>
    );
  }

  if (!data.ready) {
    return (
      <div className="mode-banner demo" role="alert">
        <AlertTriangle size={15} />
        <div>
          <strong>Research backend is not configured</strong>
          <p>No answers will be produced until this is fixed: {data.problems.join('; ')}.</p>
          <Accordion title="How to fix it">
            <ul className="plain-list">
              <li>In the <code>backend</code> folder, copy <code>.env.example</code> to <code>.env</code>.</li>
              <li>Set {data.missing.map((name) => <code key={name}>{name} </code>)} to your own keys.</li>
              <li>Restart the backend, then <button type="button" className="btn btn-ghost" onClick={reload}>check again</button>.</li>
            </ul>
          </Accordion>
        </div>
      </div>
    );
  }

  return (
    <div className="mode-banner live" role="status">
      <Info size={15} />
      <div>
        <strong>Connected to the research service</strong>
        <p>Answers are written by {data.ai.model} from sources retrieved live through {data.search.provider}. Each statement links to the source it came from.</p>
      </div>
    </div>
  );
}
