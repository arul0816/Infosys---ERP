import os
import sys
import unittest
from fastapi.testclient import TestClient

# Add backend dir to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from main import app
from database import init_db, get_db

client = TestClient(app)


class TestEventSphereBackend(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        # Create fresh test accounts instead of depending on demo credentials.
        admin_email = f"admin_{os.urandom(4).hex()}@test.com"
        org_email = f"organizer_{os.urandom(4).hex()}@test.com"
        user_email = f"user_{os.urandom(4).hex()}@test.com"

        res_admin = client.post("/auth/register", json={
            "name": "Admin Test User",
            "email": admin_email,
            "password": "adminpass123",
            "role": "admin",
            "phone": "1111111111",
            "organization": "Test Org"
        })
        self.assertEqual(res_admin.status_code, 201)
        self.admin_token = res_admin.json()["token"]

        res_org = client.post("/auth/register", json={
            "name": "Organizer Test User",
            "email": org_email,
            "password": "organizerpass123",
            "role": "organizer",
            "phone": "2222222222",
            "organization": "Test Org"
        })
        self.assertEqual(res_org.status_code, 201)
        self.org_token = res_org.json()["token"]

        res_user = client.post("/auth/register", json={
            "name": "Participant Test User",
            "email": user_email,
            "password": "userpass123",
            "role": "participant",
            "phone": "3333333333",
            "organization": "Test Org"
        })
        self.assertEqual(res_user.status_code, 201)
        self.user_token = res_user.json()["token"]

    def test_00_demo_admin_account(self):
        db = get_db()
        legacy_demos = db.execute(
            "SELECT email FROM users WHERE email IN (?, ?, ?)",
            ("organizer@eventsphere.com", "user@eventsphere.com", "sneha@eventsphere.com")
        ).fetchall()
        db.close()
        self.assertEqual(legacy_demos, [])

        login_res = client.post("/auth/login", json={
            "email": "admin@eventsphere.com",
            "password": "admin123",
        })
        self.assertEqual(login_res.status_code, 200)
        self.assertEqual(login_res.json()["user"]["role"], "admin")

    # ── 1. Authentication & RBAC Tests ────────────────────────────────────────

    def test_01_user_registration_and_login(self):
        email = f"testuser_{os.urandom(4).hex()}@test.com"
        reg_res = client.post("/auth/register", json={
            "name": "Integration Tester",
            "email": email,
            "password": "securepassword123",
            "role": "participant",
            "phone": "9988776655",
            "organization": "Test Academy"
        })
        self.assertEqual(reg_res.status_code, 201)
        self.assertIn("token", reg_res.json())
        self.assertEqual(reg_res.json()["user"]["email"], email)

        # Login
        login_res = client.post("/auth/login", json={"email": email, "password": "securepassword123"})
        self.assertEqual(login_res.status_code, 200)
        self.assertIn("token", login_res.json())

        # Invalid login
        bad_login = client.post("/auth/login", json={"email": email, "password": "wrongpassword"})
        self.assertEqual(bad_login.status_code, 401)

    def test_02_rbac_protections(self):
        # Participant cannot access admin user list
        res = client.get("/auth/users", headers={"Authorization": f"Bearer {self.user_token}"})
        self.assertEqual(res.status_code, 403)

        # Admin can access user list
        res_admin = client.get("/auth/users", headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res_admin.status_code, 200)
        self.assertIsInstance(res_admin.json(), list)

    # ── 2. Event Management Tests ─────────────────────────────────────────────

    def test_03_create_and_manage_event(self):
        # Create Venue
        v_res = client.post("/venues/", json={
            "name": f"Auditorium-{os.urandom(3).hex()}",
            "capacity": 200,
            "location": "North Wing, Floor 2"
        }, headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(v_res.status_code, 201)
        venue_id = v_res.json()["id"]

        # Create Event
        ev_res = client.post("/events/", json={
            "name": "AI Innovation Summit 2026",
            "event_type": "Conference",
            "date": "2026-10-15",
            "time": "10:00 AM",
            "budget": 75000,
            "status": "published",
            "venue_id": venue_id,
            "description": "Annual deep dive into modern AI architectures.",
            "capacity": 2, # Small capacity to test waitlist
            "category": "Technology",
            "is_online": False,
            "visibility": "public"
        }, headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(ev_res.status_code, 201)
        event_id = ev_res.json()["id"]

        # Query Event Detail
        detail_res = client.get(f"/events/{event_id}")
        self.assertEqual(detail_res.status_code, 200)
        self.assertEqual(detail_res.json()["capacity"], 2)
        self.assertEqual(detail_res.json()["remaining_seats"], 2)

    # ── 3. Registration, Capacity, Waitlist & Auto-Promotion Tests ─────────────

    def test_04_capacity_and_waitlist_auto_promotion(self):
        # Create special event with capacity of 1
        ev_res = client.post("/events/", json={
            "name": "Exclusive Leadership Workshop",
            "event_type": "Workshop",
            "date": "2026-11-20",
            "time": "02:00 PM",
            "budget": 20000,
            "status": "published",
            "capacity": 1,
            "category": "Leadership"
        }, headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(ev_res.status_code, 201)
        event_id = ev_res.json()["id"]

        # 1st Registration -> Confirmed
        reg1_res = client.post("/registrations/", json={
            "event_id": event_id,
            "name": "First Attendee",
            "email": "first@test.com",
            "phone": "1112223333",
            "college": "MIT"
        })
        self.assertEqual(reg1_res.status_code, 201)
        data1 = reg1_res.json()
        self.assertEqual(data1["status"], "registered")
        self.assertIsNotNone(data1["ticket_id"])
        self.assertIsNotNone(data1["qr_token"])
        attendee1_id = data1["attendee_id"]
        ticket1_id = data1["ticket_id"]
        qr_token1 = data1["qr_token"]

        # Duplicate registration check
        dup_res = client.post("/registrations/", json={
            "event_id": event_id,
            "name": "First Attendee Again",
            "email": "first@test.com",
            "phone": "1112223333"
        })
        self.assertEqual(dup_res.status_code, 400)

        # 2nd Registration -> Waitlisted (since capacity = 1)
        reg2_res = client.post("/registrations/", json={
            "event_id": event_id,
            "name": "Waitlisted Attendee",
            "email": "waitlist@test.com",
            "phone": "4445556666",
            "college": "Stanford"
        })
        self.assertEqual(reg2_res.status_code, 201)
        data2 = reg2_res.json()
        self.assertEqual(data2["status"], "waitlisted")
        self.assertIsNone(data2["ticket_id"])
        attendee2_id = data2["attendee_id"]

        # 4. Check-in First Attendee with QR Token
        checkin_res = client.post("/registrations/verify-checkin", json={
            "qr_data": qr_token1,
            "event_id": event_id
        }, headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(checkin_res.status_code, 200)
        self.assertTrue(checkin_res.json()["success"])

        # Prevent duplicate check-in
        dup_checkin = client.post("/registrations/verify-checkin", json={
            "ticket_id": ticket1_id,
            "event_id": event_id
        }, headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(dup_checkin.status_code, 400)

        # 5. Cancel First Registration -> Should Trigger Auto-Promotion of Waitlisted Attendee
        cancel_res = client.delete(
            f"/registrations/{attendee1_id}",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(cancel_res.status_code, 200)
        self.assertTrue(cancel_res.json()["promoted_waitlist"]["promoted"])
        self.assertEqual(cancel_res.json()["promoted_waitlist"]["attendee_id"], attendee2_id)

        # Verify attendee 2 is now 'registered' and has an active ticket
        att2_status = client.get(f"/registrations/attendance/{event_id}")
        att2_data = [a for a in att2_status.json()["attendees"] if a["id"] == attendee2_id][0]
        self.assertEqual(att2_data["status"], "registered")
        self.assertIsNotNone(att2_data["ticket_id"])

    # ── 4. Analytics & Reports Tests ──────────────────────────────────────────

    def test_05_analytics_and_reports(self):
        summary_res = client.get("/analytics/summary?range=30", headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(summary_res.status_code, 200)
        data = summary_res.json()
        self.assertIn("total_events", data)
        self.assertIn("attendance_rate", data)
        self.assertIn("capacity_utilization", data)

        # Time series
        ts_res = client.get("/analytics/registrations-over-time?range=30", headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(ts_res.status_code, 200)

        # Category distribution
        cat_res = client.get("/analytics/category-distribution", headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(cat_res.status_code, 200)

        # CSV Export
        csv_res = client.get("/reports/export/events", headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(csv_res.status_code, 200)
        self.assertIn("text/csv", csv_res.headers["content-type"])
        self.assertIn("Event ID", csv_res.text)

    def test_06_priority2_analytics_and_reports(self):
        # Create a real event with registrations and a vendor assignment
        venue_res = client.post(
            "/venues/",
            json={"name": f"Analytics Hall {os.urandom(3).hex()}", "capacity": 200, "location": "North Block"},
            headers={"Authorization": f"Bearer {self.org_token}"},
        )
        self.assertEqual(venue_res.status_code, 201)
        venue_id = venue_res.json()["id"]

        event_res = client.post(
            "/events/",
            json={
                "name": "Priority 2 Analytics Demo Event",
                "event_type": "Conference",
                "date": "2026-12-10",
                "time": "10:00 AM",
                "budget": 150000,
                "status": "published",
                "venue_id": venue_id,
                "description": "Analytics validation event.",
                "capacity": 5,
                "category": "Technology",
                "visibility": "public",
            },
            headers={"Authorization": f"Bearer {self.org_token}"},
        )
        self.assertEqual(event_res.status_code, 201)
        event_id = event_res.json()["id"]

        reg_res = client.post(
            "/registrations/",
            json={
                "event_id": event_id,
                "name": "Priority Analytics User",
                "email": f"priority_{os.urandom(3).hex()}@test.com",
                "phone": "9087654321",
                "college": "Test College",
            },
        )
        self.assertEqual(reg_res.status_code, 201)

        vendor_res = client.post(
            "/vendors/",
            json={"name": "Priority Vendor", "service_type": "Catering", "contact": "9876543210"},
            headers={"Authorization": f"Bearer {self.org_token}"},
        )
        self.assertEqual(vendor_res.status_code, 201)
        vendor_id = vendor_res.json()["id"]

        assign_res = client.post(
            "/vendors/assign",
            json={"vendor_id": vendor_id, "event_id": event_id},
            headers={"Authorization": f"Bearer {self.org_token}"},
        )
        self.assertEqual(assign_res.status_code, 201)

        rating_res = client.post(
            f"/vendor-performance/{vendor_id}/performance?event_id={event_id}",
            json={
                "quality_rating": 5,
                "timeliness_rating": 4,
                "cost_rating": 4,
                "communication_rating": 5,
                "overall_rating": 4,
                "comments": "Strong performance",
            },
            headers={"Authorization": f"Bearer {self.org_token}"},
        )
        self.assertEqual(rating_res.status_code, 201)

        overview_res = client.get("/analytics/overview", headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(overview_res.status_code, 200)
        overview = overview_res.json()
        self.assertIn("kpis", overview)
        self.assertIn("total_events", overview["kpis"])

        attendance_res = client.get("/analytics/attendance", headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(attendance_res.status_code, 200)
        self.assertIn("attendance_rate", attendance_res.json())

        budget_res = client.get(f"/analytics/budget?event_id={event_id}", headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(budget_res.status_code, 200)
        self.assertIn("total_budget", budget_res.json())

        vendor_res = client.get("/analytics/vendors", headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(vendor_res.status_code, 200)
        self.assertIn("avg_overall_rating", vendor_res.json())

        resources_res = client.get("/analytics/resources", headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(resources_res.status_code, 200)
        self.assertIn("resource_utilization", resources_res.json())

        comparison_res = client.get(
            f"/analytics/event-comparison?event_ids={event_id}",
            headers={"Authorization": f"Bearer {self.org_token}"},
        )
        self.assertEqual(comparison_res.status_code, 200)
        self.assertIn("events", comparison_res.json())

        forecast_res = client.get("/analytics/forecast", headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(forecast_res.status_code, 200)
        self.assertIn("forecast", forecast_res.json())

        pdf_res = client.get(f"/reports/events/{event_id}/pdf", headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(pdf_res.status_code, 200)
        self.assertIn("application/pdf", pdf_res.headers["content-type"])

        csv_res = client.get(f"/reports/events/{event_id}/attendees/csv", headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(csv_res.status_code, 200)
        self.assertIn("text/csv", csv_res.headers["content-type"])


if __name__ == "__main__":
    unittest.main()
