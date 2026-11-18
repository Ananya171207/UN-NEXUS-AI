import { GraduationCap, Globe, Thermometer, Wheat, Zap, Bot } from 'lucide-react';
import Accordion from '../../components/common/Accordion';
import { SUGGESTED_QUESTIONS } from '../../data/suggestedQuestions';
import ProvenanceLegend from './ProvenanceLegend';

const ICONS = {
  thermometer: Thermometer,
  globe: Globe,
  wheat: Wheat,
  graduation: GraduationCap,
  zap: Zap,
};

// Shown before the first question: explains the tool and offers starting points.
export default function EmptyThread({ onAsk, loading }) {
  return (
    <div className="empty-thread">
      <div className="hero-icon"><Bot size={26} /></div>
      <h2>Start a research question</h2>
      <p>
        Ask about global development, the Sustainable Development Goals or specific countries.
        Each answer is researched from live UN and partner sources and organised into a summary, findings, statistics, sources and related topics.
      </p>

      <h3 className="section-label">Suggested research questions</h3>
      <div className="suggestions">
        {SUGGESTED_QUESTIONS.map((item, i) => {
          const Icon = ICONS[item.icon] || Globe;
          return (
            <button
              key={item.id}
              type="button"
              className="suggestion reveal"
              style={{ '--i': i }}
              disabled={loading}
              onClick={() => onAsk(item.question)}
            >
              <span className="suggestion-icon"><Icon size={16} /></span>
              <span>
                <small>{item.category}</small>
                <strong>{item.question}</strong>
              </span>
            </button>
          );
        })}
      </div>

      <div className="legend-wrap">
        <Accordion title="How answers are labelled" defaultOpen>
          <ProvenanceLegend />
        </Accordion>
      </div>
    </div>
  );
}
