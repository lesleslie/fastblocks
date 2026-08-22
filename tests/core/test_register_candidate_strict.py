"""Phase 1.5.x remediation Card 1 — tests for register_candidate_strict.

F-L5-01 (Phase 1.5 adversarial review): ``register_candidate``
silently swallowed ``(ValidationError, ValueError, TypeError)`` and
returned ``False``. Phase 2 callers need validation failures to
surface as exceptions so typed candidates fail loudly at startup.

These tests cover the new ``register_candidate_strict`` method on
both the ``FastblocksRegistry`` facade (resolver.py) and the
legacy ``oneiric_helper`` helper. They also pin the behavior
of the original ``register_candidate`` so the lenient path is
not silently changed.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from fastblocks.adapters.oneiric_helper import (
    register_candidate as helper_register,
)
from fastblocks.adapters.oneiric_helper import (
    register_candidate_strict as helper_register_strict,
)
from fastblocks.core.resolver import (
    CandidateValidationError,
    FastblocksRegistry,
    get_resolver,
)


# A factory that returns a valid (callable, returns an object) value.
def _good_factory() -> str:
    return "instance"


@pytest.mark.unit
def test_strict_method_raises_candidate_validation_error_on_invalid_domain() -> None:
    """Passing ``domain=None`` (Pydantic rejects) must raise CandidateValidationError.

    Oneiric's ``Candidate`` doesn't Pydantic-validate ``factory`` itself
    (callables are accepted as-is), but it DOES validate ``domain`` and
    ``key`` as ``str`` and ``metadata`` as ``dict``. Use those to
    exercise the documented ValidationError path.
    """
    registry = FastblocksRegistry(get_resolver())
    with pytest.raises(CandidateValidationError) as exc_info:
        registry.register_candidate_strict(
            None,  # ty: ignore[invalid-argument-type]  # intentionally invalid domain
            "valid_key",
            factory=_good_factory,
        )
    # Exception carries the (domain, key) tuple so callers can log/respond.
    assert exc_info.value.domain is None  # whatever the caller passed
    assert exc_info.value.key == "valid_key"
    # Original exception is chained for debugging.
    assert exc_info.value.__cause__ is not None
    assert isinstance(exc_info.value.__cause__, ValidationError)


@pytest.mark.unit
def test_strict_method_raises_on_invalid_metadata() -> None:
    """Non-dict metadata must raise CandidateValidationError.

    Pydantic-validated ``Candidate.metadata`` field rejects non-dict
    values, surfacing as ``ValidationError``. The strict path
    converts that to ``CandidateValidationError`` so callers see a
    single exception type for all validation rejections.
    """
    registry = FastblocksRegistry(get_resolver())
    with pytest.raises(CandidateValidationError) as exc_info:
        registry.register_candidate_strict(
            "card1_test",
            "bad_metadata",
            factory=_good_factory,
            metadata=["not", "a", "dict"],  # ty: ignore[invalid-argument-type]
        )
    assert exc_info.value.domain == "card1_test"
    assert exc_info.value.key == "bad_metadata"


@pytest.mark.unit
def test_strict_method_returns_none_on_success() -> None:
    """Valid registration: no exception, candidate is in registry."""
    registry = FastblocksRegistry(get_resolver())
    # Use a unique domain+key per test run to avoid clashing with
    # prior tests; clean_resolver fixture resets between tests, so
    # a stable key would also work, but unique avoids accidental coupling.
    result = registry.register_candidate_strict(
        "card1_test",
        "valid_registration",
        factory=_good_factory,
    )
    assert result is None
    # Verify it actually registered.
    resolved = registry.resolve("card1_test", "valid_registration")
    assert resolved is not None
    assert resolved.factory is _good_factory


@pytest.mark.unit
def test_lenient_method_still_returns_false_on_invalid() -> None:
    """The original ``register_candidate`` MUST keep its bool contract.

    Pinning test: the lenient path is the documented Phase 1.5.x
    contract (~80 callers depend on the bool return). Phase 2 callers
    use ``register_candidate_strict`` instead. The lenient path
    continues to return ``False`` on validation failure.
    """
    registry = FastblocksRegistry(get_resolver())
    # Use domain=None to trigger Pydantic ValidationError (the documented
    # swallow set catches this). We can't use non-callable factory
    # because Oneiric's Candidate doesn't Pydantic-validate factories.
    result = registry.register_candidate(
        None,  # ty: ignore[invalid-argument-type]
        "lenient_invalid_domain",
        factory=_good_factory,
    )
    assert result is False, (
        "Lenient register_candidate must keep returning False on "
        "validation failure (backward-compat contract for ~80 callers)."
    )


@pytest.mark.unit
def test_lenient_method_returns_true_on_success() -> None:
    """The original ``register_candidate`` MUST keep its True-on-success contract."""
    registry = FastblocksRegistry(get_resolver())
    assert registry.register_candidate(
        "card1_test",
        "lenient_valid",
        factory=_good_factory,
    ) is True


@pytest.mark.unit
def test_candidate_validation_error_is_value_error_subclass() -> None:
    """CandidateValidationError subclasses ValueError so existing handlers match."""
    assert issubclass(CandidateValidationError, ValueError)
    # The subclass relationship is the load-bearing part of the contract:
    # Phase 2 callers that wrote ``except ValueError:`` continue to work
    # without modification. New callers can catch the specific class.
    err = CandidateValidationError(
        domain="x", key="y", original=ValueError("inner"),
    )
    try:
        raise err
    except ValueError as caught:
        assert caught is err


@pytest.mark.unit
def test_helper_register_candidate_strict_raises_on_invalid_domain() -> None:
    """The legacy ``oneiric_helper.register_candidate_strict`` raises too."""
    registry = FastblocksRegistry(get_resolver())
    with pytest.raises(CandidateValidationError) as exc_info:
        helper_register_strict(
            registry,
            domain=None,  # ty: ignore[invalid-argument-type]  # invalid domain
            key="bad_domain",
            factory=_good_factory,
        )
    assert exc_info.value.key == "bad_domain"


@pytest.mark.unit
def test_helper_register_candidate_returns_false_on_invalid_domain() -> None:
    """The legacy ``oneiric_helper.register_candidate`` (lenient) still returns False."""
    registry = FastblocksRegistry(get_resolver())
    assert (
        helper_register(
            registry,
            domain=None,  # ty: ignore[invalid-argument-type]
            key="lenient_bad_domain",
            factory=_good_factory,
        )
        is False
    )


@pytest.mark.unit
def test_strict_method_preserves_original_exception_chain() -> None:
    """The ``__cause__`` on CandidateValidationError points to the original error."""
    registry = FastblocksRegistry(get_resolver())
    with pytest.raises(CandidateValidationError) as exc_info:
        registry.register_candidate_strict(
            None,  # ty: ignore[invalid-argument-type]
            "chain_check",
            factory=_good_factory,
        )
    # The chained exception is the underlying validation error, NOT a string.
    original = exc_info.value.__cause__
    assert original is not None
    # It's a ValidationError (the documented swallow set).
    assert isinstance(original, ValidationError)


@pytest.mark.unit
def test_strict_method_does_not_swallow_runtime_errors() -> None:
    """Resolver implementation errors propagate as before (not graceful)."""
    # Mock the resolver.register to raise a non-documentation RuntimeError.
    registry = FastblocksRegistry(get_resolver())
    original_register = registry._resolver.register

    def fake_register(_candidate: object) -> None:
        raise RuntimeError("implementation bug, not validation")

    try:
        registry._resolver.register = fake_register  # ty: ignore[invalid-assignment]
        with pytest.raises(RuntimeError, match="implementation bug"):
            registry.register_candidate_strict(
                "card1_test",
                "runtime_bug",
                factory=_good_factory,
            )
    finally:
        registry._resolver.register = original_register  # ty: ignore[invalid-assignment]


@pytest.mark.unit
def test_lenient_path_still_uses_documented_swallow_set() -> None:
    """Pin: ValidationError, ValueError, TypeError all return False.

    Documents the exact set the lenient path catches. If a future
    change broadens this set (e.g. catches BaseException), this test
    fails.

    We use domain=None to trigger ValidationError (Pydantic). We don't
    test non-callable factory here because Oneiric's Candidate
    doesn't Pydantic-validate callables — but we can use a list as
    metadata to trigger the dict validation.
    """
    registry = FastblocksRegistry(get_resolver())

    # ValidationError via domain
    assert (
        registry.register_candidate(
            None,  # ty: ignore[invalid-argument-type]
            "k1",
            factory=_good_factory,
        )
        is False
    )

    # ValidationError via metadata (non-dict)
    assert (
        registry.register_candidate(
            "card1_test",
            "k2",
            factory=_good_factory,
            metadata=[1, 2, 3],  # ty: ignore[invalid-argument-type]
        )
        is False
    )

    # Successful registration still returns True
    assert (
        registry.register_candidate(
            "card1_test",
            "k3_valid",
            factory=_good_factory,
        )
        is True
    )
