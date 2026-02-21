# begin test_container_build.py

'''
Tier 1: Test that the grader Docker image builds successfully
and contains the expected files.
'''

import subprocess

import pytest


class TestContainerBuild:

    def test_image_builds(self, grader_image):
        """Grader image should build without errors."""
        assert grader_image == 'integration-test-grader:latest'

    def test_image_has_test_files(self, grader_image):
        """Grader image should contain test files in /tests/."""
        result = subprocess.run(
            ['docker', 'run', '--rm', grader_image,
             'python3', '-c',
             'import glob; files = glob.glob("/tests/test_*.py"); '
             'print(len(files)); assert files'],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f'Failed: {result.stderr}'

    def test_image_has_pytest(self, grader_image):
        """Grader image should have pytest installed."""
        result = subprocess.run(
            ['docker', 'run', '--rm', grader_image,
             'python3', '-c', 'import pytest; print(pytest.__version__)'],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f'Failed: {result.stderr}'
        assert result.stdout.strip(), 'pytest version should not be empty'

    def test_image_has_json_report_plugin(self, grader_image):
        """Grader image should have pytest-json-report installed."""
        result = subprocess.run(
            ['docker', 'run', '--rm', grader_image,
             'python3', '-c', 'import pytest_jsonreport; print("ok")'],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f'Failed: {result.stderr}'

    def test_image_has_ai_tutor(self, grader_image):
        """Grader image should have AI tutor code in /app/ai_tutor/."""
        result = subprocess.run(
            ['docker', 'run', '--rm', grader_image,
             'python3', '-c',
             'import pathlib; '
             'files = list(pathlib.Path("/app/ai_tutor").glob("*.py")); '
             'print(len(files)); assert files'],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f'Failed: {result.stderr}'

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


# end test_container_build.py
