import { useState } from 'react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import type { ChartConfig } from '../../types';
import { getChartColors } from '../../utils/helpers';

interface ChartRendererProps {
  config: ChartConfig;
}

const CHART_TYPES = ['bar', 'line', 'pie', 'scatter', 'table'] as const;

export function ChartRenderer({ config }: ChartRendererProps) {
  const [chartType, setChartType] = useState<string>(config.type);
  const { data, options } = config;
  const { xKey, yKey, title, yLabel, nameKey, valueKey } = options;

  if (!data || data.length === 0) return null;

  const colors = options.colors || getChartColors(10);
  const keys = Object.keys(data[0]);
  const effectiveXKey = xKey || nameKey || keys[0];
  const effectiveYKeys: string[] = yKey
    ? Array.isArray(yKey) ? yKey : [yKey]
    : valueKey
    ? [valueKey]
    : keys.filter((k) => k !== effectiveXKey && typeof data[0][k] === 'number');

  const applicableTypes = ['bar', 'line', 'table'];
  if (effectiveYKeys.length === 1 && data.length <= 12) applicableTypes.push('pie');
  if (effectiveYKeys.length >= 2) applicableTypes.push('scatter');

  const renderChart = () => {
    switch (chartType) {
      case 'bar':
        return (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                dataKey={effectiveXKey}
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                axisLine={{ stroke: '#475569' }}
              />
              <YAxis
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                axisLine={{ stroke: '#475569' }}
                label={yLabel ? { value: yLabel, angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 11 } : undefined}
              />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '0.5rem', fontSize: '0.8125rem' }}
                labelStyle={{ color: '#f1f5f9' }}
                itemStyle={{ color: '#94a3b8' }}
              />
              {effectiveYKeys.length > 1 && <Legend wrapperStyle={{ fontSize: '0.75rem' }} />}
              {effectiveYKeys.map((key, i) => (
                <Bar key={key} dataKey={key} fill={colors[i]} radius={[4, 4, 0, 0]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        );

      case 'line':
        return (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                dataKey={effectiveXKey}
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                axisLine={{ stroke: '#475569' }}
              />
              <YAxis
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                axisLine={{ stroke: '#475569' }}
              />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '0.5rem', fontSize: '0.8125rem' }}
                labelStyle={{ color: '#f1f5f9' }}
              />
              {effectiveYKeys.length > 1 && <Legend wrapperStyle={{ fontSize: '0.75rem' }} />}
              {effectiveYKeys.map((key, i) => (
                <Line key={key} type="monotone" dataKey={key} stroke={colors[i]} strokeWidth={2} dot={{ r: 3, fill: colors[i] }} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        );

      case 'pie':
        const pieKey = effectiveYKeys[0];
        return (
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={100}
                dataKey={pieKey}
                nameKey={effectiveXKey}
                paddingAngle={2}
                label={({ name, percent }: any) => `${name} (${(percent * 100).toFixed(0)}%)`}
                labelLine={{ stroke: '#64748b' }}
              >
                {data.map((_: any, i: number) => (
                  <Cell key={i} fill={colors[i]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '0.5rem', fontSize: '0.8125rem' }}
              />
            </PieChart>
          </ResponsiveContainer>
        );

      case 'scatter':
        const scatterXKey = effectiveYKeys[0] || effectiveXKey;
        const scatterYKey = effectiveYKeys[1] || effectiveYKeys[0];
        return (
          <ResponsiveContainer width="100%" height={280}>
            <ScatterChart margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                type="number"
                dataKey={scatterXKey}
                name={scatterXKey}
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                axisLine={{ stroke: '#475569' }}
              />
              <YAxis
                type="number"
                dataKey={scatterYKey}
                name={scatterYKey}
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                axisLine={{ stroke: '#475569' }}
              />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '0.5rem', fontSize: '0.8125rem' }}
                cursor={{ strokeDasharray: '3 3' }}
              />
              <Scatter data={data} fill={colors[0]} />
            </ScatterChart>
          </ResponsiveContainer>
        );

      case 'table':
        return (
          <div className="data-table-wrapper" style={{ maxHeight: '16rem' }}>
            <table className="data-table">
              <thead>
                <tr>
                  {keys.map((k) => (
                    <th key={k}>{k}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.slice(0, 50).map((row: any, i: number) => (
                  <tr key={i}>
                    {keys.map((k) => (
                      <td key={k}>
                        {row[k] != null
                          ? typeof row[k] === 'number'
                            ? row[k].toLocaleString(undefined, { maximumFractionDigits: 2 })
                            : String(row[k])
                          : '—'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="chart-container">
      {title && <div className="chart-title">{title}</div>}
      <div className="chart-type-selector">
        {CHART_TYPES.filter((t) => applicableTypes.includes(t)).map((t) => (
          <button
            key={t}
            className={`chart-type-btn ${chartType === t ? 'active' : ''}`}
            onClick={() => setChartType(t)}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      {renderChart()}
    </div>
  );
}
