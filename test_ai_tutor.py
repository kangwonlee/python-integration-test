# begin test_ai_tutor.py

'''
Tier 2: Test the AI tutor feedback generation.

These tests require at least one LLM API key to be set.
They are automatically skipped when no API keys are available.
'''

import os
import subprocess

import pytest


API_KEY_VARS = [
    'CLAUDE_API_KEY',
    'GOOGLE_API_KEY',
    'XAI_API_KEY',
    'NVIDIA_NIM_API_KEY',
    'PERPLEXITY_API_KEY',
]


def has_any_api_key() -> bool:
    """Check if any LLM API key is available."""
    return any(os.environ.get(var) for var in API_KEY_VARS)


requires_api_key = pytest.mark.skipif(
    not has_any_api_key(),
    reason='No LLM API key available (need one of: ' + ', '.join(API_KEY_VARS) + ')',
)


def get_api_key_env() -> list[str]:
    """Build Docker -e flags for available API keys."""
    env_flags = []
    for var in API_KEY_VARS:
        value = os.environ.get(var)
        if value:
            # Map to the INPUT_ format expected by the tutor
            input_var = f'INPUT_{var.replace("_", "-")}'
            env_flags.extend(['-e', f'{input_var}={value}'])
    model = os.environ.get('DEFAULT_MODEL', '')
    if model:
        env_flags.extend(['-e', f'INPUT_MODEL={model}'])
    return env_flags


@requires_api_key
class TestAITutor:
    """Test AI tutor feedback generation (requires API key)."""

    def test_tutor_generates_feedback_on_failure(
        self, grader_image, workspace, output_dir,
        copy_fixture, init_git_repo, run_grader, read_report,
    ):
        """AI tutor should generate feedback for failed tests."""
        # Step 1: Run grader to produce reports
        copy_fixture('exercise_fail_result.py', workspace)
        init_git_repo(workspace)

        run_grader(
            grader_image, workspace, output_dir,
            'test_syntax.py', 'report_syntax.json',
        )
        run_grader(
            grader_image, workspace, output_dir,
            'test_results.py', 'report_results.json',
        )

        # Step 2: Run AI tutor
        api_env = get_api_key_env()
        report_files = '/output/report_results.json,/output/report_syntax.json'
        student_files = '/app/workspace/exercise.py'

        cmd = [
            'docker', 'run', '--rm',
            '--user', '1001:1001',
            '-v', f'{workspace}:/app/workspace:ro',
            '-v', f'{output_dir}:/output',
            '-e', f'INPUT_REPORT-FILES={report_files}',
            '-e', f'INPUT_STUDENT-FILES={student_files}',
            '-e', 'INPUT_EXPLANATION-IN=English',
            '-e', 'GITHUB_REPOSITORY=test/integration-test',
        ] + api_env + [
            grader_image,
            'python3', '/app/ai_tutor/entrypoint.py',
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        # AI tutor should produce output (feedback)
        assert result.returncode == 0, f'AI tutor failed:\n{result.stderr}'
        assert len(result.stdout.strip()) > 0, 'AI tutor should produce feedback'

    def test_tutor_handles_all_pass(
        self, grader_image, workspace, output_dir,
        copy_fixture, init_git_repo, run_grader,
    ):
        """AI tutor should handle the case when all tests pass."""
        copy_fixture('exercise_pass.py', workspace)
        init_git_repo(workspace)

        run_grader(
            grader_image, workspace, output_dir,
            'test_syntax.py', 'report_syntax.json',
        )
        run_grader(
            grader_image, workspace, output_dir,
            'test_results.py', 'report_results.json',
        )

        api_env = get_api_key_env()
        report_files = '/output/report_results.json,/output/report_syntax.json'
        student_files = '/app/workspace/exercise.py'

        cmd = [
            'docker', 'run', '--rm',
            '--user', '1001:1001',
            '-v', f'{workspace}:/app/workspace:ro',
            '-v', f'{output_dir}:/output',
            '-e', f'INPUT_REPORT-FILES={report_files}',
            '-e', f'INPUT_STUDENT-FILES={student_files}',
            '-e', 'INPUT_EXPLANATION-IN=English',
            '-e', 'GITHUB_REPOSITORY=test/integration-test',
        ] + api_env + [
            grader_image,
            'python3', '/app/ai_tutor/entrypoint.py',
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        assert result.returncode == 0, f'AI tutor failed:\n{result.stderr}'


# end test_ai_tutor.py
