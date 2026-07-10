import { motion, useReducedMotion } from 'framer-motion';

export interface TrafficHourStat {
  hour: number;
  entry: number;
  exit: number;
}

interface TrafficChartProps {
  stats: TrafficHourStat[];
  rangeLabel: string;
}

export function TrafficChart({ stats, rangeLabel }: TrafficChartProps) {
  const reduceMotion = useReducedMotion();
  const maxValue = Math.max(...stats.map((s) => Math.max(s.entry, s.exit)), 1);
  const totalEntry = stats.reduce((sum, s) => sum + s.entry, 0);
  const totalExit = stats.reduce((sum, s) => sum + s.exit, 0);
  const peak = stats.reduce(
    (best, s) => {
      const volume = s.entry + s.exit;
      return volume > best.volume ? { hour: s.hour, volume } : best;
    },
    { hour: 0, volume: 0 },
  );
  const hasData = totalEntry + totalExit > 0;

  return (
    <div className="traffic-chart" data-testid="traffic-chart">
      <div className="traffic-chart-head">
        <div>
          <div className="traffic-chart-kicker">Biểu đồ lưu lượng</div>
          <h3 className="traffic-chart-title">Lưu lượng theo giờ</h3>
          <p className="traffic-chart-subtitle">{rangeLabel}</p>
        </div>
        <div className="traffic-chart-signal">
          <span className="traffic-chart-signal-label">Cao điểm</span>
          <strong>{peak.volume > 0 ? `${String(peak.hour).padStart(2, '0')}:00` : '—'}</strong>
          <span>{peak.volume > 0 ? `${peak.volume} lượt` : 'Chưa có dữ liệu'}</span>
        </div>
      </div>

      <div className="traffic-chart-meta">
        <div className="traffic-legend" aria-label="Chú giải biểu đồ">
          <span className="traffic-legend-item entry">Vào</span>
          <span className="traffic-legend-item exit">Ra</span>
        </div>
        <span className="traffic-chart-meta-note">24 giờ trong ngày</span>
      </div>

      <div className="traffic-summary">
        <div className="traffic-summary-item entry">
          <span>Tổng vào</span>
          <strong>{totalEntry}</strong>
          <i aria-hidden="true" />
        </div>
        <div className="traffic-summary-item exit">
          <span>Tổng ra</span>
          <strong>{totalExit}</strong>
          <i aria-hidden="true" />
        </div>
      </div>

      {!hasData ? (
        <div className="empty-state">Chưa có dữ liệu lưu lượng trong khoảng đã chọn.</div>
      ) : (
        <div className="traffic-plot" role="img" aria-label={`Lưu lượng theo giờ từ ${rangeLabel}`}>
          <div className="traffic-y-axis" aria-hidden="true">
            <span>{maxValue}</span>
            <span>{Math.round(maxValue / 2)}</span>
            <span>0</span>
          </div>

          <div className="traffic-bars">
            <div className="traffic-grid" aria-hidden="true">
              <span />
              <span />
              <span />
            </div>

            {stats.map((s, index) => {
              const entryPct = (s.entry / maxValue) * 100;
              const exitPct = (s.exit / maxValue) * 100;
              const isPeak = peak.volume > 0 && s.hour === peak.hour;
              const hourLabel = `${String(s.hour).padStart(2, '0')}:00`;

              return (
                <div
                  key={s.hour}
                  className={`traffic-col ${isPeak ? 'is-peak' : ''}`}
                  tabIndex={0}
                  aria-label={`${hourLabel}: vào ${s.entry}, ra ${s.exit}`}
                >
                  <div className="traffic-col-tooltip" role="status">
                    <strong>{hourLabel}</strong>
                    <span><b className="entry-dot" />Vào {s.entry}</span>
                    <span><b className="exit-dot" />Ra {s.exit}</span>
                  </div>
                  <div className="traffic-col-bars">
                    <motion.div
                      className="traffic-bar entry"
                      initial={reduceMotion ? false : { height: 0, opacity: 0.35 }}
                      animate={{ height: `${entryPct}%`, opacity: 1 }}
                      transition={{ duration: 0.65, delay: reduceMotion ? 0 : index * 0.018, ease: [0.16, 1, 0.3, 1] }}
                    />
                    <motion.div
                      className="traffic-bar exit"
                      initial={reduceMotion ? false : { height: 0, opacity: 0.35 }}
                      animate={{ height: `${exitPct}%`, opacity: 1 }}
                      transition={{ duration: 0.65, delay: reduceMotion ? 0 : index * 0.018 + 0.05, ease: [0.16, 1, 0.3, 1] }}
                    />
                  </div>
                  <div className="traffic-col-label">{String(s.hour).padStart(2, '0')}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
