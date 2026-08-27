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
  const [msg, setMsg] = useState(null);
  const { isOrganizer, isAdmin } = useAuth();

  const load = () =>
    Promise.all([api.getVendors(), api.getEvents(), api.getAssignments()]).then(
      ([v, e, a]) => {
        setVendors(v);
        setEvents(e);
        setAssignments(a);
      }
    );

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
                  {isAdmin && <th>Actions</th>}
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
    </div>
  );
}
