import os
import time
import logging
from typing import Dict
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException

logger = logging.getLogger(__name__)


class DashboardScreenshotCapture:
    def __init__(self, config: Dict):
        self.config = config
        self.wait_seconds = config["dashboard"].get("screenshot_wait_seconds", 5)
        self.output_dir = config["report"]["output_dir"]

    def _get_driver(self) -> webdriver.Chrome:
        options = Options()

        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        # shorter viewport so mainly graph area is captured
        options.add_argument("--window-size=1920,620")

        options.binary_location = "/usr/bin/chromium"

        service = Service("/usr/bin/chromedriver")

        return webdriver.Chrome(service=service, options=options)

    def _get_env_credentials(self, environment: str) -> Dict:
        for env in self.config["environments"]:
            if env["name"] == environment:
                return {
                    "url": env["url"],
                    "username": env["username"],
                    "password": env["password"]
                }

        raise ValueError(f"Environment '{environment}' not found.")

    def _login_grafana(self, driver, url, username, password):
        login_url = url.rstrip("/") + "/login"
        logger.info("Logging into Grafana: %s", login_url)

        driver.get(login_url)

        wait = WebDriverWait(driver, 20)

        user_input = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[placeholder='email or username'], input[name='user']")
            )
        )
        user_input.clear()
        user_input.send_keys(username)

        pass_input = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[placeholder='password'], input[name='password'], input[type='password']")
            )
        )
        pass_input.clear()
        pass_input.send_keys(password)

        submit_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[normalize-space()='Log in'] | //button[@type='submit']")
            )
        )
        submit_btn.click()

        wait.until(EC.url_changes(login_url))

        logger.info("Grafana login successful for URL: %s", url)

        time.sleep(2)

    def capture(self, tenant: Dict, env_url: str) -> str:
        driver = self._get_driver()

        try:
            creds = self._get_env_credentials(tenant["environment"])

            self._login_grafana(
                driver,
                creds["url"],
                creds["username"],
                creds["password"]
            )

            dashboard_url = f"{creds['url']}{tenant['dashboard_path']}"
            logger.info("Navigating to dashboard: %s", dashboard_url)

            driver.get(dashboard_url)

            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".panel-container"))
                )
            except TimeoutException:
                logger.warning("Panels not detected, using fallback wait.")

            time.sleep(self.wait_seconds)

            # slight zoom so graph fits cleanly
            driver.execute_script("document.body.style.zoom='95%'")
            time.sleep(2)

            os.makedirs(self.output_dir, exist_ok=True)

            env_tag = tenant["environment"].replace(" ", "_")
            screenshot_path = os.path.join(
                self.output_dir,
                f"{tenant['id']}_{env_tag}_dashboard.png"
            )

            # viewport-only screenshot
            driver.save_screenshot(screenshot_path)

            logger.info("Screenshot saved: %s", screenshot_path)

            return screenshot_path

        except Exception as e:
            logger.error("Screenshot failed for %s: %s", tenant["id"], e)
            raise

        finally:
            driver.quit()
