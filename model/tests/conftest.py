"""Common fixtures for model tests.

Provides stub AWS credentials so boto3 does not attempt real credential
provider lookups (which require optional native dependencies on macOS).
"""

import pytest


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set dummy AWS environment variables before every test.

    Without these, boto3 falls through to the SSO/login credential provider
    which requires botocore[crt] — an optional dependency not installed in CI.
    """
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "test")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "test")
