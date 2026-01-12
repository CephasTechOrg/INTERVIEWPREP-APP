# CI/CD Pipeline Documentation

## Overview

This directory contains GitHub Actions workflows for automated testing, quality checks, and deployment of the InterviewPrep-App.

## Workflows

### CI Pipeline (`ci.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

**Jobs:**

#### 1. Test & Quality Checks
- **Python Setup**: Python 3.11
- **Database**: PostgreSQL 16 test instance
- **Steps**:
  1. Install dependencies (`requirements.txt` + `requirements-dev.txt`)
  2. Validate question datasets with `--strict` mode
  3. Check Alembic migrations are up to date
  4. Run pytest with coverage (target: 65-70%)
  5. Upload coverage to Codecov
  6. Lint with ruff
  7. Check formatting with black
  8. Type check with mypy (non-blocking)

#### 2. Security Scan
- **Steps**:
  1. Check for known vulnerabilities with `safety`
  2. Run security linter with `bandit`
  3. Report findings (non-blocking)

#### 3. Frontend Checks
- **Steps**:
  1. Validate HTML files (basic structure)
  2. Check JavaScript syntax
  3. Ensure no obvious errors

#### 4. Docker Build Test
- **Steps**:
  1. Validate docker-compose configuration
  2. Test backend Docker image build

#### 5. CI Summary
- **Steps**:
  1. Aggregate results from all jobs
  2. Generate summary report
  3. Fail if critical checks fail

## Environment Variables

The CI pipeline uses the following environment variables:

### Required (Set in GitHub Secrets)
- None currently - all tests use test database

### Optional (For Enhanced Features)
- `CODECOV_TOKEN`: For uploading coverage reports to Codecov
- `DEEPSEEK_API_KEY`: For testing LLM integration (uses fallback if not set)

## Status Badges

Add these to your main README.md:

```markdown
![CI Pipeline](https://github.com/YOUR_USERNAME/INTERVIEWPREP-APP/workflows/CI%20Pipeline/badge.svg)
[![codecov](https://codecov.io/gh/YOUR_USERNAME/INTERVIEWPREP-APP/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_USERNAME/INTERVIEWPREP-APP)
```

## Local Testing

Before pushing, you can run the same checks locally:

### 1. Install Pre-commit Hooks
```bash
pip install pre-commit
pre-commit install
```

### 2. Run All Checks Manually
```bash
# Validate questions
python scripts/validate_questions.py --strict

# Run tests with coverage
cd backend
pytest --cov=app --cov-report=term-missing

# Lint
ruff check app/ tests/

# Format check
black app/ tests/ --check

# Type check
mypy app/ --ignore-missing-imports
```

### 3. Run Pre-commit on All Files
```bash
pre-commit run --all-files
```

## Troubleshooting

### Tests Failing Locally But Pass in CI
- Ensure you're using Python 3.11
- Check that PostgreSQL is running: `docker-compose up -d`
- Run migrations: `cd backend && alembic upgrade head`
- Clear pytest cache: `rm -rf .pytest_cache`

### Alembic Migration Check Failing
- Ensure all migrations are committed
- Run `alembic upgrade head` locally
- Check `alembic current` matches `alembic heads`
- If needed, create a new migration: `alembic revision --autogenerate -m "description"`

### Coverage Below Target
- Add tests for uncovered code paths
- Check coverage report: `pytest --cov=app --cov-report=html`
- Open `htmlcov/index.html` to see detailed coverage

### Linting Errors
- Auto-fix with: `ruff check app/ tests/ --fix`
- Format with: `black app/ tests/`
- Review remaining errors manually

### Type Checking Errors
- Currently non-blocking (continue-on-error: true)
- Fix gradually by adding type hints
- Use `# type: ignore` for third-party library issues

## CI Performance

### Typical Run Times
- Test & Quality: ~3-5 minutes
- Security Scan: ~1-2 minutes
- Frontend Checks: ~30 seconds
- Docker Build: ~2-3 minutes
- **Total**: ~7-11 minutes

### Optimization Tips
1. Use caching for pip dependencies (already enabled)
2. Run fast tests first, slow tests later
3. Parallelize independent jobs
4. Use matrix strategy for multiple Python versions (if needed)

## Future Enhancements

### Planned Additions
- [ ] Deploy to staging on merge to `develop`
- [ ] Deploy to production on merge to `main`
- [ ] Performance testing with locust
- [ ] E2E testing with Playwright
- [ ] Dependency update automation with Dependabot
- [ ] Security scanning with Snyk
- [ ] Container scanning with Trivy

### Configuration Options
- Add matrix testing for multiple Python versions
- Add matrix testing for multiple PostgreSQL versions
- Add scheduled runs for nightly builds
- Add manual workflow dispatch for on-demand runs

## Contributing

When adding new workflows:
1. Test locally with `act` (GitHub Actions local runner)
2. Use descriptive job and step names
3. Add appropriate error handling
4. Document any new environment variables
5. Update this README

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [pytest Documentation](https://docs.pytest.org/)
- [ruff Documentation](https://docs.astral.sh/ruff/)
- [black Documentation](https://black.readthedocs.io/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [pre-commit Documentation](https://pre-commit.com/)

## Support

For issues with CI/CD:
1. Check the workflow run logs in GitHub Actions tab
2. Review this documentation
3. Check the main project README.md
4. Open an issue with the `ci/cd` label
