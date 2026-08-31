import { useEffect, useState } from "react";
import { api } from "../api/api";

export default function Analytics() {
  const [range, setRange] = useState("30");
  const [summary, setSummary] = useState(null);
  const [overview, setOverview] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [categories, setCategories] = useState([]);
  const [topEvents, setTopEvents] = useState([]);
  const [resources, setResources] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [budgetAnalytics, setBudgetAnalytics] = useState(null);
  const [vendorAnalytics, setVendorAnalytics] = useState(null);
  const [allEvents, setAllEvents] = useState([]);
  const [selectedCompare, setSelectedCompare] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadData = async (selectedRange) => {
    setLoading(true);
    setError(null);
    try {
      const results = await Promise.allSettled([
        api.getAnalyticsSummary(selectedRange),
        api.getRegistrationsOverTime(selectedRange),
        api.getCategoryDistribution(),
        api.getTopEvents(5),
        api.getAnalyticsOverview(),
        api.getResourceAnalytics(),
        api.getForecast(),
        api.getBudgetAnalytics(),
        api.getVendorAnalytics(),
        api.getMyEvents().catch(() => api.getEvents()),
      ]);

      const pick = (idx) => (results[idx].status === "fulfilled" ? results[idx].value : null);
      const failures = results.filter((r) => r.status === "rejected");

      const sum = pick(0);
      const time = pick(1) || [];
      const cats = pick(2) || [];
      const top = pick(3) || [];
      const ov = pick(4);
      const res = pick(5);
      const fc = pick(6);
      const bud = pick(7);
      const vend = pick(8);
      const evList = pick(9) || [];

      if (!sum) {
        const firstErr = failures[0]?.reason;
        setError(firstErr?.message || "Unable to load analytics. Please ensure the backend server is running.");
        setSummary(null);
        return;
      }

      setSummary(sum);
      setTimeline(Array.isArray(time) ? time : []);
      setCategories(Array.isArray(cats) ? cats : []);
      setTopEvents(Array.isArray(top) ? top : []);
      setOverview(ov);
      setResources(res);
      setForecast(fc);
      setBudgetAnalytics(bud);
      setVendorAnalytics(vend);
      setAllEvents(Array.isArray(evList) ? evList : []);

      if (failures.length > 0) {
        setError("Some analytics sections could not be loaded. Showing available data.");
      }

      const events = Array.isArray(evList) ? evList : [];
      const defaultIds = events.slice(0, 3).map((e) => e.id);
      setSelectedCompare(defaultIds);
      if (defaultIds.length > 0) {
        try {
          setComparison(await api.getEventComparison(defaultIds));
        } catch (err) {
          console.error("Event comparison fetch error", err);
        }
      }
    } catch (err) {
      console.error("Analytics fetch error", err);
      setError(err.message || "Failed to load analytics.");
      setSummary(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(range); }, [range]);

  const handleCompare = async () => {
    if (selectedCompare.length < 1) return;
    try {
      setComparison(await api.getEventComparison(selectedCompare));
    } catch (err) {
      console.error(err);
    }
  };

  const toggleCompareEvent = (id) => {
    setSelectedCompare((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : prev.length < 4 ? [...prev, id] : prev
    );
  };

  const maxTimelineCount = Math.max(1, ...timeline.map((t) => t.registrations || 0));
  const _maxCategoryReg = Math.max(1, ...categories.map((c) => c.registrations || 0));
  const maxTopReg = Math.max(1, ...topEvents.map((e) => e.registered || 0));
  const maxCompareReg = Math.max(1, ...(comparison?.events || []).map((e) => e.registrations || 0));
  const categoryTotal = categories.reduce((s, c) => s + (c.registrations || 0), 0) || 1;
  const kpis = overview?.kpis || {};
  const recs = forecast?.forecast?.recommendations;
  const forecastData = forecast?.forecast;

  return (
    <div>
      <div className="page-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <h1>📈 EventSphere Analytics Dashboard</h1>
            <p>KPIs, registrations, budget utilization, resource optimization and event comparison</p>
          </div>
          <div className="range-selector-row">
            <span>Time Horizon:</span>
            <div className="range-btn-group">
              {["7", "30", "90", "all"].map((r) => (
                <button key={r} className={`range-btn ${range === r ? "active" : ""}`} onClick={() => setRange(r)}>
                  {r === "all" ? "All Time" : `${r} Days`}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className={`alert alert-${summary ? "warning" : "error"}`} style={{ marginBottom: "1rem" }}>
          {error}
          {!summary && (
            <button className="btn btn-sm btn-outline" style={{ marginLeft: "1rem" }} onClick={() => loadData(range)}>
              Retry
            </button>
          )}
        </div>
      )}

      {loading && !summary ? (
        <div className="loading-state"><div className="spinner"></div><p>Computing analytics...</p></div>
      ) : summary ? (
        <>
          <div className="stat-row">
            <div className="stat-card"><div className="stat-value">{kpis.total_events || summary.total_events}</div><div className="stat-label">Total Events</div></div>
            <div className="stat-card" style={{ background: "#4338ca" }}><div className="stat-value">{kpis.total_registrations || summary.total_registrations}</div><div className="stat-label">Registrations</div></div>
            <div className="stat-card" style={{ background: "#059669" }}><div className="stat-value">{kpis.total_attendance || summary.attended_count}</div><div className="stat-label">Checked In</div></div>
            <div className="stat-card" style={{ background: "#d97706" }}><div className="stat-value">₹{(kpis.total_budget || summary.total_budget || 0).toLocaleString()}</div><div className="stat-label">Total Budget</div></div>
            <div className="stat-card" style={{ background: "#dc2626" }}><div className="stat-value">₹{(kpis.total_expenses || summary.total_expenses || 0).toLocaleString()}</div><div className="stat-label">Expenses</div></div>
          </div>

          <div className="stat-row">
            <div className="stat-card"><div className="stat-value">₹{(kpis.remaining_budget || summary.remaining_budget || 0).toLocaleString()}</div><div className="stat-label">Remaining Budget</div></div>
            <div className="stat-card" style={{ background: "#7c3aed" }}><div className="stat-value">{kpis.budget_utilization || 0}%</div><div className="stat-label">Budget Utilization</div></div>
            <div className="stat-card" style={{ background: "#0891b2" }}><div className="stat-value">{kpis.resource_utilization || resources?.resource_utilization || 0}%</div><div className="stat-label">Resource Utilization</div></div>
            <div className="stat-card" style={{ background: "#ca8a04" }}><div className="stat-value">{kpis.avg_vendor_rating || 0} ⭐</div><div className="stat-label">Avg Vendor Rating</div></div>
            <div className="stat-card" style={{ background: "#e11d48" }}><div className="stat-value">{kpis.attendance_rate || summary.attendance_rate}%</div><div className="stat-label">Attendance Rate</div></div>
          </div>

          <div className="analytics-grid">
            {/* Registration bar chart - top events */}
            <div className="card analytics-chart-card">
              <div className="chart-header">
                <h3>📊 Registrations by Event</h3>
                <span className="chart-subtitle">Compare registration volume across top events</span>
              </div>
              {topEvents.length === 0 ? <p className="empty-state">No events yet.</p> : (
                <div>
                  {topEvents.map((e) => (
                    <div key={e.id} style={{ marginBottom: "0.75rem" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: "0.25rem" }}>
                        <span>{e.name}</span>
                        <strong>{e.registered}</strong>
                      </div>
                      <div className="progress-track" style={{ height: "12px" }}>
                        <div className="progress-fill" style={{ width: `${Math.round((e.registered / maxTopReg) * 100)}%`, background: "#4338ca" }} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Category pie-style distribution */}
            <div className="card analytics-chart-card">
              <div className="chart-header">
                <h3>🥧 Registration by Category</h3>
                <span className="chart-subtitle">Share of registrations per event category</span>
              </div>
              {categories.length === 0 ? <p className="empty-state">No category data.</p> : (
                <div>
                  {categories.map((cat, i) => {
                    const pct = Math.round((cat.registrations / categoryTotal) * 100);
                    const colors = ["#4338ca", "#059669", "#d97706", "#e11d48", "#0891b2", "#7c3aed"];
                    return (
                      <div key={cat.category} style={{ marginBottom: "0.75rem" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem" }}>
                          <span><span style={{ color: colors[i % colors.length], fontWeight: "bold" }}>●</span> {cat.category}</span>
                          <span>{pct}% ({cat.registrations})</span>
                        </div>
                        <div className="progress-track" style={{ height: "10px" }}>
                          <div className="progress-fill" style={{ width: `${pct}%`, background: colors[i % colors.length] }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Line-style registration trend */}
          <div className="card" style={{ marginTop: "1.5rem" }}>
            <div className="chart-header">
              <h3>📅 Registration Trend Over Time</h3>
              <span className="chart-subtitle">Daily registrations with check-in overlay</span>
            </div>
            {timeline.length === 0 ? <p className="empty-state">No data in range.</p> : (
              <div className="timeline-chart-wrap">
                <div className="timeline-bars-container">
                  {timeline.map((item, idx) => {
                    const regH = Math.round(((item.registrations || 0) / maxTimelineCount) * 100);
                    const attH = Math.round(((item.attended || 0) / maxTimelineCount) * 100);
                    return (
                      <div key={idx} className="timeline-bar-column">
                        <span className="bar-tooltip">{item.date}: {item.registrations || 0} reg, {item.attended || 0} attended</span>
                        <div className="bar-track" style={{ position: "relative" }}>
                          <div className="bar-fill" style={{ height: `${Math.max(8, regH)}%`, background: "#4338ca", opacity: 0.7 }} />
                          <div style={{ position: "absolute", bottom: 0, left: "25%", width: "50%", height: `${Math.max(4, attH)}%`, background: "#059669", borderRadius: "2px 2px 0 0" }} />
                        </div>
                        <span className="bar-date-label">{item.date?.slice(5)}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Event Comparison with bar chart */}
          <div className="card" style={{ marginTop: "1.5rem" }}>
            <div className="chart-header">
              <h3>⚖️ Event Comparison</h3>
              <span className="chart-subtitle">Select up to 4 events</span>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginBottom: "1rem" }}>
              {allEvents.map((ev) => (
                <button key={ev.id} className={`btn btn-sm ${selectedCompare.includes(ev.id) ? "btn-primary" : "btn-outline"}`} onClick={() => toggleCompareEvent(ev.id)}>
                  {ev.name}
                </button>
              ))}
            </div>
            <button className="btn btn-primary btn-sm" onClick={handleCompare} style={{ marginBottom: "1rem" }}>Compare Selected</button>

            {comparison?.events?.length > 0 && (
              <>
                <div style={{ marginBottom: "1.5rem" }}>
                  <strong style={{ fontSize: "0.9rem" }}>Registration Comparison</strong>
                  {comparison.events.map((e) => (
                    <div key={e.event_id} style={{ marginTop: "0.5rem" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem" }}>
                        <span>{e.name}</span><span>{e.registrations} reg · {e.attendance_rate}% attendance</span>
                      </div>
                      <div className="progress-track" style={{ height: "10px" }}>
                        <div className="progress-fill" style={{ width: `${Math.round((e.registrations / maxCompareReg) * 100)}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr><th>Metric</th>{comparison.events.map((e) => <th key={e.event_id}>{e.name}</th>)}</tr>
                    </thead>
                    <tbody>
                      <tr><td>Registrations</td>{comparison.events.map((e) => <td key={e.event_id}>{e.registrations}</td>)}</tr>
                      <tr><td>Attendance Rate</td>{comparison.events.map((e) => <td key={e.event_id}>{e.attendance_rate}%</td>)}</tr>
                      <tr><td>Budget</td>{comparison.events.map((e) => <td key={e.event_id}>₹{Number(e.budget).toLocaleString()}</td>)}</tr>
                      <tr><td>Expenses</td>{comparison.events.map((e) => <td key={e.event_id}>₹{Number(e.expenses).toLocaleString()}</td>)}</tr>
                      <tr><td>Remaining</td>{comparison.events.map((e) => <td key={e.event_id}>₹{Number(e.remaining).toLocaleString()}</td>)}</tr>
                      <tr><td>Vendor Rating</td>{comparison.events.map((e) => <td key={e.event_id}>{e.vendor_rating} ⭐</td>)}</tr>
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </div>

          {/* Budget Analytics */}
          {budgetAnalytics?.events?.length > 0 && (
            <div className="card" style={{ marginTop: "1.5rem" }}>
              <div className="chart-header">
                <h3>💰 Budget Tracking by Event</h3>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr><th>Event</th><th>Budget</th><th>Expenses</th><th>Remaining</th><th>Utilization</th></tr>
                  </thead>
                  <tbody>
                    {budgetAnalytics.events.map((e) => {
                      const util = e.total_budget ? Math.round((e.total_expenses / e.total_budget) * 100) : 0;
                      return (
                        <tr key={e.id}>
                          <td><strong>{e.name}</strong></td>
                          <td>₹{Number(e.total_budget).toLocaleString()}</td>
                          <td>₹{Number(e.total_expenses).toLocaleString()}</td>
                          <td>₹{Number((e.total_budget || 0) - (e.total_expenses || 0)).toLocaleString()}</td>
                          <td>
                            <div className="progress-track" style={{ height: "8px", width: "80px", display: "inline-block", verticalAlign: "middle", marginRight: "0.5rem" }}>
                              <div className="progress-fill" style={{ width: `${Math.min(util, 100)}%`, background: util > 90 ? "#dc2626" : "#4338ca" }} />
                            </div>
                            {util}%
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="analytics-grid" style={{ marginTop: "1.5rem" }}>
            {/* Forecast with planning recommendations */}
            <div className="card">
              <div className="chart-header"><h3>🔮 Attendance Forecast & Planning</h3></div>
              {forecastData ? (
                <div>
                  <div className="stat-row" style={{ marginBottom: "1rem" }}>
                    <div className="stat-card"><div className="stat-value">{forecastData.predicted_attendees ?? 0}</div><div className="stat-label">Predicted Attendees</div></div>
                    <div className="stat-card" style={{ background: "#4338ca" }}><div className="stat-value">{forecastData.confidence?.toUpperCase() || "N/A"}</div><div className="stat-label">Confidence</div></div>
                  </div>
                  {recs && (
                    <div style={{ background: "#f0f9ff", padding: "1rem", borderRadius: "8px", marginBottom: "1rem" }}>
                      <strong>Planning Recommendations:</strong>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", marginTop: "0.5rem", fontSize: "0.9rem" }}>
                        <div>🏛️ Venue capacity: <strong>{recs.venue_capacity}</strong></div>
                        <div>🪑 Chairs needed: <strong>{recs.chairs_needed}</strong></div>
                        <div>🍽️ Food servings: <strong>{recs.food_servings}</strong></div>
                        <div>🙋 Volunteers: <strong>{recs.volunteers}</strong></div>
                        <div>🎫 Registration counters: <strong>{recs.registration_counters}</strong></div>
                      </div>
                    </div>
                  )}
                  {(forecast.history || []).map((h) => (
                    <div key={h.id} style={{ display: "flex", justifyContent: "space-between", padding: "0.3rem 0", fontSize: "0.9rem" }}>
                      <span>{h.name}</span><span>{h.registrations} registrations</span>
                    </div>
                  ))}
                </div>
              ) : <p className="empty-state">Not enough data.</p>}
            </div>

            {/* Resource utilization */}
            <div className="card">
              <div className="chart-header"><h3>📦 Resource Utilization</h3></div>
              {resources ? (
                <div>
                  <div className="stat-row" style={{ marginBottom: "1rem" }}>
                    <div className="stat-card"><div className="stat-value">{resources.total_resources}</div><div className="stat-label">Total Units</div></div>
                    <div className="stat-card" style={{ background: "#4338ca" }}><div className="stat-value">{resources.allocated_resources}</div><div className="stat-label">Allocated</div></div>
                    <div className="stat-card" style={{ background: "#059669" }}><div className="stat-value">{resources.available_resources}</div><div className="stat-label">Available</div></div>
                    <div className="stat-card" style={{ background: "#d97706" }}><div className="stat-value">{resources.resource_utilization}%</div><div className="stat-label">Utilization</div></div>
                  </div>
                  {[...(resources.reuse_suggestions || []), ...(resources.recommendations || [])].map((r, i) => (
                    <div key={i} style={{ padding: "0.5rem", background: "#f0fdf4", borderRadius: "4px", marginTop: "0.5rem", fontSize: "0.85rem" }}>♻️ {r.message}</div>
                  ))}
                </div>
              ) : <p className="empty-state">No resource data.</p>}
            </div>
          </div>

          {/* Vendor Performance Analytics */}
          {vendorAnalytics?.vendor_comparison?.length > 0 && (
            <div className="card" style={{ marginTop: "1.5rem" }}>
              <div className="chart-header"><h3>🤝 Vendor Performance Rankings</h3></div>
              <div className="stat-row" style={{ marginBottom: "1rem" }}>
                <div className="stat-card"><div className="stat-value">{vendorAnalytics.avg_overall_rating}</div><div className="stat-label">Avg Overall</div></div>
                <div className="stat-card" style={{ background: "#4338ca" }}><div className="stat-value">{vendorAnalytics.avg_quality}</div><div className="stat-label">Avg Quality</div></div>
                <div className="stat-card" style={{ background: "#059669" }}><div className="stat-value">{vendorAnalytics.avg_timeliness}</div><div className="stat-label">Avg Timeliness</div></div>
                <div className="stat-card" style={{ background: "#d97706" }}><div className="stat-value">{vendorAnalytics.avg_cost}</div><div className="stat-label">Avg Cost</div></div>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr><th>Vendor</th><th>Quality</th><th>Timeliness</th><th>Cost</th><th>Communication</th><th>Overall</th><th>Ratings</th></tr>
                  </thead>
                  <tbody>
                    {vendorAnalytics.vendor_comparison.map((v) => (
                      <tr key={v.id}>
                        <td><strong>{v.name}</strong></td>
                        <td>{v.avg_quality || "—"} ⭐</td>
                        <td>{v.avg_timeliness || "—"} ⭐</td>
                        <td>{v.avg_cost || "—"} ⭐</td>
                        <td>{v.avg_communication || "—"} ⭐</td>
                        <td><strong>{v.avg_overall || "—"} ⭐</strong></td>
                        <td>{v.rating_count || 0}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      ) : !loading ? (
        <div className="card" style={{ textAlign: "center", padding: "3rem" }}>
          <p className="empty-state">No analytics data available yet.</p>
          <button className="btn btn-primary" onClick={() => loadData(range)}>Reload Analytics</button>
        </div>
      ) : null}
    </div>
  );
}
