# begin test_grading_pipeline.py

'''
Tier 1: Test the grading pipeline end-to-end.

Runs the grader container against sample student code
and validates that test results are correct.
'''

import pytest


class TestSyntaxCheck:
    """Test the syntax checking stage of the grading pipeline."""

    def test_pass_syntax(
        self, grader_image, workspace, output_dir,
        copy_fixture, init_git_repo, run_grader, read_report,
    ):
        """Passing code should pass syntax check."""
        copy_fixture('exercise_pass.py', workspace)
        init_git_repo(workspace)

        result = run_grader(
            grader_image, workspace, output_dir,
            'test_syntax.py', 'report_syntax.json',
        )

        report = read_report(output_dir, 'report_syntax.json')
        assert 'tests' in report
        assert 'summary' in report

        # Syntax check should pass for valid code
        passed = [t for t in report['tests'] if t['outcome'] == 'passed']
        assert len(passed) >= 1, f'Expected at least 1 passing test, got {len(passed)}'

    def test_fail_syntax(
        self, grader_image, workspace, output_dir,
        copy_fixture, init_git_repo, run_grader, read_report,
    ):
        """Code with syntax error should fail syntax check."""
        copy_fixture('exercise_fail_syntax.py', workspace)
        init_git_repo(workspace)

        run_grader(
            grader_image, workspace, output_dir,
            'test_syntax.py', 'report_syntax.json',
        )

        report = read_report(output_dir, 'report_syntax.json')
        failed = [t for t in report['tests'] if t['outcome'] == 'failed']
        assert len(failed) >= 1, 'Syntax error should be detected'


class TestStyleCheck:
    """Test the style checking stage of the grading pipeline."""

    def test_pass_style_git_commit(
        self, grader_image, workspace, output_dir,
        copy_fixture, init_git_repo, run_grader, read_report,
    ):
        """Code with proper git commit should pass style checks."""
        copy_fixture('exercise_pass.py', workspace)
        init_git_repo(workspace)

        run_grader(
            grader_image, workspace, output_dir,
            'test_style.py', 'report_style.json',
        )

        report = read_report(output_dir, 'report_style.json')
        assert 'tests' in report
        assert report['summary']['total'] > 0


class TestResultsCheck:
    """Test the results checking stage of the grading pipeline."""

    def test_pass_results(
        self, grader_image, workspace, output_dir,
        copy_fixture, init_git_repo, run_grader, read_report,
    ):
        """Correct code should pass result tests."""
        copy_fixture('exercise_pass.py', workspace)
        init_git_repo(workspace)

        result = run_grader(
            grader_image, workspace, output_dir,
            'test_results.py', 'report_results.json',
        )

        report = read_report(output_dir, 'report_results.json')
        assert 'tests' in report
        assert 'summary' in report

    def test_fail_wrong_output(
        self, grader_image, workspace, output_dir,
        copy_fixture, init_git_repo, run_grader, read_report,
    ):
        """Code with wrong output should fail result tests."""
        copy_fixture('exercise_fail_result.py', workspace)
        init_git_repo(workspace)

        run_grader(
            grader_image, workspace, output_dir,
            'test_results.py', 'report_results.json',
        )

        report = read_report(output_dir, 'report_results.json')
        failed = [t for t in report['tests'] if t['outcome'] == 'failed']
        assert len(failed) >= 1, 'Wrong output should be detected'


class TestSecurityConstraints:
    """Test that security constraints are enforced."""

    def test_readonly_workspace(
        self, grader_image, workspace, output_dir,
        copy_fixture, init_git_repo,
    ):
        """Container should not be able to write to workspace."""
        copy_fixture('exercise_pass.py', workspace)
        init_git_repo(workspace)

        import subprocess
        result = subprocess.run(
            [
                'docker', 'run', '--rm',
                '--user', '1001:1001',
                '-v', f'{workspace}:/app/workspace:ro',
                grader_image,
                'sh', '-c', 'touch /app/workspace/hacked.txt',
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode != 0, 'Should not be able to write to :ro mount'

    def test_network_disabled(
        self, grader_image, workspace, output_dir,
        copy_fixture, init_git_repo,
    ):
        """Container should not have network access."""
        copy_fixture('exercise_pass.py', workspace)
        init_git_repo(workspace)

        import subprocess
        result = subprocess.run(
            [
                'docker', 'run', '--rm',
                '--user', '1001:1001',
                '--network', 'none',
                '-v', f'{workspace}:/app/workspace:ro',
                grader_image,
                'python3', '-c',
                'import urllib.request; urllib.request.urlopen("http://example.com")',
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode != 0, 'Should not have network access'


# end test_grading_pipeline.py
