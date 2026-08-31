from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from database import init_db
from routes import (
    auth,
    events,
    venues,
    resources,
    reports,
    registrations,
    vendors,
    analytics,
    notifications,
    budgets,
    expenses,
    sponsors,
    approvals,
    reminders,
    vendor_performance,
)

app = FastAPI(
    title="EventSphere API",
    description="Enterprise Event Registration & Management Platform API",
    version="2.5.0",
)

# ── CORS Middleware ───────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4000",
        "http://127.0.0.1:4000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global Security & Error Headers Middleware ────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


# ── Exception Handlers ────────────────────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err["loc"] if l != "body")
        errors.append(f"{loc}: {err['msg']}" if loc else err["msg"])
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "; ".join(errors) or "Validation error in request payload."},
    )


# ── Initialize Database ───────────────────────────────────────────────────────
init_db()

# ── Include Routers ───────────────────────────────────────────────────────────
app.include_router(auth.router,          prefix="/auth",          tags=["Authentication & Users"])
app.include_router(events.router,        prefix="/events",        tags=["Events"])
app.include_router(registrations.router, prefix="/registrations", tags=["Registrations & Check-In"])
app.include_router(analytics.router,     prefix="/analytics",     tags=["Analytics"])
app.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
app.include_router(reports.router,       prefix="/reports",       tags=["Reports & Exports"])
app.include_router(venues.router,        prefix="/venues",        tags=["Venues"])
app.include_router(resources.router,     prefix="/resources",     tags=["Resources"])
app.include_router(vendors.router,       prefix="/vendors",       tags=["Vendors"])
app.include_router(budgets.router,       prefix="/budgets",       tags=["Budget Management"])
app.include_router(expenses.router,      prefix="/expenses",      tags=["Expense Tracking"])
app.include_router(sponsors.router,      prefix="/sponsors",      tags=["Sponsorship Management"])
app.include_router(approvals.router,     prefix="/approvals",     tags=["Approval Workflow"])
app.include_router(reminders.router,     prefix="/reminders",     tags=["Event Reminders"])
app.include_router(vendor_performance.router, prefix="/vendor-performance", tags=["Vendor Performance Ratings"])

@app.get("/")
def root():
    return {
        "app": "EventSphere Platform API",
        "version": "2.5.0",
        "status": "operational",
        "docs": "/docs",
    }
