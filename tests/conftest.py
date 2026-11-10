import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Stub the integration package so its Home Assistant imports are skipped.
_package = types.ModuleType("custom_components.ragtech")
_package.__path__ = [str(ROOT / "custom_components" / "ragtech")]
sys.modules.setdefault("custom_components.ragtech", _package)
