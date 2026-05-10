# Turbo Performance Report — Automation Pipeline

Auto-generates tenant-wise Grafana dashboard reports (screenshots + metrics) and emails them to target recipients. Runs on a **daily schedule** via Jenkins or GitLab CI, and can also be triggered manually for a specific tenant or environment.

---

## Architecture

```
Jenkins / GitLab CI / Cron
          │
          ▼
     main.py  ──► for each tenant:
          │
          ├─► DashboardScreenshotCapture   Selenium logs into Grafana, navigates to
          │                                the tenant dashboard, captures a PNG.
          │
          ├─► TurboDataExtractor           Calls Grafana HTTP API to pull active-cart
          │                                counts and 24-h lookback metrics.
          │
          ├─► ReportGenerator              Renders metrics + screenshot path into
          │                                an HTML report via Jinja2.
          │
          └─► EmailSender                  Sends the report email with the screenshot
                                           embedded inline (CID) + HTML as attachment.
```

---

## Quick Start — Local

```bash
# 1. Clone and set up virtualenv
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure secrets
cp .env.example .env
# Edit .env with real SMTP + Grafana credentials

# 3. Fill in dashboard UIDs in config/tenants.yaml
#    Replace every  REPLACE_*_UID  with the real Grafana dashboard UID.

# 4. Run all tenants
python main.py

# 5. Run a single tenant (e.g. IBM)
python main.py --tenant ibm

# 6. Dry-run (screenshots + reports, no email)
python main.py --dry-run
```

---

## Jenkins Pipeline Setup

### Prerequisites
- Jenkins with **Docker** agent support (or install Python + Chrome on the agent)
- Jenkins Credentials stored (type: *Secret text* unless noted):

| Credential ID       | Value                                      |
|---------------------|--------------------------------------------|
| `SMTP_USERNAME`     | SMTP login email                           |
| `SMTP_PASSWORD`     | SMTP password                              |
| `RING_3A_URL`       | `https://ring3a-admin-grafana.congacloud.com` |
| `RING_3A_USER`      | `ring3a`                                   |
| `RING_3A_PASS`      | `ring3a@123`                               |
| `RING_3_AWS_URL`    | `https://ring3-aws-admin-grafana.congacloud.com` |
| `RING_3_AWS_USER`   | `ring3-aws`                                |
| `RING_3_AWS_PASS`   | `ring3-aws@123`                            |
| `RING_3B_URL`       | `https://ring3b-admin-grafana.congacloud.com` |
| `RING_3B_USER`      | `ring3b`                                   |
| `RING_3B_PASS`      | `ring3b@123`                               |

### Create the Pipeline Job

1. **New Item → Pipeline**
2. Under *Pipeline* → *Definition*: choose **Pipeline script from SCM**
3. SCM: Git → your repo URL
4. Script Path: `Jenkinsfile`
5. Save → **Build Now** to test, or let the daily trigger run at 07:00 UTC.

### Manual Trigger (single tenant)

1. Open the job → **Build with Parameters**
2. Set `TENANT_ID` to e.g. `ibm`
3. Click **Build**

---

## GitLab CI Setup

1. Push this repo to GitLab.
2. Go to **Settings → CI/CD → Variables** and add the same credentials listed above.
3. Go to **CI/CD → Schedules → New schedule**:
   - Description: `Daily Turbo Reports`
   - Cron: `0 7 * * *`
   - Target branch: `main`
4. The pipeline will run automatically every day at 07:00 UTC.

---

## Adding / Updating a Tenant

Edit `config/tenants.yaml`. Each entry looks like:

```yaml
- id: "ibm"
  name: "IBM"
  environment: "Ring 3a"
  dashboard_path: "/d/<GRAFANA_UID>/dashboard-name?orgId=1&from=now-24h&to=now"
  recipients:
    - "devops@conga.com"
    - "another@conga.com"
```

To find the **Grafana UID** for a dashboard:
- Open the dashboard in Grafana
- The URL is: `https://<host>/d/<UID>/<slug>?...`
- Copy the `<UID>` segment and paste it into `dashboard_path`.

---

## Email Format

Each recipient receives:
- **Subject**: `[Turbo Report] IBM | Ring 3a | 2026-04-21 07:00:00 UTC`
- **Body**: Full HTML report with:
  - Tenant details (name, ID, environment, period)
  - Active cart metrics grid (Total, In Progress, Pending Approval, Expired)
  - **Grafana screenshot embedded inline** (visible directly in Outlook/Gmail)
  - 24-hour lookback JSON data
- **Attachments**:
  - `ibm_Ring_3a_dashboard.png` — screenshot
  - `ibm_turbo_report.html` — full HTML report

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `selenium.common.exceptions.WebDriverException: chromedriver not found` | Ensure `chromium-driver` is installed. Set `CHROMEDRIVER_PATH` env var. |
| Screenshot is blank / all white | Increase `screenshot_wait_seconds` in `config.yaml` (try 10–15 for slow dashboards). |
| `smtplib.SMTPAuthenticationError` | Verify `SMTP_USERNAME` / `SMTP_PASSWORD` env vars. For Office 365 you may need an App Password. |
| Email arrives but screenshot not shown inline | Ensure your email client isn't blocking external images. Screenshot is CID-embedded (no external URLs). |
| `No tenant found with id='...'` | Check the `id:` field in `config/tenants.yaml` — it's case-sensitive. |
| Grafana login fails | Confirm per-ring credentials; check if Grafana has changed the login form selector. |

---

## Project Structure

```
email_automation/
├── main.py                    Entry point (CLI args: --tenant, --environment, --dry-run)
├── Jenkinsfile                Jenkins declarative pipeline
├── .gitlab-ci.yml             GitLab CI pipeline (alternative)
├── Dockerfile                 Python + Chromium image
├── docker-compose.yml         Local dev / test
├── requirements.txt
├── .env.example               Template — copy to .env, never commit .env
├── config/
│   ├── config.yaml            SMTP, environments, report settings (no secrets)
│   └── tenants.yaml           Per-tenant dashboard paths and recipients
├── src/
│   ├── screenshot_capture.py  Selenium-based Grafana login + screenshot
│   ├── data_extractor.py      Grafana API metrics fetch
│   ├── report_generator.py    Jinja2 HTML report renderer
│   ├── email_sender.py        SMTP sender with inline CID screenshot
│   └── scheduler.py           Standalone APScheduler (alternative to CI)
├── templates/
│   └── report_template.html   Email/report HTML template
└── outputs/
    └── reports/               Generated PNGs and HTML reports
```
