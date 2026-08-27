import { useEffect, useState } from "react";
import { api } from "../api/api";

export default function Analytics() {
  const [range, setRange] = useState("30");
  const [summary, setSummary] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [categories, setCategories] = useState([]);
  const [topEvents, setTopEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadData = async (selectedRange) => {
    setLoading(true);
    try {
      const [sum, time, cats, top] = await Promise.all([
        api.getAnalyticsSummary(selectedRange),
        api.getRegistrationsOverTime(selectedRange),
        api.getCategoryDistribution(),
        api.getTopEvents(5),
      ]);
      setSummary(sum);
      setTimeline(time);
      setCategories(cats);
      setTopEvents(top);
    } catch (err) {
      console.error("Analytics fetch error", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(range);
  }, [range]);

  const maxTimelineCount = Math.max(1, ...timeline.map((t) => t.registrations));
  const maxCategoryReg = Math.max(1, ...categories.map((c) => c.registrations));

  return (
    <div>
      <div className="page-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <h1>📈 Platform Analytics & Telemetry</h1>
            <p>Real-time database intelligence: registrations over time, capacity utilization and attendance metrics</p>
          </div>

          {/* Date Range Selector */}
          <div className="range-selector-row">
            <span>Time Horizon:</span>
            <div className="range-btn-group">
              {["7", "30", "90", "all"].map((r) => (
                <button
                  key={r}
                  className={`range-btn ${range === r ? "active" : ""}`}
                  onClick={() => setRange(r)}
                >
                  {r === "all" ? "All Time" : `${r} Days`}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {loading && !summary ? (
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Computing analytics from live database records...</p>
        </div>
      ) : summary ? (
        <>
          {/* Key Rates & KPIs */}
          <div className="stat-row">
            <div className="stat-card">
              <div className="stat-value">{summary.total_registrations}</div>
              <div className="stat-label">Total Registrations</div>
            </div>
            <div className="stat-card" style={{ background: "#059669" }}>
              <div className="stat-value">{summary.attended_count}</div>
              <div className="stat-label">Verified Check-Ins</div>
            </div>
            <div className="stat-card" style={{ background: "#4338ca" }}>
              <div className="stat-value">{summary.attendance_rate}%</div>
              <div className="stat-label">Attendance Rate</div>
            </div>
            <div className="stat-card" style={{ background: "#d97706" }}>
              <div className="stat-value">{summary.capacity_utilization}%</div>
              <div className="stat-label">Capacity Utilization</div>
            </div>
            <div className="stat-card" style={{ background: "#e11d48" }}>
              <div className="stat-value">{summary.cancellation_rate}%</div>
              <div className="stat-label">Cancellation Rate</div>
            </div>
          </div>

          {/* Charts Grid */}
          <div className="analytics-grid">
            {/* Registrations Over Time (Bar/Area Timeline) */}
            <div className="card analytics-chart-card">
              <div className="chart-header">
                <h3>📅 Registrations Over Time</h3>
                <span className="chart-subtitle">Daily registration and verified check-in volume</span>
              </div>

              {timeline.length === 0 ? (
                <p className="empty-state">No registration entries recorded in this time range.</p>
              ) : (
                <div className="timeline-chart-wrap">
                  <div className="timeline-bars-container">
                    {timeline.map((item, idx) => {
                      const heightPct = Math.round((item.registrations / maxTimelineCount) * 100);
                      return (
                        <div key={idx} className="timeline-bar-column">
                          <span className="bar-tooltip">
                            {item.date}: {item.registrations} registered, {item.attended} attended
                          </span>
                          <div className="bar-track">
                            <div
                              className="bar-fill"
                              style={{ height: `${Math.max(8, heightPct)}%` }}
                            ></div>
                          </div>
                          <span className="bar-date-label">{item.date.slice(5)}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* Attendance Status Breakdown */}
            <div className="card analytics-chart-card">
              <div className="chart-header">
                <h3>🎯 Attendance & Status Breakdown</h3>
                <span className="chart-subtitle">Distribution of attendee outcomes across events</span>
              </div>

              <div className="breakdown-list">
                <div className="breakdown-item">
                  <div className="breakdown-label-row">
                    <span>Attended (Checked In)</span>
                    <strong>{summary.attended_count}</strong>
                  </div>
                  <div className="progress-track">
                    <div
                      className="progress-fill"
                      style={{
                        width: `${summary.total_registrations ? (summary.attended_count / summary.total_registrations) * 100 : 0}%`,
                        background: "#059669",
                      }}
                    ></div>
                  </div>
                </div>

                <div className="breakdown-item">
                  <div className="breakdown-label-row">
                    <span>Active / Registered</span>
                    <strong>{summary.active_registrations}</strong>
                  </div>
                  <div className="progress-track">
                    <div
                      className="progress-fill"
                      style={{
                        width: `${summary.total_registrations ? (summary.active_registrations / summary.total_registrations) * 100 : 0}%`,
                        background: "#4338ca",
                      }}
                    ></div>
                  </div>
                </div>

                <div className="breakdown-item">
                  <div className="breakdown-label-row">
                    <span>Waitlisted in Queue</span>
                    <strong>{summary.waitlisted_count}</strong>
                  </div>
                  <div className="progress-track">
                    <div
                      className="progress-fill"
                      style={{
                        width: `${summary.total_registrations ? (summary.waitlisted_count / summary.total_registrations) * 100 : 0}%`,
                        background: "#d97706",
                      }}
                    ></div>
                  </div>
                </div>

                <div className="breakdown-item">
                  <div className="breakdown-label-row">
                    <span>Absent / No-Show</span>
                    <strong>{summary.absent_count}</strong>
                  </div>
                  <div className="progress-track">
                    <div
                      className="progress-fill"
                      style={{
                        width: `${summary.total_registrations ? (summary.absent_count / summary.total_registrations) * 100 : 0}%`,
                        background: "#64748b",
                      }}
                    ></div>
                  </div>
                </div>

                <div className="breakdown-item">
                  <div className="breakdown-label-row">
                    <span>Cancelled</span>
                    <strong>{summary.cancelled_count}</strong>
                  </div>
                  <div className="progress-track">
                    <div
                      className="progress-fill"
                      style={{
                        width: `${summary.total_registrations ? (summary.cancelled_count / summary.total_registrations) * 100 : 0}%`,
                        background: "#ef4444",
                      }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Secondary Analytics Row */}
          <div className="analytics-grid" style={{ marginTop: "1.5rem" }}>
            {/* Category Distribution */}
            <div className="card">
              <div className="chart-header">
                <h3>🏷️ Popularity by Event Category</h3>
                <span className="chart-subtitle">Event frequency and registration engagement</span>
              </div>

              {categories.length === 0 ? (
                <p className="empty-state">No category data available.</p>
              ) : (
                <div className="category-rankings-list">
                  {categories.map((cat, idx) => {
                    const pct = Math.round((cat.registrations / maxCategoryReg) * 100);
                    return (
                      <div key={idx} className="category-rank-item">
                        <div className="cat-rank-info">
                          <strong>{cat.category}</strong>
                          <span>{cat.events} events · {cat.registrations} registrations</span>
                        </div>
                        <div className="progress-track" style={{ height: "8px" }}>
                          <div className="progress-fill" style={{ width: `${Math.max(5, pct)}%` }}></div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Top Performing Events */}
            <div className="card">
              <div className="chart-header">
                <h3>🏆 Top Performing Events</h3>
                <span className="chart-subtitle">Highest engagement and capacity utilization</span>
              </div>

              {topEvents.length === 0 ? (
                <p className="empty-state">No event records available.</p>
              ) : (
                <div className="top-events-list">
                  {topEvents.map((e, idx) => (
                    <div key={e.id} className="top-event-item">
                      <div className="top-event-rank">#{idx + 1}</div>
                      <div className="top-event-meta">
                        <strong>{e.name}</strong>
                        <span>{e.category} · {e.date}</span>
                      </div>
                      <div className="top-event-stats">
                        <div className="stat-pill">
                          <strong>{e.registered}</strong> Reg
                        </div>
                        <div className="stat-pill" style={{ color: "#059669" }}>
                          <strong>{e.attended}</strong> Attended
                        </div>
                        <div className="stat-pill" style={{ color: "#4338ca" }}>
                          <strong>{e.utilization}%</strong> Filled
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
