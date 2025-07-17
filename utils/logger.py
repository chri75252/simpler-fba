import logging
import os
from datetime import datetime
from typing import Optional


def setup_logger(log_level: int = logging.DEBUG, logs_root: str = "logs") -> Optional[str]:
    """Initialise root logger that logs to console & rotating file.

    Returns
    -------
    Optional[str]
        Absolute path to the debug log file (if it could be created), otherwise None.
    """
    try:
        # Prepare log directory
        debug_dir = os.path.join(logs_root, "debug")
        os.makedirs(debug_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_log_file = os.path.abspath(os.path.join(debug_dir, f"run_custom_poundwholesale_{timestamp}.log"))

        # Clear any root handlers so we don't duplicate logs if this function is called twice
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        # Configure logging
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(debug_log_file, mode="w", encoding="utf-8"),
            ],
            force=True,
        )

        logging.getLogger(__name__).info("🔧 Logging initialised – log file: %s", debug_log_file)
        return debug_log_file
    except Exception as exc:  # pragma: no cover – shouldn't happen but we guard anyway
        print(f"❌ Failed to set up logging: {exc}")
        logging.basicConfig(level=logging.INFO)
        return None 