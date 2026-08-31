import { useEffect, useState } from "react";
import { api } from "../api/api";
import { useAuth } from "../context/AuthContext";

const EMPTY_V = { name: "", service_type: "Catering", contact: "", email: "" };
const EMPTY_A = { vendor_id: "", event_id: "" };
const SERVICE_TYPES = [
  "Catering",
  "Decoration",
  "Photography",
  "Sound & Audio",
  "Lighting & Stage",
  "Security & Logistics",
  "Transport",
  "Live Streaming",
  "Other",
];

export default function Vendors() {
  const [vendors, setVendors] = useState([]);
  const [events, setEvents] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [vForm, setVForm] = useState(EMPTY_V);
  const [aForm, setAForm] = useState(EMPTY_A);
  const [ratingId, setRatingId] = useState(null);
  const [ratingVal, setRatingVal] = useState(0);
  const [perfModal, setPerfModal] = useState(null);
  const [viewPerf, setViewPerf] = useState(null);
  const [vendorAnalytics, setVendorAnalytics] = useState(null);
  const [perfForm, setPerfForm] = useState({
    event_id: "",
    quality_rating: 5,
    timeliness_rating: 4,
    cost_rating: 4,
    communication_rating: 5,
    overall_rating: 5,
    comments: "",
  });
  const [msg, setMsg] = useState(null);
  const { isOrganizer, isAdmin } = useAuth();

  const load = () =>
    Promise.all([
      api.getVendors(),
      api.getEvents(),
      api.getAssignments(),
      api.getVendorAnalytics().catch(() => null),
    ]).then(([v, e, a, analytics]) => {
      setVendors(v);
      setEvents(e);
      setAssignments(a);
      setVendorAnalytics(analytics);
    });

  useEffect(() => {
    load();
  }, []);

  const flash = (text, type = "success") => {
    setMsg({ text, type });
    setTimeout(() => setMsg(null), 3500);
  };

  const handleAddVendor = async (e) => {
    e.preventDefault();
    try {
      await api.addVendor(vForm);
      flash("Vendor added to directory!");
      setVForm(EMPTY_V);
      load();
    } catch (err) {
      flash(err.message, "error");
    }
  };

  const handleAssign = async (e) => {
    e.preventDefault();
    try {
      await api.assignVendor({
        vendor_id: parseInt(aForm.vendor_id),
        event_id: parseInt(aForm.event_id),
      });
      flash("Vendor assigned to event!");
      setAForm(EMPTY_A);
      load();
    } catch (err) {
      flash(err.message, "error");
    }
  };

  const handleDeleteVendor = async (id, name) => {
    if (!confirm(`Delete vendor '${name}'?`)) return;
    try {
      await api.deleteVendor(id);
      flash("Vendor deleted!");
      load();
    } catch (err) {
      flash(err.message, "error");
    }
  };

  const handleRemoveAssignment = async (id) => {
    if (!confirm("Remove this vendor assignment?")) return;
    try {
      await api.removeAssignment(id);
      flash("Vendor assignment removed!");
      load();
    } catch (err) {
      flash(err.message, "error");
    }
  };

  const handleRate = async (id) => {
    try {
      await api.rateVendor(id, parseFloat(ratingVal));
      flash("Vendor rating saved!");
      setRatingId(null);
      load();
    } catch (err) {
      flash(err.message, "error");
    }
  };

  const handleViewPerformance = async (vendor) => {
    try {
      const summary = await api.getVendorPerformance(vendor.id);
      setViewPerf({ vendor, summary });
    } catch (err) {
      flash(err.message, "error");
    }
  };

  const openPerformanceModal = (vendor) => {
    const assignedEvents = assignments.filter((a) => a.vendor_id === vendor.id);
    setPerfModal({ vendor, assignedEvents });
    setPerfForm({
      event_id: assignedEvents[0]?.event_id || "",
      quality_rating: 5,
      timeliness_rating: 4,
      cost_rating: 4,
      communication_rating: 5,
      overall_rating: 5,
      comments: "",
    });
  };

  const handlePerformanceSubmit = async (e) => {
    e.preventDefault();
    if (!perfForm.event_id) {
      flash("Select an event to rate this vendor for", "error");
      return;
    }
    try {
      await api.submitVendorRating(perfModal.vendor.id, parseInt(perfForm.event_id), {
        quality_rating: parseInt(perfForm.quality_rating),
        timeliness_rating: parseInt(perfForm.timeliness_rating),
        cost_rating: parseInt(perfForm.cost_rating),
        communication_rating: parseInt(perfForm.communication_rating),
        overall_rating: parseInt(perfForm.overall_rating),
        comments: perfForm.comments,
      });
      flash("Vendor performance rating submitted!");
      setPerfModal(null);
      load();
    } catch (err) {
      flash(err.message, "error");
    }
  };

  const starInput = (label, field) => (
    <div className="form-group">
      <label>{label}</label>
      <select value={perfForm[field]} onChange={(e) => setPerfForm({ ...perfForm, [field]: e.target.value })}>
        {[5, 4, 3, 2, 1].map((n) => (
          <option key={n} value={n}>{"★".repeat(n)}{"☆".repeat(5 - n)} ({n})</option>
        ))}
      </select>
    </div>
  );

  const stars = (n) => "★".repeat(Math.round(n)) + "☆".repeat(5 - Math.round(n));

  return (
    <div>
      <div className="page-header">
        <h1>Vendor & Supplier Management</h1>
        <p>Contract catering, staging, media crews, and rate partner performance</p>
      </div>

      {msg && <div className={`alert alert-${msg.type}`}>{msg.text}</div>}

      {/* Forms (Organizers / Admins) */}
      {isOrganizer && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1.5rem" }}>
          {/* Add Vendor */}
          <div className="card">
            <h2>Add Vendor to Directory</h2>
            <form onSubmit={handleAddVendor}>
              <div className="form-grid">
                <div className="form-group" style={{ gridColumn: "span 2" }}>
                  <label>Vendor / Business Name</label>
                  <input
                    required
                    value={vForm.name}
                    onChange={(e) => setVForm({ ...vForm, name: e.target.value })}
                    placeholder="e.g. Royal Caterers & Event Staging"
                  />
                </div>
                <div className="form-group">
                  <label>Service Domain</label>
                  <select
                    value={vForm.service_type}
                    onChange={(e) => setVForm({ ...vForm, service_type: e.target.value })}
                  >
                    {SERVICE_TYPES.map((s) => (
                      <option key={s}>{s}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Contact Phone</label>
                  <input
                    required
                    value={vForm.contact}
                    onChange={(e) => setVForm({ ...vForm, contact: e.target.value })}
                    placeholder="9876543210"
                  />
                </div>
                <div className="form-group" style={{ gridColumn: "span 2" }}>
                  <label>Email Address</label>
                  <input
                    type="email"
                    value={vForm.email}
                    onChange={(e) => setVForm({ ...vForm, email: e.target.value })}
                    placeholder="partner@royalcatering.com"
                  />
                </div>
              </div>
              <div className="btn-row">
                <button type="submit" className="btn btn-primary">
                  Register Vendor
                </button>
              </div>
            </form>
          </div>

          {/* Assign Vendor */}
          <div className="card">
            <h2>Assign Vendor to Event</h2>
            <form onSubmit={handleAssign}>
              <div className="form-grid">
                <div className="form-group">
                  <label>Select Vendor</label>
                  <select
                    required
                    value={aForm.vendor_id}
                    onChange={(e) => setAForm({ ...aForm, vendor_id: e.target.value })}
                  >
                    <option value="">-- choose vendor --</option>
                    {vendors.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.name} ({v.service_type})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Select Target Event</label>
                  <select
                    required
                    value={aForm.event_id}
                    onChange={(e) => setAForm({ ...aForm, event_id: e.target.value })}
                  >
                    <option value="">-- choose event --</option>
                    {events.map((ev) => (
                      <option key={ev.id} value={ev.id}>
                        {ev.name} ({ev.date})
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="btn-row">
                <button type="submit" className="btn btn-success">
                  Confirm Vendor Assignment
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Vendors Table */}
      <div className="card" style={{ marginTop: isOrganizer ? "1.5rem" : 0 }}>
        <h2>Vendor Directory ({vendors.length})</h2>
        {vendors.length === 0 ? (
          <p className="empty-state">No vendors in the directory.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Vendor Name</th>
                  <th>Service Domain</th>
                  <th>Contact</th>
                  <th>Email</th>
                  <th>Performance Rating</th>
                  {isOrganizer && <th>Actions</th>}
                  {isAdmin && <th>Admin</th>}
                </tr>
              </thead>
              <tbody>
                {vendors.map((v) => (
                  <tr key={v.id}>
                    <td>{v.id}</td>
                    <td>
                      <strong>{v.name}</strong>
                    </td>
                    <td>
                      <span className="badge badge-planned">{v.service_type}</span>
                    </td>
                    <td>{v.contact}</td>
                    <td>{v.email || "—"}</td>
                    <td>
                      {ratingId === v.id ? (
                        <span style={{ display: "flex", gap: "0.3rem", alignItems: "center" }}>
                          <input
                            type="number"
                            min="0"
                            max="5"
                            step="0.5"
                            value={ratingVal}
                            onChange={(e) => setRatingVal(e.target.value)}
                            style={{ width: "60px", padding: "0.2rem", border: "1px solid #ccc", borderRadius: "4px" }}
                          />
                          <button className="btn btn-success btn-sm" onClick={() => handleRate(v.id)}>
                            Save
                          </button>
                          <button className="btn btn-danger btn-sm" onClick={() => setRatingId(null)}>
                            ✕
                          </button>
                        </span>
                      ) : (
                        <span
                          style={{
                            cursor: isOrganizer ? "pointer" : "default",
                            color: "#d97706",
                            fontWeight: 600,
                          }}
                          onClick={() => {
                            if (isOrganizer) {
                              setRatingId(v.id);
                              setRatingVal(v.rating || 5);
                            }
                          }}
                          title={isOrganizer ? "Click to rate" : ""}
                        >
                          {v.rating > 0 ? `${stars(v.rating)} (${v.rating})` : isOrganizer ? "⭐ Rate Partner" : "Not Rated"}
                        </span>
                      )}
                    </td>
                    {isOrganizer && (
                      <td>
                        <button
                          className="btn btn-outline btn-sm"
                          onClick={() => handleViewPerformance(v)}
                          style={{ marginRight: "0.3rem" }}
                        >
                          👁 View
                        </button>
                        <button
                          className="btn btn-primary btn-sm"
                          onClick={() => openPerformanceModal(v)}
                          disabled={!assignments.some((a) => a.vendor_id === v.id)}
                          title={assignments.some((a) => a.vendor_id === v.id) ? "Rate post-event performance" : "Assign vendor to an event first"}
                        >
                          📊 Rate
                        </button>
                      </td>
                    )}
                    {isAdmin && (
                      <td>
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => handleDeleteVendor(v.id, v.name)}
                        >
                          Delete
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Assignments Table */}
      <div className="card">
        <h2>Active Vendor Contracts & Assignments ({assignments.length})</h2>
        {assignments.length === 0 ? (
          <p className="empty-state">No vendor assignments recorded.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Contracted Vendor</th>
                  <th>Service</th>
                  <th>Assigned Event</th>
                  {isOrganizer && <th>Action</th>}
                </tr>
              </thead>
              <tbody>
                {assignments.map((a) => (
                  <tr key={a.id}>
                    <td>{a.id}</td>
                    <td>
                      <strong>{a.vendor_name}</strong>
                    </td>
                    <td>
                      <span className="badge badge-planned">{a.service_type}</span>
                    </td>
                    <td>
                      <strong>{a.event_name}</strong>
                    </td>
                    {isOrganizer && (
                      <td>
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => handleRemoveAssignment(a.id)}
                        >
                          Remove Contract
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Vendor Performance Rankings */}
      {vendorAnalytics?.vendor_comparison?.length > 0 && (
        <div className="card" style={{ marginTop: "1.5rem" }}>
          <h2>📊 Vendor Performance Leaderboard</h2>
          <div className="table-wrap" style={{ marginTop: "1rem" }}>
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Vendor</th>
                  <th>Quality</th>
                  <th>Timeliness</th>
                  <th>Cost</th>
                  <th>Communication</th>
                  <th>Overall</th>
                </tr>
              </thead>
              <tbody>
                {vendorAnalytics.vendor_comparison.map((v, idx) => (
                  <tr key={v.id}>
                    <td>#{idx + 1}</td>
                    <td><strong>{v.name}</strong></td>
                    <td>{stars(v.avg_quality || 0)} ({v.avg_quality || "—"})</td>
                    <td>{stars(v.avg_timeliness || 0)} ({v.avg_timeliness || "—"})</td>
                    <td>{stars(v.avg_cost || 0)} ({v.avg_cost || "—"})</td>
                    <td>{stars(v.avg_communication || 0)} ({v.avg_communication || "—"})</td>
                    <td><strong>{stars(v.avg_overall || 0)} ({v.avg_overall || "—"})</strong></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* View Performance Detail Modal */}
      {viewPerf && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div className="card" style={{ maxWidth: "480px", width: "90%", maxHeight: "90vh", overflow: "auto" }}>
            <h2>{viewPerf.vendor.name}</h2>
            <p style={{ color: "#64748b" }}>Performance summary across {viewPerf.summary?.summary?.total_ratings || 0} rating(s)</p>
            {viewPerf.summary?.summary?.total_ratings > 0 ? (
              <div style={{ marginTop: "1rem" }}>
                {[
                  ["Quality", viewPerf.summary.summary.avg_quality],
                  ["Timeliness", viewPerf.summary.summary.avg_timeliness],
                  ["Cost", viewPerf.summary.summary.avg_cost],
                  ["Communication", viewPerf.summary.summary.avg_communication],
                  ["Overall", viewPerf.summary.summary.avg_overall],
                ].map(([label, val]) => (
                  <div key={label} style={{ marginBottom: "0.75rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span>{label}</span><span>{stars(val)} ({val})</span>
                    </div>
                    <div className="progress-track" style={{ height: "8px" }}>
                      <div className="progress-fill" style={{ width: `${(val / 5) * 100}%`, background: "#d97706" }} />
                    </div>
                  </div>
                ))}
                {viewPerf.summary.recent_ratings?.length > 0 && (
                  <div style={{ marginTop: "1rem" }}>
                    <strong>Recent Ratings:</strong>
                    {viewPerf.summary.recent_ratings.map((r) => (
                      <div key={r.id} style={{ padding: "0.5rem", background: "#f9fafb", borderRadius: "4px", marginTop: "0.5rem", fontSize: "0.85rem" }}>
                        <div><strong>{r.event_name}</strong> — {r.overall_rating} ⭐ overall</div>
                        {r.comments && <div style={{ color: "#64748b" }}>{r.comments}</div>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <p className="empty-state">No performance ratings submitted yet.</p>
            )}
            <button className="btn btn-outline" style={{ marginTop: "1rem" }} onClick={() => setViewPerf(null)}>Close</button>
          </div>
        </div>
      )}

      {/* Vendor Performance Rating Modal */}
      {perfModal && (
        <div style={{
          position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex",
          alignItems: "center", justifyContent: "center", zIndex: 1000,
        }}>
          <div className="card" style={{ maxWidth: "500px", width: "90%", maxHeight: "90vh", overflow: "auto" }}>
            <h2>Rate Vendor: {perfModal.vendor.name}</h2>
            <p style={{ color: "#64748b", marginBottom: "1rem" }}>Evaluate quality, timeliness, cost and communication after the event.</p>
            <form onSubmit={handlePerformanceSubmit}>
              <div className="form-group">
                <label>Event *</label>
                <select
                  required
                  value={perfForm.event_id}
                  onChange={(e) => setPerfForm({ ...perfForm, event_id: e.target.value })}
                >
                  <option value="">-- select event --</option>
                  {perfModal.assignedEvents.map((a) => (
                    <option key={a.id} value={a.event_id}>{a.event_name}</option>
                  ))}
                </select>
              </div>
              {starInput("Quality", "quality_rating")}
              {starInput("Timeliness", "timeliness_rating")}
              {starInput("Cost", "cost_rating")}
              {starInput("Communication", "communication_rating")}
              {starInput("Overall Rating", "overall_rating")}
              <div className="form-group">
                <label>Comments</label>
                <textarea
                  value={perfForm.comments}
                  onChange={(e) => setPerfForm({ ...perfForm, comments: e.target.value })}
                  rows="3"
                  placeholder="Optional feedback..."
                />
              </div>
              <div className="btn-row">
                <button type="submit" className="btn btn-primary">Submit Rating</button>
                <button type="button" className="btn btn-outline" onClick={() => setPerfModal(null)}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
