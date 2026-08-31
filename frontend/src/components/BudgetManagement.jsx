import { useEffect, useState } from "react";
import { api } from "../api/api";

export default function BudgetManagement({ event, refreshData }) {
  const [budget, setBudget] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({ total_budget: 0, notes: "" });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    if (event?.id) loadBudget();
  }, [event]);

  const loadBudget = async () => {
    setLoading(true);
    try {
      try {
        const budgetData = await api.getBudget(event.id);
        setBudget(budgetData);
        setFormData({ total_budget: budgetData.total_budget, notes: budgetData.notes || "" });
      } catch (err) {
        if (err.message?.includes("not found") || err.message?.includes("404")) {
          setBudget(null);
        } else {
          throw err;
        }
      }

      try {
        const summaryData = await api.getBudgetSummary(event.id);
        setSummary(summaryData);
      } catch {
        setSummary(null);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to load budget data");
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    try {
      await api.createBudget(event.id, formData);
      setSuccess("Budget created successfully!");
      setIsEditing(false);
      loadBudget();
      if (refreshData) refreshData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    try {
      await api.updateBudget(event.id, formData);
      setSuccess("Budget updated successfully!");
      setIsEditing(false);
      loadBudget();
      if (refreshData) refreshData();
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) {
    return <div className="loading-state"><div className="spinner"></div><p>Loading budget...</p></div>;
  }

  return (
    <div className="card">
      <div style={{ marginBottom: "1rem" }}>
        <h3>💰 Budget Management</h3>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {!budget && !isEditing ? (
        <div className="empty-state">
          <p>No budget set for this event</p>
          <button
            onClick={() => {
              setIsEditing(true);
              setFormData({ total_budget: event.budget || 0, notes: "" });
            }}
            className="btn btn-primary"
          >
            Create Budget
          </button>
        </div>
      ) : isEditing ? (
        <form onSubmit={budget ? handleUpdate : handleCreate}>
          <div className="form-group">
            <label>Total Budget (₹)</label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={formData.total_budget}
              onChange={(e) =>
                setFormData({ ...formData, total_budget: parseFloat(e.target.value) || 0 })
              }
              required
            />
          </div>

          <div className="form-group">
            <label>Notes</label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              placeholder="Budget notes (optional)"
              rows="3"
            />
          </div>

          <div style={{ display: "flex", gap: "1rem" }}>
            <button type="submit" className="btn btn-primary">
              {budget ? "Update" : "Create"} Budget
            </button>
            <button type="button" onClick={() => setIsEditing(false)} className="btn btn-outline">
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <div>
          <div className="stat-row" style={{ marginBottom: "1rem" }}>
            <div className="stat-card">
              <div className="stat-value">₹{budget?.total_budget?.toLocaleString()}</div>
              <div className="stat-label">Total Budget</div>
            </div>
            <div className="stat-card" style={{ background: "#dc2626" }}>
              <div className="stat-value">₹{summary?.total_expenses?.toLocaleString() || "0"}</div>
              <div className="stat-label">Total Expenses</div>
            </div>
            <div className="stat-card" style={{ background: "#059669" }}>
              <div className="stat-value">₹{summary?.remaining_budget?.toLocaleString() || "0"}</div>
              <div className="stat-label">Remaining Budget</div>
            </div>
            <div className="stat-card" style={{ background: "#2563eb" }}>
              <div className="stat-value">{summary?.budget_utilization?.toFixed(1) || "0"}%</div>
              <div className="stat-label">Utilization</div>
            </div>
          </div>

          {summary && (
            <div style={{ marginBottom: "1rem" }}>
              <div style={{ fontSize: "0.9rem", color: "#666", marginBottom: "0.5rem" }}>
                Budget Utilization Progress
              </div>
              <div style={{ width: "100%", height: "30px", background: "#f0f0f0", borderRadius: "5px", overflow: "hidden" }}>
                <div
                  style={{
                    height: "100%",
                    width: `${Math.min(summary.budget_utilization, 100)}%`,
                    background: summary.budget_utilization > 100 ? "#dc2626" : "#3b82f6",
                    transition: "width 0.3s ease",
                  }}
                />
              </div>
              {summary.is_over_budget && (
                <div style={{ color: "#dc2626", fontSize: "0.9rem", marginTop: "0.5rem" }}>
                  ⚠️ Budget exceeded by ₹{Math.abs(summary.remaining_budget).toLocaleString()}
                </div>
              )}
            </div>
          )}

          {budget?.notes && (
            <div style={{ marginBottom: "1rem", padding: "0.5rem", background: "#f9fafb", borderRadius: "5px" }}>
              <strong>Notes:</strong> {budget.notes}
            </div>
          )}

          <button onClick={() => setIsEditing(true)} className="btn btn-outline">
            Edit Budget
          </button>
        </div>
      )}
    </div>
  );
}
