const BASE = "http://localhost:8000";

const getToken = () => localStorage.getItem("eventsphere_token");

const getHeaders = (extra = {}) => {
  const headers = { "Content-Type": "application/json", ...extra };
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
};

const handle = async (res) => {
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    const detail = err.detail;
    const message = Array.isArray(detail)
      ? detail.map((e) => e.msg || String(e)).join("; ")
      : detail || "Request failed";
    throw new Error(message);
  }
  return res.json();
};

const post = (url, data) =>
  fetch(`${BASE}${url}`, { method: "POST", headers: getHeaders(), body: JSON.stringify(data) }).then(handle);

const put = (url, data) =>
  fetch(`${BASE}${url}`, { method: "PUT", headers: getHeaders(), body: JSON.stringify(data) }).then(handle);

const del = (url) =>
  fetch(`${BASE}${url}`, { method: "DELETE", headers: getHeaders() }).then(handle);

const get = (url) =>
  fetch(`${BASE}${url}`, { headers: getHeaders() }).then(handle);

export const api = {
  // ── Auth & Users ───────────────────────────────────────────────────────────
  login:            (data)        => post("/auth/login", data),
  registerUser:     (data)        => post("/auth/register", data),
  getMe:            ()            => get("/auth/me"),
  updateProfile:    (data)        => put("/auth/profile", data),
  changePassword:   (data)        => put("/auth/change-password", data),
  forgotPassword:   (data)        => post("/auth/forgot-password", data),
  resetPassword:    (data)        => post("/auth/reset-password", data),
  getUsers:         (params = "") => get(`/auth/users${params ? `?${params}` : ""}`),
  updateUserRole:   (id, role)    => put(`/auth/users/${id}/role`, { role }),
  updateUserStatus: (id, status)  => put(`/auth/users/${id}/status`, { status }),
  deleteUser:       (id)          => del(`/auth/users/${id}`),

  // ── Events ─────────────────────────────────────────────────────────────────
  getEvents:        (query = "")  => get(`/events${query ? `?${query}` : ""}`),
  getMyEvents:      ()            => get("/events/organizer/my-events"),
  getEvent:         (id)          => get(`/events/${id}`),
  createEvent:      (data)        => post("/events", data),
  updateEvent:      (id, data)    => put(`/events/${id}`, data),
  deleteEvent:      (id)          => del(`/events/${id}`),
  assignVenue:      (eid, vid)    => put(`/events/${eid}/venue`, { venue_id: vid }),

  // ── Venues ─────────────────────────────────────────────────────────────────
  getVenues:        ()            => get("/venues"),
  addVenue:         (data)        => post("/venues", data),
  deleteVenue:      (id)          => del(`/venues/${id}`),

  // ── Resources ──────────────────────────────────────────────────────────────
  getResources:       ()          => get("/resources"),
  addResource:        (data)      => post("/resources", data),
  allocateResource:   (data)      => post("/resources/allocate", data),
  getAllocations:     ()          => get("/resources/allocations"),
  deallocateResource: (id)        => del(`/resources/allocations/${id}`),
  deleteResource:     (id)        => del(`/resources/${id}`),

  // ── Registrations & Tickets ────────────────────────────────────────────────
  register:               (data)       => post("/registrations", data),
  getMyRegistrations:     ()           => get("/registrations/my"),
  getAllRegistrations:    (params = "")=> get(`/registrations${params ? `?${params}` : ""}`),
  getRegistrationsByEvent:(eid)        => get(`/registrations/event/${eid}`),
  getAttendance:          (eid)        => get(`/registrations/attendance/${eid}`),
  verifyCheckin:          (data)       => post("/registrations/verify-checkin", data),
  checkin:                (id)         => post(`/registrations/${id}/checkin`, {}),
  markAbsent:             (id)         => post(`/registrations/${id}/absent`, {}),
  cancelRegistration:     (id)         => del(`/registrations/${id}`),

  // ── Vendors ────────────────────────────────────────────────────────────────
  getVendors:         ()               => get("/vendors"),
  addVendor:          (data)           => post("/vendors", data),
  rateVendor:         (id, rating)     => put(`/vendors/${id}/rating`, { rating }),
  deleteVendor:       (id)             => del(`/vendors/${id}`),
  getAssignments:     ()               => get("/vendors/assignments"),
  assignVendor:       (data)           => post("/vendors/assign", data),
  removeAssignment:   (id)             => del(`/vendors/assignments/${id}`),

  // ── Notifications ──────────────────────────────────────────────────────────
  getNotifications:      ()            => get("/notifications"),
  markNotificationRead:  (id)          => put(`/notifications/${id}/read`, {}),
  markAllNotificationsRead: ()         => put("/notifications/read-all", {}),
  deleteNotification:    (id)          => del(`/notifications/${id}`),

  // ── Analytics ──────────────────────────────────────────────────────────────
  getAnalyticsSummary:      (range="30") => get(`/analytics/summary?range=${range}`),
  getRegistrationsOverTime: (range="30") => get(`/analytics/registrations-over-time?range=${range}`),
  getCategoryDistribution:  ()           => get("/analytics/category-distribution"),
  getTopEvents:             (limit=5)    => get(`/analytics/top-events?limit=${limit}`),
  getAttendanceBreakdown:   ()           => get("/analytics/attendance-breakdown"),
  getAnalyticsOverview:     ()           => get("/analytics/overview"),
  getAttendanceAnalytics:   ()           => get("/analytics/attendance"),
  getBudgetAnalytics:       (eventId)    => get(`/analytics/budget${eventId ? `?event_id=${eventId}` : ""}`),
  getVendorAnalytics:       ()           => get("/analytics/vendors"),
  getResourceAnalytics:     ()           => get("/analytics/resources"),
  getEventComparison:       (eventIds)   => get(`/analytics/event-comparison?event_ids=${eventIds.join(",")}`),
  getForecast:              ()           => get("/analytics/forecast"),
  getAuditLogs:             (params = "") => get(`/analytics/audit-logs${params ? `?${params}` : ""}`),
  getCheckinLogs:           (eventId)    => get(`/registrations/checkins${eventId ? `?event_id=${eventId}` : ""}`),


  // ── Budget Management ──────────────────────────────────────────────────────
  createBudget:          (eventId, data) => post(`/budgets/${eventId}`, data),
  getBudget:             (eventId)       => get(`/budgets/${eventId}`),
  updateBudget:          (eventId, data) => put(`/budgets/${eventId}`, data),
  deleteBudget:          (eventId)       => del(`/budgets/${eventId}`),
  getBudgetSummary:      (eventId)       => get(`/budgets/${eventId}/summary`),

  // ── Expense Tracking ───────────────────────────────────────────────────────
  createExpense:         (eventId, data) => post(`/expenses/${eventId}/expenses`, data),
  getExpenses:           (eventId)       => get(`/expenses/${eventId}/expenses`),
  updateExpense:         (eventId, expenseId, data) => put(`/expenses/${eventId}/expenses/${expenseId}`, data),
  deleteExpense:         (eventId, expenseId) => del(`/expenses/${eventId}/expenses/${expenseId}`),
  getExpense:            (eventId, expenseId) => get(`/expenses/${eventId}/expenses/${expenseId}`),
  getExpensesSummary:    (eventId)       => get(`/expenses/${eventId}/expenses-summary`),

  // ── Sponsorship Management ─────────────────────────────────────────────────
  createSponsor:         (eventId, data) => post(`/sponsors/${eventId}/sponsors`, data),
  getSponsors:           (eventId)       => get(`/sponsors/${eventId}/sponsors`),
  updateSponsor:         (eventId, sponsorId, data) => put(`/sponsors/${eventId}/sponsors/${sponsorId}`, data),
  deleteSponsor:         (eventId, sponsorId) => del(`/sponsors/${eventId}/sponsors/${sponsorId}`),
  getSponsor:            (eventId, sponsorId) => get(`/sponsors/${eventId}/sponsors/${sponsorId}`),
  getSponsorshipSummary: (eventId)       => get(`/sponsors/${eventId}/sponsors-summary`),

  // ── Approval Workflow ──────────────────────────────────────────────────────
  getApprovals:          (params = "")   => get(`/approvals${params ? `?${params}` : ""}`),
  getApproval:           (approvalId)    => get(`/approvals/${approvalId}`),
  reviewApproval:        (approvalId, data) => put(`/approvals/${approvalId}/review`, data),
  getPendingApprovalsCount: () => get("/approvals/stats/pending-count"),

  // ── Vendor Performance & Ratings ───────────────────────────────────────────
  submitVendorRating:    (vendorId, eventId, data) => post(`/vendor-performance/${vendorId}/performance?event_id=${eventId}`, data),
  getVendorPerformance:  (vendorId)       => get(`/vendor-performance/${vendorId}/performance-summary`),
  getVendorRatings:      (vendorId)       => get(`/vendor-performance/${vendorId}/performance`),
  getTopVendors:         (params = "")    => get(`/vendor-performance/rankings/top-vendors${params ? `?${params}` : ""}`),
  updateVendorRating:    (vendorId, ratingId, data) => put(`/vendor-performance/${vendorId}/performance/${ratingId}`, data),

  // ── Reminders ──────────────────────────────────────────────────────────────
  sendEventReminders:    (eventId)       => post(`/reminders/${eventId}/send`, {}),
  getReminderTracking:   (eventId)       => get(`/reminders/${eventId}/tracking`),
  processScheduledReminders: () => post("/reminders/process-scheduled-reminders", {}),

  // ── Reports & CSV Exports ──────────────────────────────────────────────────
  getReport:         ()                => get("/reports"),
  downloadExport: async (url, filename) => {
    const token = getToken();
    const res = await fetch(`${BASE}${url}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error("Download failed");
    const blob = await res.blob();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  },
};
