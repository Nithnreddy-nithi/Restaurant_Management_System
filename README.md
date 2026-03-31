# 🍽️ Restaurant Management System

A production-ready **Django REST Framework** backend with stateless JWT authentication, role-based access control, and a modular app architecture.

---

## 📁 Project Structure

```
Restaurant_Management_System/
├── manage.py
├── requirements.txt
├── .env.example
├── restaurant_management/
│   ├── __init__.py
│   ├── asgi.py
│   ├── wsgi.py
│   ├── urls.py
│   └── settings/
│       ├── __init__.py
│       ├── base.py          # Shared settings
│       └── development.py   # Dev overrides (SQLite, DEBUG=True)
└── apps/
    └── users/
        ├── migrations/
        ├── tests/
        │   └── test_auth.py  # 24 automated tests
        ├── __init__.py
        ├── apps.py
        ├── models.py         # CustomUser + AuditLog
        ├── serializers.py    # Registration, login, profile, logout
        ├── views.py          # Register, Login, Logout, Refresh, Profile
        ├── urls.py
        ├── permissions.py    # RBAC: IsAdminRole, IsOwnerOrAdmin, etc.
        ├── throttles.py      # Login rate limit: 5/min
        ├── signals.py        # Audit log on login/logout
        ├── admin.py
        └── utils.py          # Custom exception handler, token helper
```

---

## ⚡ Quick Start

### 1. Create and activate a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
copy .env.example .env   # Windows
cp .env.example .env     # macOS/Linux
# Edit .env and set your SECRET_KEY
```

### 4. Run migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create a superuser (Admin)

```bash
python manage.py createsuperuser
```

### 6. Start the development server

```bash
python manage.py runserver
```

---

## 🔑 API Endpoints

Base URL: `http://127.0.0.1:8000/api/users/`

| Method | Endpoint              | Auth Required | Description                    |
|--------|-----------------------|:-------------:|--------------------------------|
| POST   | `register/`           | ❌            | Create new user account        |
| POST   | `login/`              | ❌            | Login → returns JWT pair       |
| POST   | `logout/`             | ✅            | Blacklist refresh token        |
| POST   | `token/refresh/`      | ❌            | Rotate and get new access token|
| GET    | `profile/`            | ✅            | Get own profile                |
| PATCH  | `profile/`            | ✅            | Update own profile             |
| POST   | `change-password/`    | ✅            | Change password                |
| GET    | `` (root)             | ✅ Admin only | List all users                 |
| GET    | `<uuid>/`             | ✅ Admin only | Get specific user              |
| PATCH  | `<uuid>/`             | ✅ Admin only | Update user role/status        |
| DELETE | `<uuid>/`             | ✅ Admin only | Deactivate user (soft delete)  |

---

## 📋 Request / Response Examples

### Register
```http
POST /api/users/register/
Content-Type: application/json

{
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1234567890",
  "role": "Waiter",
  "password": "StrongPass@1",
  "password_confirm": "StrongPass@1"
}
```
**Response 201:**
```json
{
  "success": true,
  "message": "Account created successfully.",
  "user": { "id": "...", "email": "john@example.com", "role": "Waiter" },
  "access": "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>"
}
```

### Login
```http
POST /api/users/login/
Content-Type: application/json

{ "email": "john@example.com", "password": "StrongPass@1" }
```
**Response 200:**
```json
{
  "success": true,
  "message": "Login successful.",
  "user": { ... },
  "access": "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>"
}
```

### Authenticated Request
```http
GET /api/users/profile/
Authorization: Bearer <jwt_access_token>
```

### Logout
```http
POST /api/users/logout/
Authorization: Bearer <jwt_access_token>
Content-Type: application/json

{ "refresh": "<jwt_refresh_token>" }
```
**Response 205** — Token is blacklisted.

---

## 👥 Roles

| Role    | Description              |
|---------|--------------------------|
| Admin   | Full access to all APIs  |
| Waiter  | Standard staff access    |
| Chef    | Standard staff access    |
| Cashier | Standard staff access    |

---

## 🔒 Security Features

| Feature                | Implementation                                  |
|------------------------|-------------------------------------------------|
| JWT Auth               | `djangorestframework-simplejwt`                 |
| Token Refresh Rotation  | `ROTATE_REFRESH_TOKENS = True`                 |
| Token Blacklist        | `rest_framework_simplejwt.token_blacklist`      |
| Password Hashing       | Django's `PBKDF2PasswordHasher`                 |
| Password Strength      | Regex: uppercase + lowercase + digit + special  |
| Rate Limiting          | 5 login attempts/min per IP                     |
| Audit Logging          | `AuditLog` model for login/logout/register      |
| RBAC                   | Custom permission classes per role              |
| Soft Delete            | Users deactivated, never hard deleted           |

---

## 🧪 Running Tests

```bash
python manage.py test apps.users.tests --verbosity=2
```

Runs 24 tests covering:
- Registration (success, duplicate email, weak password, mismatch)
- Login (success, wrong password, inactive user)
- Token refresh (valid, invalid token)
- Logout (blacklist verification)
- Profile (get, patch, role protection)
- Change password (success, wrong old, weak new)
- Admin RBAC (list users, deactivate, 403 for non-admin)

---

## 🌐 Django Admin

Access at `http://127.0.0.1:8000/admin/`
- View and manage all users
- Browse immutable audit logs
- Assign/change roles
