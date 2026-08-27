import { useState } from "react";
import { api } from "../api/api";

export default function QRScannerModal({ eventId, onCheckinSuccess, onClose }) {
  const [inputVal, setInputVal] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleVerify = async (e) => {
    e?.preventDefault();
    if (!inputVal.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await api.verifyCheckin({
        qr_data: inputVal.trim(),
        event_id: eventId ? parseInt(eventId) : undefined,
      });
      setResult(res);
      setInputVal("");
      if (onCheckinSuccess) onCheckinSuccess(res);
    } catch (err) {
      setError(err.message || "Failed to verify check-in.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content scanner-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ fontSize: "1.5rem" }}>📷</span>
            <div>
              <h3>Event Check-In Terminal</h3>
              <p style={{ fontSize: "0.8rem", color: "#64748b", margin: 0 }}>
                Scan or paste cryptographic QR payload / Ticket ID
              </p>
            </div>
          </div>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="scanner-body">
          {/* Scanner Simulation Viewport */}
          <div className="scanner-viewport">
            <div className="scanner-laser"></div>
            <div className="scanner-target">
              <span>Ready to Verify</span>
            </div>
          </div>

          <form onSubmit={handleVerify} className="scanner-form">
            <div className="form-group">
              <label>Scan / Enter Ticket Code or QR Payload</label>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <input
                  type="text"
                  required
                  autoFocus
                  placeholder="e.g. ESP:TKT0001:1:1:b4a9... or TKT0001"
                  value={inputVal}
                  onChange={(e) => setInputVal(e.target.value)}
                />
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  {loading ? "Verifying..." : "Check In"}
                </button>
              </div>
            </div>
          </form>

          {/* Feedback Messages */}
          {error && (
            <div className="alert alert-error" style={{ marginTop: "1rem" }}>
              <strong>Check-In Failed:</strong> {error}
            </div>
          )}

          {result && (
            <div className="alert alert-success" style={{ marginTop: "1rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                <span style={{ fontSize: "1.8rem" }}>✅</span>
                <div>
                  <h4 style={{ margin: 0 }}>{result.message}</h4>
                  <p style={{ margin: "0.2rem 0 0 0", fontSize: "0.85rem" }}>
                    <strong>{result.attendee?.name}</strong> ({result.attendee?.ticket_id}) · {result.attendee?.college || "General"}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
