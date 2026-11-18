import {
  Bar, BarChart, CartesianGrid, Cell, LabelList, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { chartColors } from '../../styles/chartTheme';
import { formatValue } from './utils';

// Horizontal bars: India highlighted, others muted, dashed line = sample median.
export default function BarComparison({ indicator, rows, median }) {
  const height = rows.length * 38 + 50;
  return (
    <div style={{ width: '100%', height }} role="img" aria-label={`${indicator.label}: India compared with other sample countries`}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical" margin={{ top: 6, right: 70, left: 4, bottom: 0 }}>
          <CartesianGrid stroke={chartColors.grid} strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" stroke={chartColors.axis} tick={{ fontSize: 11 }} tickLine={false} axisLine={{ stroke: chartColors.grid }} />
          <YAxis type="category" dataKey="name" width={104} stroke={chartColors.axis} tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
          <Tooltip
            cursor={{ fill: 'rgba(255,255,255,0.04)' }}
            formatter={(value) => [formatValue(indicator, value), `${indicator.label} (sample)`]}
            contentStyle={{ background: chartColors.tooltipBg, border: `1px solid ${chartColors.tooltipBorder}`, borderRadius: 4, fontSize: 12 }}
            labelStyle={{ color: chartColors.axis }}
            itemStyle={{ color: '#ebebe8' }}
          />
          <ReferenceLine x={median} stroke={chartColors.amber} strokeDasharray="5 4" label={{ value: 'sample median', fill: chartColors.amber, fontSize: 10, position: 'top' }} />
          <Bar dataKey="value" radius={[0, 3, 3, 0]} animationDuration={900}>
            {rows.map((row) => <Cell key={row.id} fill={row.id === 'IN' ? chartColors.accent : chartColors.teal} fillOpacity={row.id === 'IN' ? 1 : 0.6} />)}
            <LabelList dataKey="label" position="right" fill={chartColors.axis} fontSize={11} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
