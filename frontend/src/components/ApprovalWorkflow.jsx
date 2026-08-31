import { useEffect, useState } from "react";
import { api } from "../api/api";

const APPROVAL_STATUSES = ["pending", "approved", "rejected"];

export default function ApprovalWorkflow({ event, refreshData }) {
  const [approvals, setApprovals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState("pending");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [reviewingId, setReviewingId] = useState(null);
  const [reviewData, setReviewData] = useState({ status: "approved", reviewer_comment: "" });

  useEffect(() => {
    if (event?.id) loadApprovals();
  }, [event, filterStatus]);

  const loadApprovals = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ event_id: event.id });
      if (filterStatus) params.set("status", filterStatus);
      const data = await api.getApprovals(params.toString());
      setApprovals(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error(err);
      setError("Failed to load approvals");
    } finally {
      setLoading(false);
    }
  };

  const handleReview = async (approvalId) => {
    setError("");
    setSuccess("");
    try {
      await api.reviewApproval(approvalId, reviewData);
      setSuccess(`Approval ${reviewData.status}!`);
      setReviewingId(null);
      setReviewData({ status: "approved", reviewer_comment: "" });
      loadApprovals();
      if (refreshData) refreshData();
    } catch (err) {
      setError(err.message);
    }
  };

  const statusColor = (status) => ({
    pending: "#f59e0b",
    approved: "#059669",
    rejected: "#dc2626",
  }[status] || "#6b7280");

  const requestTypeIcon = (type) => ({
    vendor: "👤",
    expense: "💸",
    resource: "📦",
    sponsorship: "🤝",
  }[type] || "📋");

  if (loading) return <div className="loading-state"><div className="spinner"></div></div>;

  return (
    <div className="card">
      <div style={{ marginBottom: "1rem" }}>
        <h3>✋ Approval Workflow</h3>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div style={{ marginBottom: "1rem" }}>
        <label style={{ fontSize: "0.9rem" }}>Filter by Status:</label>
        <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} style={{ marginTop: "0.5rem", width: "100%" }}>
          <option value="">All</option>
          {APPROVAL_STATUSES.map((status) => (
            <option key={status} value={status}>{status.charAt(0).toUpperCase() + status.slice(1)}</option>
          ))}
        </select>
      </div>

      {approvals.length === 0 ? (
        <div className="empty-state">
          <p>{filterStatus ? `No ${filterStatus} approvals` : "No approvals"}</p>
        </div>
      ) : (
        <div style={{ display: "grid", gap: "1rem" }}>
          {approvals.map((approval) => (
            <div key={approval.id} style={{ padding: "1rem", border: "1px solid #e5e7eb", borderRadius: "5px", background: "#f9fafb" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: "0.5rem" }}>
                <div>
                  <div style={{ fontSize: "0.9rem", color: "#666" }}>
                    {requestTypeIcon(approval.request_type)} {approval.request_type.toUpperCase()} REQUEST
                  </div>
                  <div style={{ fontSize: "1.1rem", fontWeight: "bold", marginTop: "0.25rem" }}>
                    Request #{approval.id}
                  </div>
                </div>
                <span style={{ background: statusColor(approval.status), color: "white", padding: "0.25rem 0.75rem", borderRadius: "5px", fontSize: "0.9rem" }}>
                  {approval.status.toUpperCase()}
                </span>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem", fontSize: "0.9rem" }}>
                {approval.amount > 0 && (
                  <div>
                    <div style={{ color: "#666" }}>Amount</div>
                    <div style={{ fontWeight: "bold" }}>₹{approval.amount?.toLocaleString()}</div>
                  </div>
                )}
                {approval.reason && (
                  <div>
                    <div style={{ color: "#666" }}>Reason</div>
                    <div>{approval.reason}</div>
                  </div>
                )}
              </div>

              {approval.status === "pending" && reviewingId !== approval.id && (
                <button onClick={() => setReviewingId(approval.id)} className="btn btn-sm btn-outline">
                  Review
                </button>
              )}

              {reviewingId === approval.id && (
                <div style={{ padding: "1rem", background: "white", borderRadius: "5px", marginTop: "1rem" }}>
                  <div className="form-group">
                    <label>Decision</label>
                    <select value={reviewData.status} onChange={(e) => setReviewData({ ...reviewData, status: e.target.value })}>
                      <option value="approved">✅ Approve</option>
                      <option value="rejected">❌ Reject</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Comment (Optional)</label>
                    <textarea
                      value={reviewData.reviewer_comment}
                      onChange={(e) => setReviewData({ ...reviewData, reviewer_comment: e.target.value })}
                      placeholder="Add comment for the requester"
                      rows="2"
                    />
                  </div>
                  <div style={{ display: "flex", gap: "0.5rem" }}>
                    <button onClick={() => handleReview(approval.id)} className="btn btn-sm btn-primary">Submit Review</button>
                    <button onClick={() => setReviewingId(null)} className="btn btn-sm btn-outline">Cancel</button>
                  </div>
                </div>
              )}

              {approval.status !== "pending" && approval.reviewed_at && (
                <div style={{ padding: "0.5rem", background: "#f0f9ff", borderRadius: "5px", fontSize: "0.85rem", marginTop: "0.5rem" }}>
                  <div style={{ color: "#666" }}>Reviewed on {new Date(approval.reviewed_at).toLocaleDateString()}</div>
                  {approval.reviewer_comment && (
                    <div style={{ marginTop: "0.25rem" }}><strong>Comment:</strong> {approval.reviewer_comment}</div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
