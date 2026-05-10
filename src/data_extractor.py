import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

logger = logging.getLogger(__name__)


class TurboDataExtractor:
    def __init__(self, config: Dict):
        self.config = config
        self.auth_token = config["dashboard"]["auth_token"]
        self.lookback_hours = config["report"]["lookback_hours"]

    def get_tenant_metrics(self, tenant: Dict) -> Dict[str, Any]:
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}", "Content-Type": "application/json"}
            env_url = self._get_env_url(tenant["environment"])
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=self.lookback_hours)

            metrics = {
                "tenant_id": tenant["id"],
                "tenant_name": tenant["name"],
                "environment": tenant["environment"],
                "report_generated_at": end_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "lookback_period": f"Last {self.lookback_hours} hours",
                "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            }

            metrics["active_carts"] = self._fetch_active_carts(env_url, tenant["id"], headers)
            metrics["lookback_data"] = self._fetch_lookback_data(env_url, tenant["id"], start_time, end_time, headers)
            metrics["performance"] = self._fetch_performance_metrics(env_url, tenant["id"], headers)

            logger.info(f"Metrics extracted for tenant: {tenant['id']}")
            return metrics
        except Exception as e:
            logger.error(f"Failed to extract metrics for {tenant['id']}: {e}")
            raise

    def _fetch_active_carts(self, base_url, tenant_id, headers):
        try:
            r = requests.get(f"{base_url}/api/v1/tenants/{tenant_id}/carts/active", headers=headers, timeout=30)
            r.raise_for_status()
            d = r.json()
            return {"total": d.get("totalActiveCarts", 0), "in_progress": d.get("inProgress", 0),
                    "pending_approval": d.get("pendingApproval", 0), "expired": d.get("expired", 0)}
        except Exception as e:
            logger.warning(f"Could not fetch active carts for {tenant_id}: {e}")
            return {"total": "N/A", "in_progress": "N/A", "pending_approval": "N/A", "expired": "N/A"}

    def _fetch_lookback_data(self, base_url, tenant_id, start, end, headers):
        try:
            params = {"startTime": start.isoformat(), "endTime": end.isoformat(), "tenantId": tenant_id}
            r = requests.get(f"{base_url}/api/v1/turbo/performance/lookback", headers=headers, params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning(f"Could not fetch lookback data for {tenant_id}: {e}")
            return {}

    def _fetch_performance_metrics(self, base_url, tenant_id, headers):
        try:
            r = requests.get(f"{base_url}/api/v1/turbo/performance/summary/{tenant_id}", headers=headers, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning(f"Could not fetch performance metrics for {tenant_id}: {e}")
            return {}

    def _get_env_url(self, env_name):
        for env in self.config["environments"]:
            if env["name"] == env_name:
                return env["url"]
        raise ValueError(f"Environment '{env_name}' not found in config.")
