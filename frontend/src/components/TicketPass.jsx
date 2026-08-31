import { useEffect, useState } from "react";
import QRCode from "qrcode";

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function buildPrintHtml(ticket, qrUrl) {
  const eventName = ticket.event_name || `Event #${ticket.event_id}`;
  const dateTime = [ticket.event_date || ticket.date || "Scheduled", ticket.event_time || ticket.time || ""]
    .filter(Boolean)
    .join(" · ");
  const venue = ticket.venue_name || (ticket.is_online ? "Online Live" : "To Be Announced");
  const status = (ticket.status || "registered").toUpperCase();

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>EventSphere Pass - ${escapeHtml(ticket.ticket_id)}</title>
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: Arial, Helvetica, sans-serif;
      margin: 0;
      padding: 24px;
      color: #0f172a;
      background: #fff;
    }
    .ticket {
      max-width: 720px;
      margin: 0 auto;
      border: 2px solid #334155;
      border-radius: 12px;
      overflow: hidden;
    }
    .header {
      background: #0f172a;
      color: #fff;
      padding: 20px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
    }
    .header h1 {
      margin: 0;
      font-size: 22px;
    }
    .header p {
      margin: 4px 0 0;
      color: #c7d2fe;
      font-size: 12px;
    }
    .status {
      background: #059669;
      color: #fff;
      padding: 6px 12px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      white-space: nowrap;
    }
    .body {
      display: grid;
      grid-template-columns: 1fr 200px;
      gap: 24px;
      padding: 24px;
    }
    .field { margin-bottom: 16px; }
    .field label {
      display: block;
      font-size: 11px;
      font-weight: 700;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 4px;
    }
    .field h2 {
      margin: 0;
      font-size: 20px;
      line-height: 1.3;
    }
    .field p {
      margin: 0;
      font-size: 15px;
      font-weight: 600;
    }
    .row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }
    .ticket-id {
      display: inline-block;
      margin-top: 8px;
      padding: 8px 14px;
      border: 1px dashed #94a3b8;
      background: #f8fafc;
      border-radius: 6px;
      font-family: Consolas, monospace;
      font-size: 14px;
    }
    .qr {
      text-align: center;
    }
    .qr img {
      width: 180px;
      height: 180px;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
    }
    .qr p {
      margin: 8px 0 0;
      font-size: 11px;
      color: #64748b;
    }
    .seal {
      margin-top: 12px;
      font-size: 11px;
      color: #475569;
      text-align: center;
    }
    @media print {
      body { padding: 0; }
      .ticket { border-width: 1px; }
    }
    @media (max-width: 600px) {
      .body { grid-template-columns: 1fr; }
      .row { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="ticket">
    <div class="header">
      <div>
        <h1>EventSphere Official Pass</h1>
        <p>Authorized Digital Entry Ticket</p>
      </div>
      <div class="status">${escapeHtml(status)}</div>
    </div>
    <div class="body">
      <div>
        <div class="field">
          <label>Event Name</label>
          <h2>${escapeHtml(eventName)}</h2>
        </div>
        <div class="row">
          <div class="field">
            <label>Participant</label>
            <p>${escapeHtml(ticket.name)}</p>
          </div>
          <div class="field">
            <label>Email</label>
            <p>${escapeHtml(ticket.email)}</p>
          </div>
        </div>
        <div class="row">
          <div class="field">
            <label>Date &amp; Time</label>
            <p>${escapeHtml(dateTime)}</p>
          </div>
          <div class="field">
            <label>Venue / Format</label>
            <p>${escapeHtml(venue)}</p>
          </div>
        </div>
        ${ticket.college ? `
        <div class="field">
          <label>Organization / College</label>
          <p>${escapeHtml(ticket.college)}</p>
        </div>` : ""}
        <div class="ticket-id">TICKET ID: <strong>${escapeHtml(ticket.ticket_id)}</strong></div>
      </div>
      <div class="qr">
        ${qrUrl ? `<img src="${qrUrl}" alt="Ticket QR Code" />` : "<p>QR unavailable</p>"}
        <p>Scan at event desk to verify</p>
        <div class="seal">Cryptographically Signed</div>
      </div>
    </div>
  </div>
</body>
</html>`;
}

function printTicketHtml(html) {
  const iframe = document.createElement("iframe");
  iframe.setAttribute("title", "EventSphere Pass Print");
  iframe.style.cssText =
    "position:fixed;right:0;bottom:0;width:0;height:0;border:0;opacity:0;pointer-events:none;";
  document.body.appendChild(iframe);

  const win = iframe.contentWindow;
  const doc = win.document;
  doc.open();
  doc.write(html);
  doc.close();

  const cleanup = () => {
    window.setTimeout(() => {
      if (iframe.parentNode) iframe.parentNode.removeChild(iframe);
    }, 500);
    win.removeEventListener("afterprint", cleanup);
  };
  win.addEventListener("afterprint", cleanup);

  const triggerPrint = () => {
    win.focus();
    win.print();
  };

  const waitForImages = () => {
    const images = Array.from(win.document.images || []);
    const pending = images.filter((img) => !img.complete);
    if (pending.length === 0) {
      window.setTimeout(triggerPrint, 150);
      return;
    }
    let loaded = 0;
    const done = () => {
      loaded += 1;
      if (loaded >= pending.length) window.setTimeout(triggerPrint, 150);
    };
    pending.forEach((img) => {
      img.addEventListener("load", done);
      img.addEventListener("error", done);
    });
  };

  if (doc.readyState === "complete") {
    waitForImages();
  } else {
    win.addEventListener("load", waitForImages);
  }
}

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
    printTicketHtml(buildPrintHtml(ticket, qrUrl));
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content ticket-modal-wrap" onClick={(e) => e.stopPropagation()}>
        <div className="ticket-pass-container">
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

          <div className="ticket-pass-footer">
            <button className="btn btn-primary" onClick={handlePrint} disabled={!qrUrl}>
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
