import { useEffect, useState } from "react";
import { api } from "../api/api";

const SPONSORSHIP_TYPES = ["Platinum", "Gold", "Silver", "Bronze", "In-kind"];
const SPONSOR_STATUSES = ["pending", "approved", "rejected", "confirmed"];

export default function SponsorshipManagement({ event, refreshData }) {
  const [sponsors, setSponsors] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [filterStatus, setFilterStatus] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [formData, setFormData] = useState({
    sponsor_name: "",
    contact_person: "",
    contact_email: "",
    contact_phone: "",
    sponsorship_amount: 0,
    sponsorship_type: "Gold",
    status: "pending",
    notes: "",
  });

  useEffect(() => {
    if (event?.id) loadData();
  }, [event]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [sponsorList, summaryData] = await Promise.all([
        api.getSponsors(event.id),
        api.getSponsorshipSummary(event.id),
      ]);
      setSponsors(sponsorList);
      setSummary(summaryData);
    } catch (err) {
      console.error(err);
      setError("Failed to load sponsors");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (formData.sponsorship_amount < 0) {
      setError("Amount cannot be negative");
      return;
    }

    try {
      if (isEditing) {
        await api.updateSponsor(event.id, editingId, formData);
        setSuccess("Sponsor updated!");
      } else {
        await api.createSponsor(event.id, formData);
        setSuccess("Sponsor added!");
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

  const handleEdit = (sponsor) => {
    setFormData({
      sponsor_name: sponsor.sponsor_name,
      contact_person: sponsor.contact_person,
      contact_email: sponsor.contact_email,
      contact_phone: sponsor.contact_phone,
      sponsorship_amount: sponsor.sponsorship_amount,
      sponsorship_type: sponsor.sponsorship_type,
      status: sponsor.status,
      notes: sponsor.notes,
    });
    setEditingId(sponsor.id);
    setIsEditing(true);
    setIsFormOpen(true);
  };

  const handleDelete = async (sponsorId) => {
    if (!confirm("Are you sure you want to delete this sponsor?")) return;
    try {
      await api.deleteSponsor(event.id, sponsorId);
      setSuccess("Sponsor deleted!");
      loadData();
      if (refreshData) refreshData();
    } catch (err) {
      setError(err.message);
    }
  };

  const resetForm = () => {
    setFormData({
      sponsor_name: "",
      contact_person: "",
      contact_email: "",
      contact_phone: "",
      sponsorship_amount: 0,
      sponsorship_type: "Gold",
      status: "pending",
      notes: "",
    });
  };

  const filteredSponsors = filterStatus
    ? sponsors.filter((s) => s.status === filterStatus)
    : sponsors;

  const statusColor = (status) => ({
    pending: "#f59e0b",
    approved: "#3b82f6",
    rejected: "#dc2626",
    confirmed: "#059669",
  }[status] || "#6b7280");

  if (loading) return <div className="loading-state"><div className="spinner"></div></div>;

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h3>🤝 Sponsorship Management</h3>
        <button
          onClick={() => { setIsFormOpen(!isFormOpen); setIsEditing(false); resetForm(); }}
          className="btn btn-primary btn-sm"
        >
          {isFormOpen ? "Cancel" : "➕ Add Sponsor"}
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {isFormOpen && (
        <form onSubmit={handleSubmit} style={{ marginBottom: "1.5rem", padding: "1rem", background: "#f9fafb", borderRadius: "5px" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div className="form-group">
              <label>Sponsor Name *</label>
              <input type="text" value={formData.sponsor_name} onChange={(e) => setFormData({ ...formData, sponsor_name: e.target.value })} required />
            </div>
            <div className="form-group">
              <label>Sponsorship Amount (₹) *</label>
              <input type="number" step="0.01" min="0" value={formData.sponsorship_amount} onChange={(e) => setFormData({ ...formData, sponsorship_amount: parseFloat(e.target.value) })} required />
            </div>
            <div className="form-group">
              <label>Contact Person</label>
              <input type="text" value={formData.contact_person} onChange={(e) => setFormData({ ...formData, contact_person: e.target.value })} />
            </div>
            <div className="form-group">
              <label>Contact Email</label>
              <input type="email" value={formData.contact_email} onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })} />
            </div>
            <div className="form-group">
              <label>Contact Phone</label>
              <input type="tel" value={formData.contact_phone} onChange={(e) => setFormData({ ...formData, contact_phone: e.target.value })} />
            </div>
            <div className="form-group">
              <label>Sponsorship Type</label>
              <select value={formData.sponsorship_type} onChange={(e) => setFormData({ ...formData, sponsorship_type: e.target.value })}>
                {SPONSORSHIP_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Status</label>
              <select value={formData.status} onChange={(e) => setFormData({ ...formData, status: e.target.value })}>
                {SPONSOR_STATUSES.map((status) => <option key={status} value={status}>{status.charAt(0).toUpperCase() + status.slice(1)}</option>)}
              </select>
            </div>
            <div className="form-group" style={{ gridColumn: "1 / -1" }}>
              <label>Notes</label>
              <textarea value={formData.notes} onChange={(e) => setFormData({ ...formData, notes: e.target.value })} placeholder="Additional notes (optional)" rows="3" />
            </div>
          </div>
          <button type="submit" className="btn btn-primary" style={{ marginTop: "1rem" }}>
            {isEditing ? "Update" : "Add"} Sponsor
          </button>
        </form>
      )}

      {summary && (
        <div style={{ marginBottom: "1rem", padding: "1rem", background: "#f0f9ff", borderRadius: "5px", display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "1rem" }}>
          <div>
            <div style={{ fontSize: "0.9rem", color: "#666" }}>Total Confirmed Sponsorship</div>
            <div style={{ fontSize: "1.5rem", fontWeight: "bold" }}>₹{summary.total_sponsorship_confirmed?.toLocaleString()}</div>
          </div>
          <div>
            <div style={{ fontSize: "0.9rem", color: "#666" }}>Total Sponsorship (All)</div>
            <div style={{ fontSize: "1.5rem", fontWeight: "bold" }}>₹{summary.total_sponsorship_all?.toLocaleString()}</div>
          </div>
        </div>
      )}

      <div style={{ marginBottom: "1rem" }}>
        <label style={{ fontSize: "0.9rem" }}>Filter by Status:</label>
        <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} style={{ marginTop: "0.5rem", width: "100%" }}>
          <option value="">All Statuses</option>
          {SPONSOR_STATUSES.map((status) => <option key={status} value={status}>{status.charAt(0).toUpperCase() + status.slice(1)}</option>)}
        </select>
      </div>

      {filteredSponsors.length === 0 ? (
        <div className="empty-state">
          <p>{filterStatus ? "No sponsors with this status" : "No sponsors added yet"}</p>
        </div>
      ) : (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Sponsor</th>
                <th>Contact</th>
                <th>Amount</th>
                <th>Type</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredSponsors.map((sponsor) => (
                <tr key={sponsor.id}>
                  <td><strong>{sponsor.sponsor_name}</strong></td>
                  <td>{sponsor.contact_person || sponsor.contact_email || "-"}</td>
                  <td>₹{sponsor.sponsorship_amount?.toLocaleString()}</td>
                  <td>{sponsor.sponsorship_type}</td>
                  <td>
                    <span style={{ background: statusColor(sponsor.status), color: "white", padding: "0.25rem 0.75rem", borderRadius: "5px", fontSize: "0.9rem" }}>
                      {sponsor.status.charAt(0).toUpperCase() + sponsor.status.slice(1)}
                    </span>
                  </td>
                  <td>
                    <button onClick={() => handleEdit(sponsor)} className="btn btn-sm btn-outline" style={{ marginRight: "0.5rem" }}>Edit</button>
                    <button onClick={() => handleDelete(sponsor.id)} className="btn btn-sm btn-outline" style={{ color: "#dc2626" }}>Delete</button>
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
