"""Security-specific fixtures for the tests/security/ suite."""

from __future__ import annotations

import pytest


@pytest.fixture
def xss_payloads() -> list[str]:
    """Standard XSS payloads used across security tests."""
    return [
        "<script>alert(1)</script>",
        "javascript:alert(1)",
        "<img src=x onerror=alert(1)>",
        "<svg onload=alert(1)>",
        '"><script>alert(document.cookie)</script>',
        "<iframe src=javascript:alert(1)>",
        "<body onload=alert(1)>",
        "'-alert(1)-'",
        '";alert(1);//',
        "<script>alert('XSS')</script>",
    ]


@pytest.fixture
def sqli_payloads() -> list[str]:
    """Standard SQL injection payloads used across security tests."""
    return [
        "' OR 1=1 --",
        "'; DROP TABLE users; --",
        "admin' OR '1'='1",
        "' UNION SELECT * FROM users --",
        "'; DELETE FROM users WHERE '1'='1",
        "admin'--",
        "' OR 'x'='x",
        "' OR 1=1#",
        "1=1",
        '" OR ""="',
    ]


@pytest.fixture
def path_traversal_payloads() -> list[str]:
    """Standard path-traversal payloads used across security tests."""
    return [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32",
        "%2e%2e%2f",
        "....//",
        "../../etc/shadow",
        "./../../../etc",
        "%252e%252e%252f",
        "..%2f..%2f..%2fetc%2fpasswd",
    ]


@pytest.fixture
def safe_inputs() -> list[str]:
    """Inputs that must NOT be flagged by any security check."""
    return [
        "normal text",
        "user@example.com",
        "valid-username_123",
        "This is a normal sentence.",
        "hello world",
        "product-v2.0",
    ]
