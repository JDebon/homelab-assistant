import os
import sys
from pathlib import Path

# Set test environment variables BEFORE importing any application modules.
# pydantic-settings reads these when Settings() is instantiated.
os.environ["API_KEY"] = "test-api-key"
os.environ["GROQ_API_KEY"] = "test-groq-key"
os.environ["OPENAI_API_KEY"] = "test-openai-key"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["ORCHESTRATOR_URL"] = "http://test-orchestrator:8001"
os.environ["LLM_ADAPTER_URL"] = "http://test-llm-adapter:8002"
os.environ["MONITORING_URL"] = "http://test-monitoring:8003"
os.environ["AUDIT_LOG_PATH"] = "/tmp/test-audit.jsonl"
os.environ["DB_PATH"] = ":memory:"

# Add each app's source directory to sys.path so packages are importable.
_APPS_DIR = Path(__file__).parent.parent / "apps"
for _app_dir in ["gateway", "orchestrator", "llm_adapter", "tool_monitoring"]:
    sys.path.insert(0, str(_APPS_DIR / _app_dir))

# Clear the LRU cache so Settings() re-reads the env vars set above.
from homelab_common.config import get_settings

get_settings.cache_clear()
