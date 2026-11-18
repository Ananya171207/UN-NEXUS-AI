import {
  Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { chartColors } from '../../styles/chartTheme';
import { sdgs } from '../../data/sdg';
import { SAMPLE_SCORES } from '../../data/sdgProgress';

// All 17 sample scores side by side. When the scope is not "World", the
// world score is drawn next to it for comparison.
export default function SdgScoreChart({ scopeId, scopeLabel, selected, onSelect }) {
  const compare = scopeId !== 'world';
  const data = sdgs.map((goal) => ({
    goal: String(goal.number),
    name: goal.name,
    color: goal.color,
    score: SAMPLE_SCORES[scopeId][goal.number - 1],
    world: SAMPLE_SCORES.world[goal.number - 1],
  }));

  return (
    <div className="sdgt-score-chart" role="img" aria-label={`Sample progress score for each of the 17 goals: ${scopeLabel}`}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }} onClick={(state) => state?.activeLabel && onSelect(Number(state.activeLabel))}>
          <CartesianGrid stroke={chartColors.grid} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="goal" stroke={chartColors.axis} tick={{ fontSize: 11 }} tickLine={false} axisLine={{ stroke: chartColors.grid }} />
          <YAxis domain={[0, 100]} stroke={chartColors.axis} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
          <Tooltip
            cursor={{ fill: 'rgba(255,255,255,0.04)' }}
            labelFormatter={(label, items) => `Goal ${label}: ${items?.[0]?.payload?.name ?? ''}`}
            formatter={(value, key) => [`${value}/100`, key === 'world' ? 'World (sample)' : `${scopeLabel} (sample)`]}
            contentStyle={{ background: chartColors.tooltipBg, border: `1px solid ${chartColors.tooltipBorder}`, borderRadius: 4, fontSize: 12 }}
            labelStyle={{ color: chartColors.axis }}
            itemStyle={{ color: '#ebebe8' }}
          />
          {compare && <Legend formatter={(key) => (key === 'world' ? 'World (sample)' : `${scopeLabel} (sample)`)} wrapperStyle={{ fontSize: 11 }} />}
          <Bar dataKey="score" radius={[3, 3, 0, 0]} animationDuration={900} cursor="pointer">
            {data.map((row) => (
              <Cell key={row.goal} fill={row.color} fillOpacity={Number(row.goal) === selected ? 1 : 0.7} />
            ))}
          </Bar>
          {compare && <Bar dataKey="world" fill={chartColors.axis} fillOpacity={0.45} radius={[3, 3, 0, 0]} animationDuration={900} />}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
