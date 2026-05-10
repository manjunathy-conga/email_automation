import os
import time
import logging
from typing import Dict
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

logger = logging.getLogger(__name__)


class DashboardScreenshotCapture:
    def __init__(self, config: Dict):
        self.config = config
        self.wait_seconds = config["dashboard"].get("screenshot_wait_seconds", 5)
        self.output_dir = config["report"]["output_dir"]

    def _get_driver(self) -> webdriver.Chrome:
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)  # was: optioxns

    def _get_env_credentials(self, environment: str) -> Dict:
        """Get username/password for the given environment."""
        for env in self.config["environments"]:
            if env["name"] == environment:
                return {"url": env["url"], "username": env["username"], "password": env["password"]}
        raise ValueError(f"Environment '{environment}' not found.")

    def _login_grafana(self, driver, url, username, password):
        login_url = url.rstrip("/") + "/login"
        logger.info("Logging into Grafana: %s", login_url)
        driver.get(login_url)

        wait = WebDriverWait(driver, 20)

        # Username field — Grafana uses placeholder "email or username"
        user_input = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "input[placeholder='email or username'], input[name='user']")
        ))
        user_input.clear()
        user_input.send_keys(username)

        # Password field
        pass_input = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "input[placeholder='password'], input[name='password'], input[type='password']")
        ))
        pass_input.clear()
        pass_input.send_keys(password)

        # "Log in" button — Grafana button may not have type='submit'
        submit_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[normalize-space()='Log in'] | //button[@type='submit']")
        ))
        submit_btn.click()

        # Wait until redirected away from login page
        wait.until(EC.url_changes(login_url))
        logger.info("Grafana login successful for URL: %s", url)
        time.sleep(2)

    def capture(self, tenant: Dict, env_url: str) -> str:
        """Login to Grafana, navigate to tenant dashboard, capture screenshot."""
        driver = self._get_driver()
        try:
            creds = self._get_env_credentials(tenant["environment"])

            # Step 1 — Login
            self._login_grafana(driver, creds["url"], creds["username"], creds["password"])

            # Step 2 — Navigate to tenant dashboard
            dashboard_url = f"{creds['url']}{tenant['dashboard_path']}"
            logger.info(f"Navigating to dashboard: {dashboard_url}")
            driver.get(dashboard_url)

            # Step 3 — Wait for Grafana panels to render
            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".panel-container"))
                )
            except TimeoutException:
                logger.warning("Panels not detected, using time-based wait.")

            time.sleep(self.wait_seconds)

            # Step 4 — Save screenshot
            os.makedirs(self.output_dir, exist_ok=True)
            env_tag = tenant["environment"].replace(" ", "_")
            screenshot_path = os.path.join(
                self.output_dir,
                f"{tenant['id']}_{env_tag}_dashboard.png"
            )
            driver.save_screenshot(screenshot_path)
            logger.info(f"Screenshot saved: {screenshot_path}")
            return screenshot_path

        except Exception as e:
            logger.error(f"Screenshot failed for {tenant['id']}: {e}")
            raise
        finally:
            driver.quit()