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


class TestEdgeCasesBackwardCompat:
    """Verify the edge-cases grading step is backward-compatible.

    Images WITHOUT test_edge_cases.py should grade normally (3-step).
    Images WITH test_edge_cases.py should run the 4th step.
    """

    def test_image_without_edge_cases_grades_normally(
        self, grader_image, workspace, output_dir,
        copy_fixture, init_git_repo, run_grader, read_report,
        image_has_test_file,
    ):
        """An image without test_edge_cases.py should grade with 3 steps only."""
        if image_has_test_file(grader_image, 'test_edge_cases.py'):
            pytest.skip('Image has test_edge_cases.py — test the WITH path instead')

        copy_fixture('exercise_pass.py', workspace)
        init_git_repo(workspace)

        for test_file, report_name in [
            ('test_syntax.py', 'report_syntax.json'),
            ('test_style.py', 'report_style.json'),
            ('test_results.py', 'report_results.json'),
        ]:
            run_grader(grader_image, workspace, output_dir, test_file, report_name)
            report = read_report(output_dir, report_name)
            assert 'tests' in report, f'{report_name} should have tests'
            assert 'summary' in report, f'{report_name} should have summary'

    def test_edge_cases_file_absent_means_step_skipped(
        self, grader_image, image_has_test_file,
    ):
        """Image without test_edge_cases.py: running it should fail (file not found)."""
        if image_has_test_file(grader_image, 'test_edge_cases.py'):
            pytest.skip('Image has test_edge_cases.py')

        import subprocess
        result = subprocess.run(
            ['docker', 'run', '--rm', grader_image,
             'python3', '-m', 'pytest', '/tests/test_edge_cases.py', '--co'],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0, (
            'test_edge_cases.py should not exist — '
            'the workflow skips this step via max_score_edge_cases=0'
        )

    def test_image_with_edge_cases_runs_4th_step(
        self, grader_image, workspace, output_dir,
        copy_fixture, init_git_repo, run_grader, read_report,
        image_has_test_file,
    ):
        """An image with test_edge_cases.py should run and report the 4th step."""
        if not image_has_test_file(grader_image, 'test_edge_cases.py'):
            pytest.skip('Image does not have test_edge_cases.py')

        copy_fixture('exercise_pass.py', workspace)
        init_git_repo(workspace)

        result = run_grader(
            grader_image, workspace, output_dir,
            'test_edge_cases.py', 'report_edge_cases.json',
        )

        report = read_report(output_dir, 'report_edge_cases.json')
        assert 'tests' in report, 'Edge-cases report should have tests'
        assert 'summary' in report, 'Edge-cases report should have summary'
        assert report['summary']['total'] > 0, 'Edge-cases should have at least one test'

    def test_results_and_edge_cases_are_disjoint(
        self, grader_image, workspace, output_dir,
        copy_fixture, init_git_repo, run_grader, read_report,
        image_has_test_file,
    ):
        """test_results.py and test_edge_cases.py should have no overlapping test names."""
        if not image_has_test_file(grader_image, 'test_edge_cases.py'):
            pytest.skip('Image does not have test_edge_cases.py')

        copy_fixture('exercise_pass.py', workspace)
        init_git_repo(workspace)

        run_grader(grader_image, workspace, output_dir,
                   'test_results.py', 'report_results.json')
        run_grader(grader_image, workspace, output_dir,
                   'test_edge_cases.py', 'report_edge_cases.json')

        results_report = read_report(output_dir, 'report_results.json')
        edge_report = read_report(output_dir, 'report_edge_cases.json')

        results_names = {t['nodeid'].split('::')[-1].split('[')[0]
                         for t in results_report.get('tests', [])}
        edge_names = {t['nodeid'].split('::')[-1].split('[')[0]
                      for t in edge_report.get('tests', [])}

        overlap = results_names & edge_names
        assert not overlap, (
            f'Tests overlap between test_results.py and test_edge_cases.py: {overlap}'
        )


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
