import json
import logging
import os
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)


class SystemConfigLoader:
    """Simple loader for *config/system_config.json* and helper accessors.

    The existing codebase only needs a handful of getters.  We implement those so
    that the rest of the system keeps working without any further refactor.
    """

    def __init__(self, config_path: str | None = None):
        self.config_path = config_path or os.path.join("config", "system_config.json")
        self._config: Dict[str, Any] = {}
        self._load()

    # ---------------------------------------------------------------------
    # public helpers
    # ---------------------------------------------------------------------
    def get_system_config(self) -> Dict[str, Any]:
        return self._config.get("system", self._config)

    def get_amazon_config(self) -> Dict[str, Any]:
        return self._config.get("amazon", {})

    def get_supplier_config(self, supplier_name: str) -> Dict[str, Any]:
        suppliers = self._config.get("suppliers", {})
        return suppliers.get(supplier_name, {})

    def get_credentials(self, supplier_name: str) -> Dict[str, str]:
        return self._config.get("credentials", {}).get(supplier_name, {})

    def get_workflow_config(self, workflow_key: str) -> Dict[str, Any]:
        return self._config.get("workflows", {}).get(workflow_key, {})

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _load(self) -> None:
        if not os.path.exists(self.config_path):
            log.error("System config JSON not found at %s", self.config_path)
            self._config = {}
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as fh:
                self._config = json.load(fh)
        except Exception as exc:
            log.exception("Failed to parse system config JSON: %s", exc)
            self._config = {} 