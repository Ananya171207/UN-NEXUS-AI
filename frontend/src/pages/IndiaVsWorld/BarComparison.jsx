import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { chartColors } from '../../styles/chartTheme';
import { formatValue } from './utils';

// Bars show the selected countries' reported values. The dashed line marks the baseline.
export default function BarComparison({ indicator, rows, baselineValue, baselineName }) {
  const height = Math.max(150, rows.length * 42 + 48);

  return (
    <div
      style={{ width: '100%', height }}
      role="img"
      aria-label={`${indicator.label}: live comparison across selected countries`}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical" margin={{ top: 8, right: 76, left: 4, bottom: 0 }}>
          <CartesianGrid stroke={chartColors.grid} strokeDasharray="3 3" horizontal={false} />
          <XAxis
            type="number"
            stroke={chartColors.axis}
            tick={{ fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: chartColors.grid }}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={112}
            stroke={chartColors.axis}
            tick={{ fontSize: 12 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            cursor={{ fill: 'rgba(255,255,255,0.04)' }}
            formatter={(value) => [formatValue(indicator, value), indicator.label]}
            labelFormatter={(label, payload) => {
              const year = payload?.[0]?.payload?.year;
              return year ? `${label} · ${year}` : label;
            }}
            contentStyle={{
              background: chartColors.tooltipBg,
              border: `1px solid ${chartColors.tooltipBorder}`,
              borderRadius: 4,
              fontSize: 12,
            }}
            labelStyle={{ color: chartColors.axis }}
            itemStyle={{ color: '#ebebe8' }}
          />
          {Number.isFinite(baselineValue) && (
            <ReferenceLine
              x={baselineValue}
              stroke={chartColors.amber}
              strokeDasharray="5 4"
              label={{
                value: `${baselineName} baseline`,
                fill: chartColors.amber,
                fontSize: 10,
                position: 'top',
              }}
            />
          )}
          <Bar dataKey="value" radius={[0, 3, 3, 0]} animationDuration={700}>
            {rows.map((row) => (
              <Cell
                key={row.code}
                fill={row.isBaseline ? chartColors.accent : chartColors.teal}
                fillOpacity={row.isBaseline ? 1 : 0.68}
              />
            ))}
            <LabelList dataKey="label" position="right" fill={chartColors.axis} fontSize={11} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
