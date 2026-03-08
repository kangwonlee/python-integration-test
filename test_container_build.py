# begin test_container_build.py

'''
Tier 1: Test that the grader Docker image builds successfully
and contains the expected files.
'''

import subprocess

import pytest


# ── Required files inside the container ──────────────────────────

# Each grader test file that must be present in /tests/
REQUIRED_TEST_FILES = [
    'conftest.py',
    'test_syntax.py',
    'test_style.py',
    'test_results.py',
]

# AI tutor Python modules in /app/ai_tutor/
REQUIRED_TUTOR_FILES = [
    'entrypoint.py',
    'llm_client.py',
    'llm_configs.py',
    'prompt.py',
]

# Python packages that must be importable
REQUIRED_PACKAGES = [
    ('pytest', 'pytest'),
    ('pytest-json-report', 'pytest_jsonreport'),
    ('pytest-xdist', 'xdist'),
    ('requests', 'requests'),
]


class TestContainerBuild:

    def test_image_builds(self, grader_image):
        """Grader image should build without errors."""
        assert grader_image == 'integration-test-grader:latest'

    def test_image_runs_as_nonroot(self, grader_image):
        """Grader container should run as non-root user."""
        result = subprocess.run(
            ['docker', 'run', '--rm', grader_image, 'whoami'],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert result.stdout.strip() != 'root'

    def test_image_python_version(self, grader_image):
        """Container Python version should be 3.11.x."""
        result = subprocess.run(
            ['docker', 'run', '--rm', grader_image,
             'python3', '-c', 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f'Failed: {result.stderr}'
        assert result.stdout.strip() == '3.11', f'Expected Python 3.11, got {result.stdout.strip()}'


class TestRequiredTestFiles:
    """Verify that all grader test files exist in /tests/."""

    @pytest.mark.parametrize('filename', REQUIRED_TEST_FILES)
    def test_test_file_exists(self, grader_image, filename):
        """Each required test file must exist in /tests/."""
        result = subprocess.run(
            ['docker', 'run', '--rm', grader_image,
             'python3', '-c',
             f'import pathlib; p = pathlib.Path("/tests/{filename}"); '
             f'assert p.exists(), f"{{p}} not found"'],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f'/tests/{filename} missing: {result.stderr}'


class TestRequiredTutorFiles:
    """Verify that AI tutor files and locale data exist in /app/ai_tutor/."""

    @pytest.mark.parametrize('filename', REQUIRED_TUTOR_FILES)
    def test_tutor_file_exists(self, grader_image, filename):
        """Each required AI tutor module must exist."""
        result = subprocess.run(
            ['docker', 'run', '--rm', grader_image,
             'python3', '-c',
             f'import pathlib; p = pathlib.Path("/app/ai_tutor/{filename}"); '
             f'assert p.exists(), f"{{p}} not found"'],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f'/app/ai_tutor/{filename} missing: {result.stderr}'

    def test_tutor_has_locale_dir(self, grader_image):
        """AI tutor locale directory must exist with language files."""
        result = subprocess.run(
            ['docker', 'run', '--rm', grader_image,
             'python3', '-c',
             'import pathlib; '
             'locale = pathlib.Path("/app/ai_tutor/locale"); '
             'assert locale.is_dir(), "locale dir missing"; '
             'jsons = list(locale.glob("*.json")); '
             'assert jsons, "no locale .json files"; '
             'print(len(jsons))'],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f'locale check failed: {result.stderr}'

    def test_tutor_entrypoint_imports(self, grader_image):
        """AI tutor entrypoint.py should import without errors."""
        result = subprocess.run(
            ['docker', 'run', '--rm', grader_image,
             'python3', '-c',
             'import sys; sys.path.insert(0, "/app/ai_tutor"); '
             'import entrypoint; print("ok")'],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f'entrypoint import failed: {result.stderr}'


class TestRequiredPackages:
    """Verify that all Python packages from pyproject.toml are installed."""

    @pytest.mark.parametrize('pkg_name,import_name', REQUIRED_PACKAGES)
    def test_package_importable(self, grader_image, pkg_name, import_name):
        """Each required Python package must be importable."""
        result = subprocess.run(
            ['docker', 'run', '--rm', grader_image,
             'python3', '-c', f'import {import_name}; print("ok")'],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f'{pkg_name} ({import_name}) not installed: {result.stderr}'


# end test_container_build.py
