# DRDO Training Portal — Prototype

A training request and management portal for DRDO employees, built with Flask + MySQL + Bootstrap.  
This is a standalone prototype to be later integrated with the main DRDO Internship Portal.

---

## Features

**Employee**
- Browse and register for listed trainings
- Request a custom training topic
- View training records with auto-updated status
- Submit feedback after training ends

**HR**
- Create and list trainings with date-driven status
- Review employee requests — approve (auto-lists) or reject
- View registered employees per training
- Forward employee list to concerned department via email

**Training Status (automatic, date-driven)**
| Status | Condition |
|---|---|
| Upcoming | Before registration opens |
| Registration | Between reg open and reg close dates |
| Ongoing | Between start and end dates |
| Need Feedback | After end date, feedback pending |
| Finished | After end date, feedback submitted |

---

## Tech Stack

- **Backend** — Python 3.8+, Flask
- **Database** — MySQL
- **Frontend** — Bootstrap 5.3, Bootstrap Icons

---

## Project Structure

```
Training-Portal/
├── app.py               # Main Flask app, all routes
├── first_setup.py       # One-time setup script
├── schema.sql           # Database schema
├── static/
│   └── css/
│       └── style.css
└── templates/
    ├── base.html
    ├── _sidebar_links.html
    ├── login.html
    ├── register.html
    ├── employee/
    │   ├── dashboard.html
    │   ├── browse.html
    │   ├── my_training.html
    │   ├── request_training.html
    │   └── feedback.html
    └── hr/
        ├── dashboard.html
        ├── manage_training.html
        ├── create_training.html
        ├── requests.html
        └── registrations.html
```

---

## Setup Instructions

### 1. Prerequisites
- Python 3.8+
- MySQL running locally

### 2. Clone the repo
```bash
git clone https://github.com/ayushi-solani/Training-Portal.git
cd Training-Portal
```

### 3. Run setup
```bash
python first_setup.py
```
This will:
- Install all dependencies
- Ask for your MySQL credentials
- Create the database and tables
- Create demo accounts
- Patch `app.py` with your credentials

### 4. Run the app
```bash
python app.py
```

### 5. Open in browser
```
http://127.0.0.1:5000
```

---

## Demo Credentials

| Role | Email | Password |
|---|---|---|
| HR | hr@drdo.in | Hr@1234 |
| Employee | ayushi@drdo.in | Ayushi@1234 |
| Employee | raj@drdo.in | Raj@1234 |
| Employee | priya@drdo.in | Priya@1234 |

---

## Email Forwarding (optional)

To enable HR's "Forward Employee List" feature:

1. Open `app.py`
2. Set your Gmail credentials:
```python
SMTP_USER     = "your@gmail.com"
SMTP_PASSWORD = "your_app_password"
EMAIL_ENABLED = True
```
3. Use a Gmail App Password (not your regular password).  
   Generate one at: https://myaccount.google.com/apppasswords

> ⚠️ Never commit `app.py` with real credentials to Git.

---

## Notes

- `app.py` is patched by `first_setup.py` with your local DB credentials — do not commit it.
- Add `app.py` to `.gitignore` if working with real passwords.
- This portal will later be integrated with the DRDO Internship Portal (same Flask + MySQL stack).