import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/api";
import BudgetManagement from "../components/BudgetManagement";
import ExpenseTracking from "../components/ExpenseTracking";
import SponsorshipManagement from "../components/SponsorshipManagement";
import ApprovalWorkflow from "../components/ApprovalWorkflow";

export default function FinanceDashboard() {
  const [events, setEvents] = useState([]);
  const [selectedEventId, setSelectedEventId] = useState(null);
  const [pendingApprovals, setPendingApprovals] = useState(0);
  const [financials, setFinancials] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (selectedEventId) loadFinancials(selectedEventId);
  }, [selectedEventId]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [evList, pending] = await Promise.all([
        api.getMyEvents(),
        api.getPendingApprovalsCount().catch(() => ({ pending_count: 0 })),
      ]);
      setEvents(evList);
      setPendingApprovals(pending.pending_count || 0);
      if (evList.length > 0) {
        setSelectedEventId((prev) => prev || evList[0].id);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadFinancials = async (eventId) => {
    try {
      const [budget, expenses, sponsors] = await Promise.all([
        api.getBudgetSummary(eventId).catch(() => null),
        api.getExpensesSummary(eventId).catch(() => null),
        api.getSponsorshipSummary(eventId).catch(() => null),
      ]);
      setFinancials({ budget, expenses, sponsors });
    } catch (err) {
      console.error(err);
    }
  };

  const selectedEvent = events.find((e) => e.id === selectedEventId);
  const budget = financials?.budget;
  const expenses = financials?.expenses;
  const sponsors = financials?.sponsors;

  if (loading) {
    return (
      <div className="loading-state">
        <div className="spinner"></div>
        <p>Loading financial dashboard...</p>
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div>
        <div className="page-header">
          <h1>💼 Finance & Budget Dashboard</h1>
          <p>Manage budgets, expenses, and sponsorships for your events</p>
        </div>
        <div className="card">
          <div className="empty-state">
            <p>You haven't created any events yet.</p>
            <Link to="/events" className="btn btn-primary" style={{ display: "inline-block", marginTop: "1rem" }}>
              Create Your First Event
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <h1>💼 Finance & Budget Dashboard</h1>
            <p>Manage budgets, track expenses, handle sponsorships, and approve requests</p>
          </div>
          {pendingApprovals > 0 && (
            <button
              className="btn btn-outline"
              onClick={() => setActiveTab("approvals")}
              style={{ background: "#fef3c7", borderColor: "#fcd34d" }}
            >
              ✋ {pendingApprovals} Pending Approval{pendingApprovals > 1 ? "s" : ""}
            </button>
          )}
        </div>
      </div>

      <div className="card" style={{ marginBottom: "2rem" }}>
        <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: "bold" }}>Select Event:</label>
        <select
          value={selectedEventId || ""}
          onChange={(e) => setSelectedEventId(parseInt(e.target.value))}
          style={{ width: "100%", padding: "0.5rem", border: "1px solid #d1d5db", borderRadius: "5px", fontSize: "1rem" }}
        >
          {events.map((event) => (
            <option key={event.id} value={event.id}>{event.name} ({event.date})</option>
          ))}
        </select>
      </div>

      {selectedEvent && (
        <div>
          <div style={{ display: "flex", gap: "0.5rem", marginBottom: "2rem", borderBottom: "2px solid #e5e7eb", overflowX: "auto" }}>
            {[
              { id: "overview", label: "📊 Overview" },
              { id: "budget", label: "💰 Budget" },
              { id: "expenses", label: "💸 Expenses" },
              { id: "sponsors", label: "🤝 Sponsors" },
              { id: "approvals", label: "✋ Approvals" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  padding: "1rem",
                  border: "none",
                  background: activeTab === tab.id ? "#3b82f6" : "transparent",
                  color: activeTab === tab.id ? "white" : "#666",
                  cursor: "pointer",
                  fontWeight: activeTab === tab.id ? "bold" : "normal",
                  borderBottom: activeTab === tab.id ? "3px solid #3b82f6" : "none",
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {activeTab === "overview" && (
            <div>
              {/* Financial KPI Row */}
              <div className="stat-row" style={{ marginBottom: "1.5rem" }}>
                <div className="stat-card">
                  <div className="stat-value">₹{(budget?.total_budget || selectedEvent.budget || 0).toLocaleString()}</div>
                  <div className="stat-label">Total Budget</div>
                </div>
                <div className="stat-card" style={{ background: "#dc2626" }}>
                  <div className="stat-value">₹{(budget?.total_expenses || expenses?.total_expenses || 0).toLocaleString()}</div>
                  <div className="stat-label">Total Expenses</div>
                </div>
                <div className="stat-card" style={{ background: "#059669" }}>
                  <div className="stat-value">₹{(budget?.remaining_budget ?? 0).toLocaleString()}</div>
                  <div className="stat-label">Remaining</div>
                </div>
                <div className="stat-card" style={{ background: "#7c3aed" }}>
                  <div className="stat-value">{(budget?.budget_utilization || 0).toFixed(1)}%</div>
                  <div className="stat-label">Utilization</div>
                </div>
                <div className="stat-card" style={{ background: "#0891b2" }}>
                  <div className="stat-value">₹{(sponsors?.total_sponsorship_confirmed || 0).toLocaleString()}</div>
                  <div className="stat-label">Sponsorship Revenue</div>
                </div>
              </div>

              {/* Budget utilization bar */}
              {budget && (
                <div className="card" style={{ marginBottom: "1.5rem" }}>
                  <h3>Budget Utilization</h3>
                  <div style={{ marginTop: "1rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.9rem", marginBottom: "0.5rem" }}>
                      <span>₹{(budget.total_expenses || 0).toLocaleString()} spent</span>
                      <span>₹{(budget.total_budget || 0).toLocaleString()} budget</span>
                    </div>
                    <div className="progress-track" style={{ height: "20px" }}>
                      <div
                        className="progress-fill"
                        style={{
                          width: `${Math.min(budget.budget_utilization || 0, 100)}%`,
                          background: budget.is_over_budget ? "#dc2626" : "#3b82f6",
                        }}
                      />
                    </div>
                    {budget.is_over_budget && (
                      <p style={{ color: "#dc2626", fontSize: "0.9rem", marginTop: "0.5rem" }}>
                        ⚠️ Over budget by ₹{Math.abs(budget.remaining_budget).toLocaleString()}
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Expense breakdown by category */}
              {expenses?.by_category?.length > 0 && (
                <div className="card" style={{ marginBottom: "1.5rem" }}>
                  <h3>Expenses by Category</h3>
                  <div style={{ marginTop: "1rem" }}>
                    {expenses.by_category.map((cat) => {
                      const pct = expenses.total_expenses
                        ? Math.round((cat.total / expenses.total_expenses) * 100)
                        : 0;
                      return (
                        <div key={cat.category} style={{ marginBottom: "0.75rem" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.9rem", marginBottom: "0.25rem" }}>
                            <span><strong>{cat.category}</strong> ({cat.count} items)</span>
                            <span>₹{cat.total?.toLocaleString()} ({pct}%)</span>
                          </div>
                          <div className="progress-track" style={{ height: "8px" }}>
                            <div className="progress-fill" style={{ width: `${pct}%`, background: "#4338ca" }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Event details + balance calculation */}
              <div className="card">
                <h3>Financial Balance Sheet</h3>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginTop: "1rem" }}>
                  <div>
                    <div style={{ fontSize: "0.9rem", color: "#666" }}>Event</div>
                    <div style={{ fontWeight: "bold" }}>{selectedEvent.name} · {selectedEvent.date}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: "0.9rem", color: "#666" }}>Status</div>
                    <div style={{ fontWeight: "bold" }}>{selectedEvent.status?.toUpperCase()}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: "0.9rem", color: "#666" }}>Total Expenses</div>
                    <div style={{ fontWeight: "bold", color: "#dc2626" }}>₹{(expenses?.total_expenses || 0).toLocaleString()}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: "0.9rem", color: "#666" }}>Confirmed Sponsorship</div>
                    <div style={{ fontWeight: "bold", color: "#059669" }}>₹{(sponsors?.total_sponsorship_confirmed || 0).toLocaleString()}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: "0.9rem", color: "#666" }}>Net Balance (Budget − Expenses + Sponsors)</div>
                    <div style={{ fontWeight: "bold", fontSize: "1.2rem" }}>
                      ₹{(
                        (budget?.total_budget || selectedEvent.budget || 0)
                        - (expenses?.total_expenses || 0)
                        + (sponsors?.total_sponsorship_confirmed || 0)
                      ).toLocaleString()}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: "0.9rem", color: "#666" }}>Registered Attendees</div>
                    <div style={{ fontWeight: "bold" }}>{selectedEvent.registered_count || 0} / {selectedEvent.capacity}</div>
                  </div>
                </div>
                {!budget && (
                  <p style={{ marginTop: "1rem", color: "#d97706" }}>
                    No formal budget set yet. <button className="btn btn-sm btn-primary" onClick={() => setActiveTab("budget")}>Create Budget</button>
                  </p>
                )}
              </div>
            </div>
          )}

          {activeTab === "budget" && <BudgetManagement event={selectedEvent} refreshData={() => { loadData(); loadFinancials(selectedEventId); }} />}
          {activeTab === "expenses" && <ExpenseTracking event={selectedEvent} refreshData={() => { loadData(); loadFinancials(selectedEventId); }} />}
          {activeTab === "sponsors" && <SponsorshipManagement event={selectedEvent} refreshData={() => { loadData(); loadFinancials(selectedEventId); }} />}
          {activeTab === "approvals" && <ApprovalWorkflow event={selectedEvent} refreshData={loadData} />}
        </div>
      )}
    </div>
  );
}
