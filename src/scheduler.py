import logging
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

logger = logging.getLogger(__name__)


def job_listener(event):
    if event.exception:
        logger.error(f"Job failed: {event.exception}")
    else:
        logger.info("Scheduled job completed successfully.")


def start_scheduler():
    from main import main, load_config
    config = load_config()
    cron_expr = config["report"]["schedule_cron"]
    parts = cron_expr.split()

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    scheduler.add_job(main, "cron", minute=parts[0], hour=parts[1],
                      day=parts[2], month=parts[3], day_of_week=parts[4],
                      id="turbo_report_job", max_instances=1, misfire_grace_time=600)

    logger.info(f"Scheduler started — cron: {cron_expr} (UTC)")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
    start_scheduler()
