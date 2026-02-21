# begin test_report_format.py

'''
Tier 1: Validate the JSON report format and schema.

Ensures reports produced by the grading pipeline conform
to the expected schema consumed by the AI tutor.
'''

import pytest


REQUIRED_TOP_LEVEL_KEYS = {'tests', 'summary', 'created'}
REQUIRED_SUMMARY_KEYS = {'total'}
OPTIONAL_SUMMARY_KEYS = {'passed', 'failed', 'skipped', 'error', 'collected', 'xfailed', 'xpassed'}
VALID_OUTCOMES = {'passed', 'failed', 'skipped', 'error', 'xfailed', 'xpassed'}


class TestReportSchema:
    """Validate JSON report structure."""

    @pytest.fixture
    def sample_report(
        self, grader_image, workspace, output_dir,
        copy_fixture, init_git_repo, run_grader, read_report,
    ):
        """Generate a sample report for schema validation."""
        copy_fixture('exercise_pass.py', workspace)
        init_git_repo(workspace)

        run_grader(
            grader_image, workspace, output_dir,
            'test_syntax.py', 'report_syntax.json',
        )

        return read_report(output_dir, 'report_syntax.json')

    def test_top_level_keys(self, sample_report):
        """Report should have required top-level keys."""
        for key in REQUIRED_TOP_LEVEL_KEYS:
            assert key in sample_report, f'Missing key: {key}'

    def test_summary_keys(self, sample_report):
        """Summary should have required fields."""
        summary = sample_report['summary']
        for key in REQUIRED_SUMMARY_KEYS:
            assert key in summary, f'Missing summary key: {key}'

    def test_summary_values_are_integers(self, sample_report):
        """Summary counts should be non-negative integers."""
        summary = sample_report['summary']
        for key in summary:
            assert isinstance(summary[key], int), f'{key} should be int'
            assert summary[key] >= 0, f'{key} should be non-negative'

    def test_summary_total_matches(self, sample_report):
        """Total should equal sum of other counts."""
        summary = sample_report['summary']
        counted = (
            summary.get('passed', 0)
            + summary.get('failed', 0)
            + summary.get('skipped', 0)
            + summary.get('error', 0)
            + summary.get('xfailed', 0)
            + summary.get('xpassed', 0)
        )
        assert summary['total'] == counted

    def test_tests_is_list(self, sample_report):
        """Tests should be a list."""
        assert isinstance(sample_report['tests'], list)

    def test_each_test_has_required_fields(self, sample_report):
        """Each test entry should have nodeid and outcome."""
        for test in sample_report['tests']:
            assert 'nodeid' in test, f'Missing nodeid in test: {test}'
            assert 'outcome' in test, f'Missing outcome in test: {test}'

    def test_outcomes_are_valid(self, sample_report):
        """Test outcomes should be valid values."""
        for test in sample_report['tests']:
            assert test['outcome'] in VALID_OUTCOMES, (
                f'Invalid outcome: {test["outcome"]}'
            )

    def test_created_is_timestamp(self, sample_report):
        """Created field should be a numeric timestamp."""
        assert isinstance(sample_report['created'], (int, float))
        assert sample_report['created'] > 0


class TestFailedReportFormat:
    """Validate that failed test reports include error details."""

    @pytest.fixture
    def failed_report(
        self, grader_image, workspace, output_dir,
        copy_fixture, init_git_repo, run_grader, read_report,
    ):
        """Generate a report with failures."""
        copy_fixture('exercise_fail_syntax.py', workspace)
        init_git_repo(workspace)

        run_grader(
            grader_image, workspace, output_dir,
            'test_syntax.py', 'report_syntax.json',
        )

        return read_report(output_dir, 'report_syntax.json')

    def test_failed_tests_exist(self, failed_report):
        """Report should contain at least one failed test."""
        failed = [t for t in failed_report['tests'] if t['outcome'] == 'failed']
        assert len(failed) >= 1

    def test_failed_tests_have_call_info(self, failed_report):
        """Failed tests should have call information with error details."""
        failed = [t for t in failed_report['tests'] if t['outcome'] == 'failed']
        for test in failed:
            assert 'call' in test or 'setup' in test, (
                f'Failed test should have call or setup info: {test["nodeid"]}'
            )


# end test_report_format.py
