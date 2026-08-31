import { useEffect, useState } from "react";
import { api } from "../api/api";

const CATEGORIES = ["Venue", "Catering", "Marketing", "Equipment", "Staffing", "Transportation", "Logistics", "Other"];

export default function ExpenseTracking({ event, refreshData }) {
  const [expenses, setExpenses] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [vendors, setVendors] = useState([]);
  const [filterCategory, setFilterCategory] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [formData, setFormData] = useState({
    category: "Other",
    description: "",
    amount: 0,
    date: new Date().toISOString().split("T")[0],
    vendor_id: null,
    status: "pending",
  });

  useEffect(() => {
    if (event?.id) loadData();
  }, [event]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [expList, summaryData, vendorList] = await Promise.all([
        api.getExpenses(event.id),
        api.getExpensesSummary(event.id),
        api.getVendors(),
      ]);
      setExpenses(expList);
      setSummary(summaryData);
      setVendors(vendorList);
    } catch (err) {
      console.error(err);
      setError("Failed to load expenses");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (formData.amount <= 0) {
      setError("Amount must be greater than 0");
      return;
    }

    try {
      if (isEditing) {
        await api.updateExpense(event.id, editingId, formData);
        setSuccess("Expense updated!");
      } else {
        await api.createExpense(event.id, formData);
        setSuccess("Expense created!");
      }
      setIsFormOpen(false);
      setIsEditing(false);
      setEditingId(null);
      resetForm();
      loadData();
      if (refreshData) refreshData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleEdit = (expense) => {
    setFormData({
      category: expense.category,
      description: expense.description,
      amount: expense.amount,
      date: expense.date,
      vendor_id: expense.vendor_id,
      status: expense.status,
    });
    setEditingId(expense.id);
    setIsEditing(true);
    setIsFormOpen(true);
  };

  const handleDelete = async (expenseId) => {
    if (!confirm("Are you sure you want to delete this expense?")) return;
    try {
      await api.deleteExpense(event.id, expenseId);
      setSuccess("Expense deleted!");
      loadData();
      if (refreshData) refreshData();
    } catch (err) {
      setError(err.message);
    }
  };

  const resetForm = () => {
    setFormData({
      category: "Other",
      description: "",
      amount: 0,
      date: new Date().toISOString().split("T")[0],
      vendor_id: null,
      status: "pending",
    });
  };

  const filteredExpenses = filterCategory
    ? expenses.filter((e) => e.category === filterCategory)
    : expenses;

  if (loading) return <div className="loading-state"><div className="spinner"></div></div>;

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h3>💸 Expense Tracking</h3>
        <button
          onClick={() => {
            setIsFormOpen(!isFormOpen);
            setIsEditing(false);
            resetForm();
          }}
          className="btn btn-primary btn-sm"
        >
          {isFormOpen ? "Cancel" : "➕ Add Expense"}
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {isFormOpen && (
        <form onSubmit={handleSubmit} style={{ marginBottom: "1.5rem", padding: "1rem", background: "#f9fafb", borderRadius: "5px" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div className="form-group">
              <label>Category *</label>
              <select
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                required
              >
                {CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Amount (₹) *</label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={formData.amount}
                onChange={(e) => setFormData({ ...formData, amount: parseFloat(e.target.value) })}
                required
              />
            </div>
            <div className="form-group">
              <label>Date *</label>
              <input
                type="date"
                value={formData.date}
                onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label>Vendor (Optional)</label>
              <select
                value={formData.vendor_id || ""}
                onChange={(e) => setFormData({ ...formData, vendor_id: e.target.value ? parseInt(e.target.value) : null })}
              >
                <option value="">None</option>
                {vendors.map((v) => (
                  <option key={v.id} value={v.id}>{v.name}</option>
                ))}
              </select>
            </div>
            <div className="form-group" style={{ gridColumn: "1 / -1" }}>
              <label>Description *</label>
              <input
                type="text"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Expense description"
                required
              />
            </div>
            <div className="form-group">
              <label>Status</label>
              <select
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value })}
              >
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>
          </div>
          <button type="submit" className="btn btn-primary" style={{ marginTop: "1rem" }}>
            {isEditing ? "Update" : "Create"} Expense
          </button>
        </form>
      )}

      {summary && (
        <div style={{ marginBottom: "1rem", padding: "1rem", background: "#f0f9ff", borderRadius: "5px", display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "1rem" }}>
          <div>
            <div style={{ fontSize: "0.9rem", color: "#666" }}>Total Expenses</div>
            <div style={{ fontSize: "1.5rem", fontWeight: "bold" }}>₹{summary.total_expenses?.toLocaleString()}</div>
          </div>
          <div>
            <div style={{ fontSize: "0.9rem", color: "#666" }}>Number of Expenses</div>
            <div style={{ fontSize: "1.5rem", fontWeight: "bold" }}>{expenses.length}</div>
          </div>
        </div>
      )}

      <div style={{ marginBottom: "1rem" }}>
        <label style={{ fontSize: "0.9rem" }}>Filter by Category:</label>
        <select value={filterCategory} onChange={(e) => setFilterCategory(e.target.value)} style={{ marginTop: "0.5rem", width: "100%" }}>
          <option value="">All Categories</option>
          {CATEGORIES.map((cat) => (
            <option key={cat} value={cat}>{cat}</option>
          ))}
        </select>
      </div>

      {filteredExpenses.length === 0 ? (
        <div className="empty-state">
          <p>{filterCategory ? "No expenses in this category" : "No expenses added yet"}</p>
        </div>
      ) : (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Category</th>
                <th>Description</th>
                <th>Amount</th>
                <th>Date</th>
                <th>Vendor</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredExpenses.map((exp) => (
                <tr key={exp.id}>
                  <td>{exp.category}</td>
                  <td>{exp.description}</td>
                  <td>₹{exp.amount?.toLocaleString()}</td>
                  <td>{exp.date}</td>
                  <td>{exp.vendor_id ? vendors.find((v) => v.id === exp.vendor_id)?.name || "N/A" : "-"}</td>
                  <td>
                    <span className={`badge badge-${exp.status === "approved" ? "success" : exp.status === "rejected" ? "danger" : "info"}`}>
                      {exp.status}
                    </span>
                  </td>
                  <td>
                    <button onClick={() => handleEdit(exp)} className="btn btn-sm btn-outline" style={{ marginRight: "0.5rem" }}>
                      Edit
                    </button>
                    <button onClick={() => handleDelete(exp.id)} className="btn btn-sm btn-outline" style={{ color: "#dc2626" }}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
