import { Legend, PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer, Tooltip } from 'recharts';
import { chartColors } from '../../styles/chartTheme';

// "Profile" view: every indicator rescaled to 0-100 so very different things can be drawn together.
export default function ProfileRadar({ data, otherName }) {
  return (
    <div className="iw-radar" role="img" aria-label={`Profile of India${otherName ? ` and ${otherName}` : ''} across seven indicators (sample data, 0 to 100)`}>
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} outerRadius="70%">
          <PolarGrid stroke={chartColors.grid} />
          <PolarAngleAxis dataKey="axis" tick={{ fill: chartColors.axis, fontSize: 11 }} />
          <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
          <Tooltip contentStyle={{ background: chartColors.tooltipBg, border: `1px solid ${chartColors.tooltipBorder}`, borderRadius: 4, fontSize: 12 }} itemStyle={{ color: '#ebebe8' }} />
          <Radar name="Sample median" dataKey="median" stroke={chartColors.amber} fill={chartColors.amber} fillOpacity={0.06} strokeDasharray="4 3" />
          {otherName && <Radar name={otherName} dataKey="other" stroke={chartColors.teal} fill={chartColors.teal} fillOpacity={0.16} />}
          <Radar name="India" dataKey="india" stroke={chartColors.accent} fill={chartColors.accent} fillOpacity={0.22} strokeWidth={2} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
