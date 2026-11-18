import {
  CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { chartColors } from '../../styles/chartTheme';

// Small line chart for one sample indicator, with an optional dashed 2030 target line.
export default function IndicatorChart({ data, unit, target, color }) {
  return (
    <div className="sdgt-chart" role="img" aria-label="Indicator trend from 2015 to 2024 (sample data)">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 10, left: -14, bottom: 0 }}>
          <CartesianGrid stroke={chartColors.grid} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="year" stroke={chartColors.axis} tick={{ fontSize: 10 }} tickLine={false} axisLine={{ stroke: chartColors.grid }} />
          <YAxis stroke={chartColors.axis} tick={{ fontSize: 10 }} tickLine={false} axisLine={false} domain={['auto', 'auto']} />
          <Tooltip
            formatter={(value) => [`${value}${unit ? ` ${unit}` : ''}`, 'Sample value']}
            contentStyle={{ background: chartColors.tooltipBg, border: `1px solid ${chartColors.tooltipBorder}`, borderRadius: 4, fontSize: 12 }}
            labelStyle={{ color: chartColors.axis }}
            itemStyle={{ color: '#ebebe8' }}
          />
          {target !== null && (
            <ReferenceLine y={target} stroke={chartColors.amber} strokeDasharray="5 4" label={{ value: '2030 target', fill: chartColors.amber, fontSize: 10, position: 'insideTopRight' }} />
          )}
          <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} dot={{ r: 2.5, fill: color, strokeWidth: 0 }} activeDot={{ r: 5 }} animationDuration={900} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
