"""
main.py  —  Turbo Performance Report — Entry Point
"""

import argparse
import logging
import os
import sys

import yaml
from dotenv import load_dotenv

from src.data_extractor import TurboDataExtractor
from src.email_sender import EmailSender
from src.report_generator import ReportGenerator
from src.screenshot_capture import DashboardScreenshotCapture

load_dotenv()

os.makedirs("outputs/reports", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("outputs/automation.log"),
    ],
)
logger = logging.getLogger(__name__)


# ─── Config helpers ─────────────────────────────────────────

def load_config() -> dict:
    with open("config/config.yaml") as f:
        config = yaml.safe_load(f)

    config["smtp"]["username"] = os.environ.get("SMTP_USERNAME", config["smtp"].get("username", ""))
    config["smtp"]["password"] = os.environ.get("SMTP_PASSWORD", config["smtp"].get("password", ""))
    config["dashboard"]["auth_token"] = os.environ.get("DASHBOARD_AUTH_TOKEN", "")

    env_overrides = {
        "Ring 3a":     {"url": "RING_3A_URL",     "username": "RING_3A_USER",     "password": "RING_3A_PASS"},
        "Ring 3-aws":  {"url": "RING_3_AWS_URL",  "username": "RING_3_AWS_USER",  "password": "RING_3_AWS_PASS"},
        "Ring 3b":     {"url": "RING_3B_URL",     "username": "RING_3B_USER",     "password": "RING_3B_PASS"},
    }

    for env in config["environments"]:
        mapping = env_overrides.get(env["name"], {})
        for key, env_var in mapping.items():
            val = os.environ.get(env_var)
            if val:
                env[key] = val

    return config


def load_tenants() -> list:
    with open("config/tenants.yaml") as f:
        return yaml.safe_load(f)["tenants"]


# ─── Args ───────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Turbo Performance Report Generator")
    p.add_argument("--tenant", metavar="ID")
    p.add_argument("--environment", metavar="ENV")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


# ─── Main ───────────────────────────────────────────────────

def main():
    args    = parse_args()
    config  = load_config()
    tenants = load_tenants()

    # Filters
    if args.tenant:
        tenants = [t for t in tenants if t["id"] == args.tenant]
        if not tenants:
            logger.error("No tenant found with id='%s'", args.tenant)
            sys.exit(1)

    elif args.environment:
        tenants = [t for t in tenants if t["environment"] == args.environment]
        if not tenants:
            logger.error("No tenants found for environment='%s'", args.environment)
            sys.exit(1)

    logger.info("Processing %d tenant(s) | dry_run=%s", len(tenants), args.dry_run)

    extractor     = TurboDataExtractor(config)
    screenshotter = DashboardScreenshotCapture(config)
    generator     = ReportGenerator(config)
    sender        = EmailSender(config)

    results = []
    all_recipients = set()

    ok = fail = 0

    for tenant in tenants:
        try:
            logger.info("▶ Processing: %s | %s", tenant["name"], tenant["environment"])

            metrics = extractor.get_tenant_metrics(tenant)

            env_url = next(
                e["url"] for e in config["environments"]
                if e["name"] == tenant["environment"]
            )

            screenshot_path = screenshotter.capture(tenant, env_url)
            report_path     = generator.generate_html_report(metrics, screenshot_path)

            # Collect for combined email
            results.append({
                "metrics": metrics,
                "screenshot_path": screenshot_path
            })

            # Collect recipients (deduplicated)
            for r in tenant.get("recipients", []):
                if r:
                    all_recipients.add(r)

            ok += 1
            logger.info("✅ Done: %s", tenant["name"])

        except Exception as exc:
            logger.error("❌ Failed for %s: %s", tenant["id"], exc, exc_info=True)
            fail += 1

    # ── Send ONE combined email ─────────────────────────────
    if not args.dry_run and results:
        logger.info("📧 Sending combined email to: %s", list(all_recipients))
        sender.send_combined_report(list(all_recipients), results)
    else:
        logger.info("DRY-RUN — skipping email")

    logger.info("\n📬 Done — ✅ %d succeeded | ❌ %d failed", ok, fail)

    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()