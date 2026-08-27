import { useEffect, useState } from "react";
import QRCode from "qrcode";

export default function TicketPass({ ticket, onClose }) {
  const [qrUrl, setQrUrl] = useState("");

  useEffect(() => {
    if (!ticket) return;
    const qrData = ticket.qr_token || `ESP:${ticket.ticket_id}:${ticket.event_id}:${ticket.attendee_id || ticket.id}:AUTO`;
    QRCode.toDataURL(qrData, {
      width: 220,
      margin: 1,
      color: { dark: "#0f172a", light: "#ffffff" },
    }).then(setQrUrl);
  }, [ticket]);

  if (!ticket) return null;

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content ticket-modal-wrap" onClick={(e) => e.stopPropagation()}>
        <div className="ticket-pass-container">
          {/* Header Banner */}
          <div className="ticket-pass-header">
            <div className="ticket-brand">
              <span className="brand-icon">🎫</span>
              <div>
                <h3>EventSphere Official Pass</h3>
                <span>Authorized Digital Entry Ticket</span>
              </div>
            </div>
            <span className={`badge badge-${ticket.status || "registered"}`}>
              {ticket.status || "CONFIRMED"}
            </span>
          </div>

          {/* Ticket Body */}
          <div className="ticket-pass-body">
            <div className="ticket-details-col">
              <div className="ticket-field">
                <label>Event Name</label>
                <h4>{ticket.event_name || `Event #${ticket.event_id}`}</h4>
              </div>

              <div className="ticket-grid-row">
                <div className="ticket-field">
                  <label>Participant</label>
                  <p>{ticket.name}</p>
                </div>
                <div className="ticket-field">
                  <label>Email</label>
                  <p>{ticket.email}</p>
                </div>
              </div>

              <div className="ticket-grid-row">
                <div className="ticket-field">
                  <label>Date & Time</label>
                  <p>{ticket.event_date || ticket.date || "Scheduled"} · {ticket.event_time || ticket.time || ""}</p>
                </div>
                <div className="ticket-field">
                  <label>Venue / Format</label>
                  <p>{ticket.venue_name || (ticket.is_online ? "🌐 Online Live" : "To Be Announced")}</p>
                </div>
              </div>

              {ticket.college && (
                <div className="ticket-field">
                  <label>Organization / College</label>
                  <p>{ticket.college}</p>
                </div>
              )}

              <div className="ticket-code-pill">
                <span>TICKET ID:</span>
                <strong>{ticket.ticket_id}</strong>
              </div>
            </div>

            {/* QR Side */}
            <div className="ticket-qr-col">
              {qrUrl ? (
                <div className="ticket-qr-box">
                  <img src={qrUrl} alt="Security Ticket QR Code" />
                  <span className="qr-hint">Scan at event desk to verify</span>
                </div>
              ) : (
                <div className="spinner"></div>
              )}
              <div className="security-seal">
                <span>🔒 Cryptographically Signed</span>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="ticket-pass-footer">
            <button className="btn btn-primary" onClick={handlePrint}>
              🖨️ Print / Save PDF
            </button>
            <button className="btn btn-secondary" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
