"""Compatibility command for the packaged ReportKit diagnostic gate."""
try:
    from reportkit.diagnostics import *  # type: ignore # noqa: F401,F403
    from reportkit.diagnostics import main
except ModuleNotFoundError:
    import importlib.util
    from pathlib import Path
    import sys

    _path = Path(__file__).resolve().parents[2] / "python_scripts" / "reportkit" / "diagnostics.py"
    _spec = importlib.util.spec_from_file_location("reportkit.diagnostics", _path)
    if not _spec or not _spec.loader:
        raise ImportError(f"unable to load {_path}")
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_spec.name] = _module
    _spec.loader.exec_module(_module)
    for _name in ("DEFAULT_UNDERFULL_BADNESS", "DIAGNOSTIC_TYPES", "LEGACY_TYPES", "inspect_log", "load_allowlist", "main"):
        globals()[_name] = getattr(_module, _name)


if __name__ == "__main__":
    raise SystemExit(main())
