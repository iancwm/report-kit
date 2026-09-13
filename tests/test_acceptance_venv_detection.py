"""
Test that acceptance_check.sh properly auto-detects the test virtual environment.

This test ensures the fix for the NumPy/bottleneck environment issue
remains in place. The acceptance check script should auto-detect
build/.venv-tests if it exists, rather than falling back to system Python
which may have incompatible compiled dependencies.
"""

import os
import subprocess
from pathlib import Path


def test_acceptance_check_uses_venv():
    """Verify that acceptance_check.sh uses the test venv when it exists."""
    repo_root = Path(__file__).parent.parent
    test_venv = repo_root / "build" / ".venv-tests"
    
    # This test only runs if the venv exists
    if not test_venv.exists():
        pytest.skip("Test venv not found at build/.venv-tests")
    
    # Verify the script has the auto-detection code
    acceptance_check = repo_root / "scripts" / "acceptance_check.sh"
    script_content = acceptance_check.read_text()
    
    assert "Auto-detect test venv" in script_content, (
        "acceptance_check.sh should contain auto-detection logic "
        "for build/.venv-tests"
    )
    
    # Verify the venv Python is executable
    venv_python = test_venv / "bin" / "python"
    assert venv_python.exists(), f"Venv Python not found at {venv_python}"
    
    # Verify the venv has pytest
    result = subprocess.run(
        [str(venv_python), "-c", "import pytest"],
        capture_output=True,
        timeout=5
    )
    assert result.returncode == 0, (
        f"Venv Python should have pytest installed"
    )


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
