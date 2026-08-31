import os
import sys
import unittest
import concurrent.futures
from fastapi.testclient import TestClient

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from main import app
from database import init_db, get_db

client = TestClient(app)


class TestEnterpriseFeatures(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        # Register fresh test admin, organizer, and participant
        admin_email = f"admin_{os.urandom(4).hex()}@test.com"
        org_email = f"org_{os.urandom(4).hex()}@test.com"
        user_email = f"user_{os.urandom(4).hex()}@test.com"

        res_admin = client.post("/auth/register", json={
            "name": "Super Admin",
            "email": admin_email,
            "password": "adminpassword123",
            "role": "admin",
            "phone": "9998887770",
            "organization": "Admin HQ"
        })
        self.assertEqual(res_admin.status_code, 201)
        self.admin_token = res_admin.json()["token"]
        self.admin_user = res_admin.json()["user"]

        res_org = client.post("/auth/register", json={
            "name": "Soundarya Organizer",
            "email": org_email,
            "password": "orgpassword123",
            "role": "organizer",
            "phone": "9887766554",
            "organization": "Event Org"
        })
        self.assertEqual(res_org.status_code, 201)
        self.org_token = res_org.json()["token"]
        self.org_user = res_org.json()["user"]

        res_user = client.post("/auth/register", json={
            "name": "Arul Participant",
            "email": user_email,
            "password": "userpassword123",
            "role": "participant",
            "phone": "9776655443",
            "organization": "Engineering College"
        })
        self.assertEqual(res_user.status_code, 201)
        self.user_token = res_user.json()["token"]
        self.user = res_user.json()["user"]

    # ──────────────────────────────────────────────────────────────────────────
    # Requirement 1: Explicit Event Lifecycle
    # ──────────────────────────────────────────────────────────────────────────
    def test_01_explicit_event_lifecycle(self):
        # 1. Create event in DRAFT status
        draft_res = client.post("/events/", json={
            "name": "Draft Tech Symposium 2026",
            "event_type": "Conference",
            "date": "2026-11-15",
            "time": "10:00",
            "end_time": "13:00",
            "budget": 25000,
            "status": "draft",
            "capacity": 50,
            "category": "Technology"
        }, headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(draft_res.status_code, 201)
        event_id = draft_res.json()["id"]
        self.assertEqual(draft_res.json()["status"], "draft")

        # 2. Cannot create event in invalid initial status (e.g. completed or ongoing)
        invalid_init = client.post("/events/", json={
            "name": "Invalid Status Event",
            "event_type": "Workshop",
            "date": "2026-11-15",
            "time": "10:00",
            "status": "completed",
            "capacity": 50,
        }, headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(invalid_init.status_code, 400)

        # 3. Participants cannot register for a DRAFT event
        reg_draft = client.post("/registrations/", json={
            "event_id": event_id,
            "name": "Eager Attendee",
            "email": "eager@test.com",
            "phone": "9990001112"
        })
        self.assertEqual(reg_draft.status_code, 400)
        self.assertIn("draft", reg_draft.json()["detail"].lower())

        # 4. Transition DRAFT -> PUBLISHED
        pub_res = client.put(f"/events/{event_id}", json={
            "name": "Draft Tech Symposium 2026",
            "event_type": "Conference",
            "date": "2026-11-15",
            "time": "10:00",
            "end_time": "13:00",
            "budget": 25000,
            "status": "published",
            "capacity": 50,
            "category": "Technology"
        }, headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(pub_res.status_code, 200)
        self.assertEqual(pub_res.json()["status"], "published")

        # 5. Now registrations are allowed
        reg_pub = client.post("/registrations/", json={
            "event_id": event_id,
            "name": "Eager Attendee",
            "email": "eager@test.com",
            "phone": "9990001112"
        })
        self.assertEqual(reg_pub.status_code, 201)
        self.assertEqual(reg_pub.json()["status"], "registered")

        # 6. Transition PUBLISHED -> ONGOING
        ongoing_res = client.put(f"/events/{event_id}", json={
            "name": "Draft Tech Symposium 2026",
            "event_type": "Conference",
            "date": "2026-11-15",
            "time": "10:00",
            "end_time": "13:00",
            "budget": 25000,
            "status": "ongoing",
            "capacity": 50,
            "category": "Technology"
        }, headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(ongoing_res.status_code, 200)
        self.assertEqual(ongoing_res.json()["status"], "ongoing")

        # 7. Transition ONGOING -> COMPLETED
        comp_res = client.put(f"/events/{event_id}", json={
            "name": "Draft Tech Symposium 2026",
            "event_type": "Conference",
            "date": "2026-11-15",
            "time": "10:00",
            "end_time": "13:00",
            "budget": 25000,
            "status": "completed",
            "capacity": 50,
            "category": "Technology"
        }, headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(comp_res.status_code, 200)
        self.assertEqual(comp_res.json()["status"], "completed")

        # 8. Editing a COMPLETED event is prevented (locked historical records)
        edit_comp = client.put(f"/events/{event_id}", json={
            "name": "Modified After Completed",
            "event_type": "Conference",
            "date": "2026-11-15",
            "time": "10:00",
            "status": "completed",
            "capacity": 100,
        }, headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(edit_comp.status_code, 400)
        self.assertIn("locked", edit_comp.json()["detail"].lower())

        # 9. Registering for COMPLETED event is prevented
        reg_comp = client.post("/registrations/", json={
            "event_id": event_id,
            "name": "Late Attendee",
            "email": "late@test.com",
            "phone": "9990001113"
        })
        self.assertEqual(reg_comp.status_code, 400)

    # ──────────────────────────────────────────────────────────────────────────
    # Requirement 2: Registration Validation Pipeline
    # ──────────────────────────────────────────────────────────────────────────
    def test_02_registration_validation_pipeline(self):
        # 1. Registration Deadline enforcement
        past_event_res = client.post("/events/", json={
            "name": "Expired Deadline Event",
            "event_type": "Workshop",
            "date": "2026-12-01",
            "time": "09:00",
            "status": "published",
            "capacity": 50,
            "registration_deadline": "2020-01-01", # Past deadline
        }, headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(past_event_res.status_code, 201)
        past_eid = past_event_res.json()["id"]

        expired_reg = client.post("/registrations/", json={
            "event_id": past_eid,
            "name": "Deadline Attendee",
            "email": "deadline@test.com",
            "phone": "8887776665"
        })
        self.assertEqual(expired_reg.status_code, 400)
        self.assertIn("deadline", expired_reg.json()["detail"].lower())

        # 2. Duplicate Registration Prevention
        active_event_res = client.post("/events/", json={
            "name": "Active Duplicate Test Event",
            "event_type": "Workshop",
            "date": "2026-12-01",
            "time": "09:00",
            "status": "published",
            "capacity": 50,
            "registration_deadline": "2026-11-30",
        }, headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(active_event_res.status_code, 201)
        active_eid = active_event_res.json()["id"]

        # First registration -> 201
        reg1 = client.post("/registrations/", json={
            "event_id": active_eid,
            "name": "Arul Tester",
            "email": "arul.dup@test.com",
            "phone": "9998887771"
        })
        self.assertEqual(reg1.status_code, 201)

        # Second registration with same email -> 400 (Duplicate)
        reg2 = client.post("/registrations/", json={
            "event_id": active_eid,
            "name": "Arul Again",
            "email": "arul.dup@test.com",
            "phone": "9998887771"
        })
        self.assertEqual(reg2.status_code, 400)
        self.assertIn("already", reg2.json()["detail"].lower())

        # Authenticated user duplicate check
        reg_auth1 = client.post("/registrations/", json={
            "event_id": active_eid,
            "name": self.user["name"],
            "email": self.user["email"],
            "phone": self.user["phone"]
        }, headers={"Authorization": f"Bearer {self.user_token}"})
        self.assertEqual(reg_auth1.status_code, 201)

        reg_auth2 = client.post("/registrations/", json={
            "event_id": active_eid,
            "name": self.user["name"],
            "email": "different_email@test.com",
            "phone": self.user["phone"]
        }, headers={"Authorization": f"Bearer {self.user_token}"})
        self.assertEqual(reg_auth2.status_code, 400)
        self.assertIn("already", reg_auth2.json()["detail"].lower())

    # ──────────────────────────────────────────────────────────────────────────
    # Requirement 3: Concurrency-Safe Capacity Management
    # ──────────────────────────────────────────────────────────────────────────
    def test_03_concurrency_safe_capacity_management(self):
        # Create event with capacity = 1
        ev_res = client.post("/events/", json={
            "name": "High Concurrency Single Seat Keynote",
            "event_type": "Seminar",
            "date": "2026-12-15",
            "time": "14:00",
            "status": "published",
            "capacity": 1,
        }, headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(ev_res.status_code, 201)
        event_id = ev_res.json()["id"]

        # Run 5 serialized / race requests to fill seat and overflow to waitlist
        results = []
        for i in range(5):
            res = client.post("/registrations/", json={
                "event_id": event_id,
                "name": f"Candidate User {i}",
                "email": f"cand_{i}_{os.urandom(3).hex()}@test.com",
                "phone": f"900000000{i}"
            })
            results.append(res)

        status_codes = [r.status_code for r in results]
        self.assertTrue(all(code == 201 for code in status_codes))

        statuses = [r.json()["status"] for r in results]
        confirmed_count = sum(1 for s in statuses if s == "registered")
        waitlisted_count = sum(1 for s in statuses if s == "waitlisted")

        # EXACTLY 1 confirmed seat, EXACTLY 4 waitlisted! No overselling!
        self.assertEqual(confirmed_count, 1)
        self.assertEqual(waitlisted_count, 4)

        # Verify first registrant received valid Ticket ID and active ticket
        self.assertIsNotNone(results[0].json()["ticket_id"])
        self.assertIsNotNone(results[0].json()["qr_token"])

        # Verify waitlisted registrants received waitlist position numbers
        self.assertEqual(results[1].json()["waitlist_position"], 1)
        self.assertEqual(results[2].json()["waitlist_position"], 2)

        # Verify tickets in DB
        db = get_db()
        tickets = db.execute("SELECT * FROM tickets WHERE event_id = ? AND status = 'active'", (event_id,)).fetchall()
        db.close()
        self.assertEqual(len(tickets), 1)


    # ──────────────────────────────────────────────────────────────────────────
    # Requirement 4: Venue Conflict Detection
    # ──────────────────────────────────────────────────────────────────────────
    def test_04_venue_conflict_detection(self):
        # 1. Create a venue
        v_res = client.post("/venues/", json={
            "name": f"Platinum Hall {os.urandom(3).hex()}",
            "capacity": 300,
            "location": "Central Campus, Block A"
        }, headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(v_res.status_code, 201)
        venue_id = v_res.json()["id"]

        # 2. Event A: 10:00 AM – 01:00 PM (10:00 - 13:00) on 2026-10-20
        evA_res = client.post("/events/", json={
            "name": "Morning AI Conference",
            "event_type": "Conference",
            "date": "2026-10-20",
            "time": "10:00",
            "end_time": "13:00",
            "venue_id": venue_id,
            "status": "published",
        }, headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(evA_res.status_code, 201)

        # 3. Event B: 11:00 AM – 02:00 PM (11:00 - 14:00) -> OVERLAPS Event A on same date & venue -> REJECT!
        evB_res = client.post("/events/", json={
            "name": "Conflicting Midday Workshop",
            "event_type": "Workshop",
            "date": "2026-10-20",
            "time": "11:00",
            "end_time": "14:00",
            "venue_id": venue_id,
            "status": "published",
        }, headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(evB_res.status_code, 400)
        self.assertIn("venue overlap", evB_res.json()["detail"].lower())

        # 4. Event C: 02:00 PM – 05:00 PM (14:00 - 17:00) -> SEQUENTIAL to Event A on same date -> ALLOWED!
        evC_res = client.post("/events/", json={
            "name": "Afternoon Robotics Demo",
            "event_type": "Workshop",
            "date": "2026-10-20",
            "time": "14:00",
            "end_time": "17:00",
            "venue_id": venue_id,
            "status": "published",
        }, headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(evC_res.status_code, 201)

        # 5. Event D: 10:00 AM – 01:00 PM on DIFFERENT DATE (2026-10-21) -> ALLOWED!
        evD_res = client.post("/events/", json={
            "name": "Next Day Keynote",
            "event_type": "Conference",
            "date": "2026-10-21",
            "time": "10:00",
            "end_time": "13:00",
            "venue_id": venue_id,
            "status": "published",
        }, headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(evD_res.status_code, 201)

    # ──────────────────────────────────────────────────────────────────────────
    # Requirement 5: Resource Conflict Detection
    # ──────────────────────────────────────────────────────────────────────────
    def test_05_resource_conflict_detection(self):
        # 1. Create single inventory resource (Quantity = 1)
        res_item = client.post("/resources/", json={
            "name": f"Holographic Display {os.urandom(3).hex()}",
            "quantity": 1
        }, headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res_item.status_code, 201)
        resource_id = res_item.json()["id"]

        # Create two events on same date: Event 1 (10:00-12:00), Event 2 (11:00-13:00 overlapping), Event 3 (14:00-16:00 sequential)
        ev1 = client.post("/events/", json={
            "name": "Resource Event 1", "event_type": "Workshop", "date": "2026-11-05", "time": "10:00", "end_time": "12:00", "status": "published"
        }, headers={"Authorization": f"Bearer {self.org_token}"}).json()["id"]

        ev2 = client.post("/events/", json={
            "name": "Resource Event 2 (Overlapping)", "event_type": "Workshop", "date": "2026-11-05", "time": "11:00", "end_time": "13:00", "status": "published"
        }, headers={"Authorization": f"Bearer {self.org_token}"}).json()["id"]

        ev3 = client.post("/events/", json={
            "name": "Resource Event 3 (Sequential)", "event_type": "Workshop", "date": "2026-11-05", "time": "14:00", "end_time": "16:00", "status": "published"
        }, headers={"Authorization": f"Bearer {self.org_token}"}).json()["id"]

        # Allocate to Event 1 -> 201
        alloc1 = client.post("/resources/allocate", json={
            "event_id": ev1, "resource_id": resource_id, "quantity_used": 1
        }, headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(alloc1.status_code, 201)

        # Allocate to Event 2 (overlapping time) -> 400 (Conflict: exceeds quantity of 1)
        alloc2 = client.post("/resources/allocate", json={
            "event_id": ev2, "resource_id": resource_id, "quantity_used": 1
        }, headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(alloc2.status_code, 400)
        self.assertIn("resource conflict", alloc2.json()["detail"].lower())

        # Allocate to Event 3 (sequential time slot) -> 201 (Allowed: reuse without overlap)
        alloc3 = client.post("/resources/allocate", json={
            "event_id": ev3, "resource_id": resource_id, "quantity_used": 1
        }, headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(alloc3.status_code, 201)

    # ──────────────────────────────────────────────────────────────────────────
    # Requirement 6: Strengthened Cancellation Flow
    # ──────────────────────────────────────────────────────────────────────────
    def test_06_strengthened_cancellation_flow(self):
        # 1. Flow A: Participant cancellation triggers auto-promotion with new ticket & QR
        ev_res = client.post("/events/", json={
            "name": "Waitlist Promotion Flow Event",
            "event_type": "Conference",
            "date": "2026-12-20",
            "time": "10:00",
            "status": "published",
            "capacity": 1,
        }, headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(ev_res.status_code, 201)
        eid = ev_res.json()["id"]

        reg1 = client.post("/registrations/", json={
            "event_id": eid, "name": "Primary Participant", "email": "primary@test.com", "phone": "1234567890"
        }).json()
        self.assertEqual(reg1["status"], "registered")
        att1_id = reg1["attendee_id"]

        reg2 = client.post("/registrations/", json={
            "event_id": eid, "name": "Waitlisted Participant", "email": "waitlisted.cand@test.com", "phone": "9876543210"
        }).json()
        self.assertEqual(reg2["status"], "waitlisted")
        att2_id = reg2["attendee_id"]

        # Cancel Primary Participant
        cancel_res = client.delete(f"/registrations/{att1_id}", headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(cancel_res.status_code, 200)
        self.assertTrue(cancel_res.json()["promoted_waitlist"]["promoted"])
        self.assertEqual(cancel_res.json()["promoted_waitlist"]["attendee_id"], att2_id)
        self.assertIsNotNone(cancel_res.json()["promoted_waitlist"]["ticket_id"])

        # 2. Flow B: Organizer cancels whole event
        event_to_cancel = client.post("/events/", json={
            "name": "Event To Be Cancelled",
            "event_type": "Summit",
            "date": "2026-12-22",
            "time": "11:00",
            "status": "published",
            "capacity": 10,
        }, headers={"Authorization": f"Bearer {self.org_token}"}).json()["id"]

        # Register attendees
        att_c1 = client.post("/registrations/", json={
            "event_id": event_to_cancel, "name": "Attendee One", "email": "att1@test.com", "phone": "1112223333"
        }).json()["attendee_id"]

        # Cancel the event
        cancel_event_res = client.put(f"/events/{event_to_cancel}", json={
            "name": "Event To Be Cancelled",
            "event_type": "Summit",
            "date": "2026-12-22",
            "time": "11:00",
            "status": "cancelled",
            "capacity": 10,
        }, headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(cancel_event_res.status_code, 200)
        self.assertEqual(cancel_event_res.json()["status"], "cancelled")

        # Verify attendee is cancelled and ticket is cancelled
        db = get_db()
        att_row = db.execute("SELECT status, cancelled_at FROM attendees WHERE id = ?", (att_c1,)).fetchone()
        tkt_row = db.execute("SELECT status FROM tickets WHERE attendee_id = ?", (att_c1,)).fetchone()
        db.close()
        self.assertEqual(att_row["status"], "cancelled")
        self.assertIsNotNone(att_row["cancelled_at"])
        self.assertEqual(tkt_row["status"], "cancelled")

    # ──────────────────────────────────────────────────────────────────────────
    # Requirement 7: Strengthened QR Check-In & Attendance Audit Trail
    # ──────────────────────────────────────────────────────────────────────────
    def test_07_qr_checkin_and_audit_trail(self):
        ev_res = client.post("/events/", json={
            "name": "QR Verification Masterclass",
            "event_type": "Workshop",
            "date": "2026-12-25",
            "time": "15:00",
            "status": "published",
            "capacity": 10,
        }, headers={"Authorization": f"Bearer {self.org_token}"})
        eid = ev_res.json()["id"]

        reg = client.post("/registrations/", json={
            "event_id": eid, "name": "Checkin Attendee", "email": "checkin.user@test.com", "phone": "9998881111"
        }).json()
        qr_token = reg["qr_token"]
        ticket_id = reg["ticket_id"]

        # 1. Invalid / Forged signature check
        fake_token = qr_token[:-4] + "ffff"
        bad_checkin = client.post("/registrations/verify-checkin", json={
            "qr_data": fake_token, "event_id": eid
        }, headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(bad_checkin.status_code, 400)
        self.assertIn("signature", bad_checkin.json()["detail"].lower())

        # 2. Valid check-in
        good_checkin = client.post("/registrations/verify-checkin", json={
            "qr_data": qr_token, "event_id": eid
        }, headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(good_checkin.status_code, 200)
        self.assertTrue(good_checkin.json()["success"])

        # 3. Duplicate check-in rejection
        dup_checkin = client.post("/registrations/verify-checkin", json={
            "ticket_id": ticket_id, "event_id": eid
        }, headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(dup_checkin.status_code, 400)
        self.assertIn("already checked in", dup_checkin.json()["detail"].lower())

        # 4. Checkin logs query
        logs_res = client.get(f"/registrations/checkins?event_id={eid}", headers={"Authorization": f"Bearer {self.org_token}"})
        self.assertEqual(logs_res.status_code, 200)
        logs = logs_res.json()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["ticket_id"], ticket_id)
        self.assertEqual(logs[0]["attendee_name"], "Checkin Attendee")
        self.assertEqual(logs[0]["staff_name"], self.org_user["name"])

    # ──────────────────────────────────────────────────────────────────────────
    # Requirement 8: Enterprise Admin Audit Logs
    # ──────────────────────────────────────────────────────────────────────────
    def test_08_enterprise_audit_logs(self):
        # 1. Admin updates a user's role
        role_res = client.put(f"/auth/users/{self.user['id']}/role", json={
            "role": "organizer"
        }, headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(role_res.status_code, 200)

        # 2. Admin updates user status
        status_res = client.put(f"/auth/users/{self.user['id']}/status", json={
            "status": "inactive"
        }, headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(status_res.status_code, 200)

        # 3. Query audit logs from /analytics/audit-logs
        audit_res = client.get("/analytics/audit-logs?object_type=user", headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(audit_res.status_code, 200)
        logs = audit_res.json()
        self.assertGreaterEqual(len(logs), 2)

        role_log = [l for l in logs if l["action"] == "user.role_change"][0]
        self.assertEqual(role_log["actor_name"], self.admin_user["name"])
        self.assertEqual(role_log["previous_value"], "participant")
        self.assertEqual(role_log["new_value"], "organizer")

        status_log = [l for l in logs if l["action"] == "user.status_change"][0]
        self.assertEqual(status_log["previous_value"], "active")
        self.assertEqual(status_log["new_value"], "inactive")


if __name__ == "__main__":
    unittest.main()
