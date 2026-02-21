# begin conftest.py

'''
Shared fixtures for integration tests.

Provides Docker image management, container execution,
and temporary workspace management.

Image source (checked in order):
  1. GRADER_IMAGE env var — use a pre-built image directly
  2. GRADER_IMAGE_BUILD env var — path to Dockerfile context to build from
  3. Sibling template dir — build from ../python-pytest-template/
  4. GHCR fallback — pull ghcr.io/kangwonlee/python-pytest-template:latest
'''

import json
import os
import pathlib
import shutil
import subprocess

import pytest


FIXTURES_DIR = pathlib.Path(__file__).parent / 'fixtures'
TEMPLATE_DIR = pathlib.Path(__file__).parent.parent / 'python-pytest-template'
LOCAL_BUILD_TAG = 'integration-test-grader:latest'
GHCR_FALLBACK = 'ghcr.io/kangwonlee/python-pytest-template:latest'


@pytest.fixture(scope='session')
def docker_available():
    """Check if Docker is available."""
    result = subprocess.run(
        ['docker', 'info'],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip('Docker is not available')
    return True


@pytest.fixture(scope='session')
def grader_image(docker_available):
    """
    Provide a grader Docker image for testing.

    Resolution order:
      1. GRADER_IMAGE env var (pre-built, e.g. from CI build step)
      2. GRADER_IMAGE_BUILD env var (path to Dockerfile context)
      3. Sibling python-pytest-template directory (local dev)
      4. GHCR fallback (pull from registry)
    """
    built_locally = False

    # 1. Explicit image from env
    env_image = os.environ.get('GRADER_IMAGE')
    if env_image:
        yield env_image
        return

    # 2. Explicit build path from env
    build_path = os.environ.get('GRADER_IMAGE_BUILD')
    if build_path:
        build_dir = pathlib.Path(build_path)
        if build_dir.exists():
            _docker_build(build_dir, LOCAL_BUILD_TAG)
            built_locally = True
            yield LOCAL_BUILD_TAG
            if built_locally:
                _docker_rmi(LOCAL_BUILD_TAG)
            return

    # 3. Sibling template directory
    if TEMPLATE_DIR.exists():
        _docker_build(TEMPLATE_DIR, LOCAL_BUILD_TAG)
        built_locally = True
        yield LOCAL_BUILD_TAG
        if built_locally:
            _docker_rmi(LOCAL_BUILD_TAG)
        return

    # 4. GHCR fallback
    _docker_pull(GHCR_FALLBACK)
    yield GHCR_FALLBACK


def _docker_build(context: pathlib.Path, tag: str) -> None:
    result = subprocess.run(
        ['docker', 'build', '-t', tag, '.'],
        cwd=context,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        pytest.fail(f'Docker build failed:\n{result.stderr}')


def _docker_pull(image: str) -> None:
    result = subprocess.run(
        ['docker', 'pull', image],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        pytest.fail(f'Docker pull failed:\n{result.stderr}')


def _docker_rmi(image: str) -> None:
    subprocess.run(
        ['docker', 'rmi', image],
        capture_output=True,
        text=True,
    )


@pytest.fixture
def workspace(tmp_path):
    """Create a temporary workspace directory simulating student code."""
    workspace_dir = tmp_path / 'workspace'
    workspace_dir.mkdir()
    return workspace_dir


@pytest.fixture
def output_dir(tmp_path):
    """Create a temporary output directory for reports."""
    output = tmp_path / 'output'
    output.mkdir()
    return output


@pytest.fixture
def copy_fixture():
    """Copy a fixture file to a workspace as exercise.py."""
    def _copy(fixture_name: str, workspace: pathlib.Path):
        src = FIXTURES_DIR / fixture_name
        dst = workspace / 'exercise.py'
        shutil.copy2(src, dst)
        return dst
    return _copy


@pytest.fixture
def init_git_repo():
    """Initialize a git repo in the workspace with a commit."""
    def _init(workspace: pathlib.Path):
        subprocess.run(['git', 'init'], cwd=workspace, capture_output=True)
        subprocess.run(['git', 'add', '.'], cwd=workspace, capture_output=True)
        subprocess.run(
            ['git', 'commit', '-m', 'Add exercise solution'],
            cwd=workspace,
            capture_output=True,
            env={
                'GIT_AUTHOR_NAME': 'Test Student',
                'GIT_AUTHOR_EMAIL': 'student@test.com',
                'GIT_COMMITTER_NAME': 'Test Student',
                'GIT_COMMITTER_EMAIL': 'student@test.com',
                'HOME': str(workspace.parent),
                'PATH': '/usr/bin:/bin:/usr/local/bin',
            },
        )
    return _init


@pytest.fixture
def run_grader():
    """Run the grader container against student code."""
    def _run(
        image: str,
        workspace: pathlib.Path,
        output_dir: pathlib.Path,
        test_file: str,
        report_name: str,
        timeout: int = 30,
        extra_args: str = '',
    ) -> subprocess.CompletedProcess:
        cmd = [
            'docker', 'run', '--rm',
            '--user', '1001:1001',
            '--network', 'none',
            '-v', f'{workspace}:/app/workspace:ro',
            '-v', f'{output_dir}:/output',
            '-e', 'STUDENT_CODE_FOLDER=/app/workspace',
            '-e', 'GITHUB_WORKSPACE=/app/workspace',
            image,
            'python', '-m', 'pytest',
            f'/tests/{test_file}',
            '--json-report',
            '--json-report-indent=4',
            f'--json-report-file=/output/{report_name}',
            '-v',
            '--tb=short',
        ]

        if extra_args:
            cmd.extend(extra_args.split())

        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    return _run


@pytest.fixture
def read_report():
    """Read and parse a JSON report file."""
    def _read(output_dir: pathlib.Path, report_name: str) -> dict:
        report_path = output_dir / report_name
        if not report_path.exists():
            pytest.fail(f'Report not found: {report_path}')
        return json.loads(report_path.read_text())
    return _read


# end conftest.py
