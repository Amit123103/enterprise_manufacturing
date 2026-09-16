# Enterprise Manufacturing Management Application (Python / Django)

A comprehensive, production-ready Manufacturing Management System engineered in **Python 3.11+ / Django 5+** and Django REST Framework. The application features two strictly separated portals (`/admin-panel/` and `/user-panel/`), a multi-tiered hierarchy (**Super Admin $\rightarrow$ Admin $\rightarrow$ User**), an interactive 6-action Authority Matrix, an end-to-end 6-stage manufacturing workflow pipeline, non-conformance quality tracking, automated QR code tagging & scanning, engineering document versioning, and ReportLab PDF / openpyxl Excel reporting.

---

## Architecture & User Hierarchy

```
                          SUPER ADMIN
                               │
               ┌───────────────┴───────────────┐
               ↓                               ↓
          ADMINS (Scoped)                SYSTEM CONTROL
               │
        ┌──────┼──────┐
        ↓      ↓      ↓
      USERS  USERS  USERS (Operators / Inspectors)
        │
        ↓
  PRODUCT LOTS
        │
        ↓
     BENDING  ── (Tube Size, Thickness, Critical Dimension)
        ↓
     PRESSING
        ├── BLANKING      ── (DIM Report, Production Count)
        ├── FORMING
        ├── PEARLING
        └── RESTRICTING
        ↓
     WELDING
        ├── Stage 1       ── (Golden Sample Verification)
        ├── Stage 2
        ├── Stage 3
        ├── Stage 4
        └── Stage 5
        ↓
      PAINT   ── (CEO Sign-off + Production Control Sign-off)
        ↓
       PDI    ── (Pre-Dispatch Inspection Checklist & Sheet)
        ↓
    DISPATCH  ── (Strict Gatekeeper Clearance & Logistics Bill)
```

---

## Technology Stack

- **Backend**: Python 3.11+, Django 5.2, Django REST Framework, Django ORM, PostgreSQL (with automatic zero-config SQLite development fallback)
- **Frontend**: Django Templates, HTML5, Vanilla CSS3 (Custom Industrial Navy/Steel Blue design system), JavaScript, Chart.js 4.4
- **Security & RBAC**: Custom User Model (`accounts.User`), Granular Module-Action Authority Matrix (`can_view`, `can_create`, `can_edit`, `can_delete`, `can_approve`, `can_export`), Custom Middlewares & View Decorators
- **QR Code Engine**: Python `qrcode` with Pillow, High-Density payload format (`MFG-ID:...|PART:...|CUST:...`), Camera Scanner with fallback manual lookup
- **Reporting Engine**: ReportLab (High-resolution PDF generation with letterheads & tables), openpyxl (styled Excel exports), streaming CSV

---

## Dual Isolated Interfaces

1. **Admin Portal (`/admin-panel/`)**:
   - Executive Dashboard with KPI stat cards and Chart.js production distribution & quality clearance charts.
   - Super Admin exclusive Admin Provisioning and Authority Matrix customization.
   - User & Operator management with department and line bindings.
   - Production oversight, Quality assurance, Controlled documents, Audit logs, and System settings.

2. **Operator Portal (`/user-panel/`)**:
   - Dedicated shop floor interface for machine operators and inspectors.
   - Workstation queues for Bending, Pressing (Blanking, Forming, Pearling, Restricting), Welding (Stages 1-5), Paint, PDI, and Dispatch.
   - Integrated camera QR scanner for mobile shopfloor tablets and terminals.
   - View-only access to authorized SOPs and drawings.

---

## Quick Start & Development Commands

### 1. Create Virtual Environment
```powershell
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Seed Comprehensive Demo Data
Populates the database with Super Admin, Department Admins, Operators, Controlled Documents, and 7 realistic product lots in various workflow stages:
```bash
python manage.py seed_demo_data
```

### 5. Start Development Server
```bash
python manage.py runserver 0.0.0.0:8000
```
Visit: **`http://localhost:8000/`**

---

## Demo Credentials

All accounts are pre-seeded and ready for immediate evaluation:

| Role | Email Address | Password | Assigned Authority / Stage |
| :--- | :--- | :--- | :--- |
| **Super Admin** | `superadmin@example.com` | `SuperAdmin123!` | Full System & Admin Control Plane |
| **Production Admin** | `production.admin@example.com` | `AdminPass123!` | Production Admin Template (Fabrication) |
| **Quality Admin** | `quality.admin@example.com` | `AdminPass123!` | Quality Admin Template (PDI & Assurance) |
| **Dispatch Admin** | `dispatch.admin@example.com` | `AdminPass123!` | Dispatch Admin Template (Logistics) |
| **Bending Operator** | `bending.user@example.com` | `UserPass123!` | Stage 1: Bending Station |
| **Welding Operator** | `welding.user@example.com` | `UserPass123!` | Stage 3: Welding Stages 1-5 |
| **Paint Operator** | `paint.user@example.com` | `UserPass123!` | Stage 4: Paint & Surface Finish |
| **PDI Inspector** | `pdi.user@example.com` | `UserPass123!` | Stage 5: Pre-Dispatch Inspection |
| **Dispatch Operator** | `dispatch.user@example.com` | `UserPass123!` | Stage 6: Dispatch & Bill of Lading |

---

## Security & Architectural Constraints

1. **Admin Cannot Create Admin**:
   - Strictly enforced at 4 distinct layers: Django views (`@super_admin_required`), API endpoints, Middleware, and Form level.
   - Any attempt by a normal Admin or Operator to access `/admin-panel/admins/create/` returns a hard **403 Forbidden**.
2. **Dispatch Gatekeeper**:
   - A product cannot be dispatched if any preceding stage (Bending, Pressing, Welding, Paint, PDI) is incomplete or not approved.
   - Paint strictly requires **both** CEO and Production Control (PC) sign-offs.
   - Dispatch is hard-blocked if any unresolved quality rejections exist.
3. **Automated Quality Issue on Critical Failure**:
   - If an operator submits a `FAIL` on a critical dimension in Bending or Pressing, the application automatically sets the lot status to `REJECTED` and creates an open non-conformance rejection record in Quality Assurance.
4. **Immutable Audit Trail**:
   - Every administrative login, admin creation, status suspension, permission update, stage transition, and export is recorded in `apps.audit.AuditLog` with timestamp, user, and IP address.

---

## Running Automated Tests

A comprehensive test suite verifies RBAC, admin creation denial, panel isolation, workflow advancement, dispatch gatekeeping, and QR code generation:
```bash
python manage.py test tests
```
