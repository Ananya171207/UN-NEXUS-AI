import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { chartColors } from '../../styles/chartTheme';

// Reusable single-series trend chart.
// `data` is an array like [{ year: '2020', value: 55 }, ...]
export default function TrendChart({ data, unit, color = chartColors.accent, height = 240 }) {
  const gradientId = `trend-${color.replace('#', '')}`;

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.22} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={chartColors.grid} strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="year"
            stroke={chartColors.axis}
            tick={{ fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: chartColors.grid }}
          />
          <YAxis stroke={chartColors.axis} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
          <Tooltip
            formatter={(value) => [`${value} ${unit || ''}`.trim(), 'Value']}
            contentStyle={{
              background: chartColors.tooltipBg,
              border: `1px solid ${chartColors.tooltipBorder}`,
              borderRadius: 4,
              fontSize: 12,
            }}
            labelStyle={{ color: chartColors.axis }}
            itemStyle={{ color: '#ebebe8' }}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            fill={`url(#${gradientId})`}
            dot={{ r: 3, fill: color, strokeWidth: 0 }}
            activeDot={{ r: 6 }}
            animationDuration={1100}
            animationEasing="ease-out"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
