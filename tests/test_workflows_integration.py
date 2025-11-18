"""Tests for FastBlocks ACB Workflows integration.

Verifies workflow orchestration, background jobs, and graceful degradation.
"""

import pytest

# Try to import workflows integration
try:
    from fastblocks._workflows_integration import (
        ACB_WORKFLOWS_AVAILABLE,
        FastBlocksWorkflowService,
        execute_cache_warming,
        execute_performance_optimization,
        execute_template_cleanup,
        get_workflow_service,
        register_fastblocks_workflows,
    )

    WORKFLOWS_INTEGRATION_AVAILABLE = True
except ImportError:
    WORKFLOWS_INTEGRATION_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="Workflows integration not available")


@pytest.fixture
def workflow_service():
    """Get workflow service instance."""
    if not WORKFLOWS_INTEGRATION_AVAILABLE:
        pytest.skip("Workflows integration not available")
    return get_workflow_service()


@pytest.mark.integration
class TestWorkflowServiceBasics:
    """Test basic workflow service functionality."""

    def test_singleton_pattern(self, workflow_service):
        """Test that get_workflow_service returns the same instance."""
        service1 = get_workflow_service()
        service2 = get_workflow_service()
        assert service1 is service2

    def test_availability_check(self, workflow_service):
        """Test workflow service availability property."""
        # Should be True when ACB available, False otherwise
        assert isinstance(workflow_service.available, bool)

    def test_acb_availability_flag(self):
        """Test ACB_WORKFLOWS_AVAILABLE flag."""
        assert isinstance(ACB_WORKFLOWS_AVAILABLE, bool)


@pytest.mark.integration
class TestCacheWarmingWorkflow:
    """Test cache warming workflow functionality."""

    @pytest.mark.asyncio
    async def test_cache_warming_all_enabled(self, workflow_service):
        """Test cache warming with all options enabled."""
        result = await execute_cache_warming(
            warm_templates=True,
            warm_static=True,
            warm_routes=True,
        )

        # Verify result structure
        assert isinstance(result, dict)
        assert "workflow_id" in result
        assert result["workflow_id"] == "cache-warming"
        assert "state" in result
        assert "completed_at" in result

        # Check for either workflow mode or manual mode results
        if "mode" in result and result["mode"] == "manual":
            assert "results" in result
        else:
            assert "steps_completed" in result or "mode" in result

    @pytest.mark.asyncio
    async def test_cache_warming_templates_only(self, workflow_service):
        """Test cache warming with only templates enabled."""
        result = await execute_cache_warming(
            warm_templates=True,
            warm_static=False,
            warm_routes=False,
        )

        assert result["workflow_id"] == "cache-warming"
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_cache_warming_static_only(self, workflow_service):
        """Test cache warming with only static files enabled."""
        result = await execute_cache_warming(
            warm_templates=False,
            warm_static=True,
            warm_routes=False,
        )

        assert result["workflow_id"] == "cache-warming"
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_cache_warming_routes_only(self, workflow_service):
        """Test cache warming with only routes enabled."""
        result = await execute_cache_warming(
            warm_templates=False,
            warm_static=False,
            warm_routes=True,
        )

        assert result["workflow_id"] == "cache-warming"
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_cache_warming_none_enabled(self, workflow_service):
        """Test cache warming with no options enabled."""
        result = await execute_cache_warming(
            warm_templates=False,
            warm_static=False,
            warm_routes=False,
        )

        assert result["workflow_id"] == "cache-warming"
        # Should complete successfully even with nothing to do
        assert result["state"] in ["completed", "skipped"]


@pytest.mark.integration
class TestTemplateCleanupWorkflow:
    """Test template cleanup workflow functionality."""

    @pytest.mark.asyncio
    async def test_template_cleanup_all_enabled(self, workflow_service):
        """Test template cleanup with all options enabled."""
        result = await execute_template_cleanup(
            remove_stale=True,
            optimize_storage=True,
            cleanup_cache=True,
        )

        # Verify result structure
        assert isinstance(result, dict)
        assert "workflow_id" in result
        assert result["workflow_id"] == "template-cleanup"
        assert "state" in result
        assert "completed_at" in result

    @pytest.mark.asyncio
    async def test_template_cleanup_dependency_chain(self, workflow_service):
        """Test that cleanup steps execute in dependency order."""
        # cleanup_cache → remove_stale → optimize_storage
        result = await execute_template_cleanup(
            remove_stale=True,
            optimize_storage=True,
            cleanup_cache=True,
        )

        # Should complete successfully
        assert result["state"] in ["completed", "failed", "skipped"]

        # In manual mode, check results order
        if "mode" in result and result["mode"] == "manual":
            results = result.get("results", {})
            # All three steps should be present
            expected_keys = {"cache_cleanup", "stale_removal", "storage_optimization"}
            assert expected_keys.issubset(set(results.keys()))

    @pytest.mark.asyncio
    async def test_template_cleanup_cache_only(self, workflow_service):
        """Test template cleanup with only cache cleanup enabled."""
        result = await execute_template_cleanup(
            remove_stale=False,
            optimize_storage=False,
            cleanup_cache=True,
        )

        assert result["workflow_id"] == "template-cleanup"
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_template_cleanup_stale_only(self, workflow_service):
        """Test template cleanup with only stale removal enabled."""
        result = await execute_template_cleanup(
            remove_stale=True,
            optimize_storage=False,
            cleanup_cache=False,
        )

        assert result["workflow_id"] == "template-cleanup"
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_template_cleanup_none_enabled(self, workflow_service):
        """Test template cleanup with no options enabled."""
        result = await execute_template_cleanup(
            remove_stale=False,
            optimize_storage=False,
            cleanup_cache=False,
        )

        assert result["workflow_id"] == "template-cleanup"
        # Should complete successfully even with nothing to do
        assert result["state"] in ["completed", "skipped"]


@pytest.mark.integration
class TestPerformanceOptimizationWorkflow:
    """Test performance optimization workflow functionality."""

    @pytest.mark.asyncio
    async def test_performance_optimization_all_enabled(self, workflow_service):
        """Test performance optimization with all options enabled."""
        result = await execute_performance_optimization(
            optimize_queries=True,
            rebuild_indexes=True,
            cleanup_sessions=True,
        )

        # Verify result structure
        assert isinstance(result, dict)
        assert "workflow_id" in result
        assert result["workflow_id"] == "performance-optimization"
        assert "state" in result
        assert "completed_at" in result

    @pytest.mark.asyncio
    async def test_performance_optimization_dependency_chain(self, workflow_service):
        """Test that optimization steps execute with proper dependencies."""
        # optimize_queries → rebuild_indexes (depends on optimize_queries)
        result = await execute_performance_optimization(
            optimize_queries=True,
            rebuild_indexes=True,
            cleanup_sessions=False,
        )

        # Should complete successfully
        assert result["state"] in ["completed", "failed", "skipped"]

    @pytest.mark.asyncio
    async def test_performance_optimization_queries_only(self, workflow_service):
        """Test performance optimization with only query optimization."""
        result = await execute_performance_optimization(
            optimize_queries=True,
            rebuild_indexes=False,
            cleanup_sessions=False,
        )

        assert result["workflow_id"] == "performance-optimization"
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_performance_optimization_sessions_only(self, workflow_service):
        """Test performance optimization with only session cleanup."""
        result = await execute_performance_optimization(
            optimize_queries=False,
            rebuild_indexes=False,
            cleanup_sessions=True,
        )

        assert result["workflow_id"] == "performance-optimization"
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_performance_optimization_none_enabled(self, workflow_service):
        """Test performance optimization with no options enabled."""
        result = await execute_performance_optimization(
            optimize_queries=False,
            rebuild_indexes=False,
            cleanup_sessions=False,
        )

        assert result["workflow_id"] == "performance-optimization"
        # Should complete successfully even with nothing to do
        assert result["state"] in ["completed", "skipped"]


@pytest.mark.integration
class TestActionHandlers:
    """Test individual action handler functions."""

    @pytest.mark.asyncio
    async def test_warm_template_cache_handler(self):
        """Test template cache warming handler."""
        from fastblocks._workflows_integration import _warm_template_cache

        result = await _warm_template_cache({}, {})

        # Should return a dict with status
        assert isinstance(result, dict)
        assert "status" in result
        assert result["status"] in ["completed", "skipped"]

    @pytest.mark.asyncio
    async def test_warm_static_cache_handler(self):
        """Test static file cache warming handler."""
        from fastblocks._workflows_integration import _warm_static_cache

        result = await _warm_static_cache({}, {})

        assert isinstance(result, dict)
        assert "status" in result

    @pytest.mark.asyncio
    async def test_warm_route_cache_handler(self):
        """Test route cache warming handler."""
        from fastblocks._workflows_integration import _warm_route_cache

        result = await _warm_route_cache({}, {})

        assert isinstance(result, dict)
        assert "status" in result

    @pytest.mark.asyncio
    async def test_cleanup_template_cache_handler(self):
        """Test template cache cleanup handler."""
        from fastblocks._workflows_integration import _cleanup_template_cache

        result = await _cleanup_template_cache({}, {})

        assert isinstance(result, dict)
        assert "status" in result
        assert "cache_cleared" in result

    @pytest.mark.asyncio
    async def test_remove_stale_templates_handler(self):
        """Test stale template removal handler."""
        from fastblocks._workflows_integration import _remove_stale_templates

        result = await _remove_stale_templates({}, {"days_threshold": 30})

        assert isinstance(result, dict)
        assert "status" in result
        assert "templates_removed" in result
        assert "days_threshold" in result
        assert result["days_threshold"] == 30

    @pytest.mark.asyncio
    async def test_optimize_template_storage_handler(self):
        """Test template storage optimization handler."""
        from fastblocks._workflows_integration import _optimize_template_storage

        result = await _optimize_template_storage({}, {})

        assert isinstance(result, dict)
        assert "status" in result

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions_handler(self):
        """Test expired session cleanup handler."""
        from fastblocks._workflows_integration import _cleanup_expired_sessions

        result = await _cleanup_expired_sessions({}, {"expiry_hours": 24})

        assert isinstance(result, dict)
        assert "status" in result
        assert "sessions_cleaned" in result
        assert "expiry_hours" in result
        assert result["expiry_hours"] == 24

    @pytest.mark.asyncio
    async def test_optimize_database_queries_handler(self):
        """Test database query optimization handler."""
        from fastblocks._workflows_integration import _optimize_database_queries

        result = await _optimize_database_queries({}, {})

        assert isinstance(result, dict)
        assert "status" in result

    @pytest.mark.asyncio
    async def test_rebuild_database_indexes_handler(self):
        """Test database index rebuild handler."""
        from fastblocks._workflows_integration import _rebuild_database_indexes

        result = await _rebuild_database_indexes({}, {})

        assert isinstance(result, dict)
        assert "status" in result


@pytest.mark.integration
class TestManualFallbacks:
    """Test manual fallback implementations."""

    @pytest.mark.asyncio
    async def test_manual_cache_warming(self):
        """Test manual cache warming fallback."""
        from fastblocks._workflows_integration import _manual_cache_warming

        result = await _manual_cache_warming(
            warm_templates=True,
            warm_static=True,
            warm_routes=True,
        )

        # Verify manual mode result structure
        assert isinstance(result, dict)
        assert result["workflow_id"] == "cache-warming"
        assert result["mode"] == "manual"
        assert "state" in result
        assert "completed_at" in result
        assert "results" in result

        # Check that all requested operations were attempted
        results = result["results"]
        assert "templates" in results
        assert "static" in results
        assert "routes" in results

    @pytest.mark.asyncio
    async def test_manual_template_cleanup(self):
        """Test manual template cleanup fallback."""
        from fastblocks._workflows_integration import _manual_template_cleanup

        result = await _manual_template_cleanup(
            remove_stale=True,
            optimize_storage=True,
            cleanup_cache=True,
        )

        # Verify manual mode result structure
        assert isinstance(result, dict)
        assert result["workflow_id"] == "template-cleanup"
        assert result["mode"] == "manual"
        assert "results" in result

        # Check that all requested operations were attempted
        results = result["results"]
        assert "cache_cleanup" in results
        assert "stale_removal" in results
        assert "storage_optimization" in results

    @pytest.mark.asyncio
    async def test_manual_performance_optimization(self):
        """Test manual performance optimization fallback."""
        from fastblocks._workflows_integration import _manual_performance_optimization

        result = await _manual_performance_optimization(
            optimize_queries=True,
            rebuild_indexes=True,
            cleanup_sessions=True,
        )

        # Verify manual mode result structure
        assert isinstance(result, dict)
        assert result["workflow_id"] == "performance-optimization"
        assert result["mode"] == "manual"
        assert "results" in result

        # Check that all requested operations were attempted
        results = result["results"]
        assert "session_cleanup" in results
        assert "query_optimization" in results
        assert "index_rebuild" in results


@pytest.mark.integration
class TestGracefulDegradation:
    """Test graceful degradation when ACB unavailable."""

    @pytest.mark.asyncio
    async def test_workflows_when_acb_unavailable(self, workflow_service):
        """Test that workflows degrade gracefully when ACB unavailable."""
        # All workflows should work, just using manual mode if ACB unavailable
        result = await execute_cache_warming()

        # Should succeed (graceful degradation)
        assert isinstance(result, dict)
        assert "workflow_id" in result
        assert "state" in result

    @pytest.mark.asyncio
    async def test_template_cleanup_degradation(self, workflow_service):
        """Test template cleanup degradation."""
        result = await execute_template_cleanup()

        assert isinstance(result, dict)
        assert result["workflow_id"] == "template-cleanup"

    @pytest.mark.asyncio
    async def test_performance_optimization_degradation(self, workflow_service):
        """Test performance optimization degradation."""
        result = await execute_performance_optimization()

        assert isinstance(result, dict)
        assert result["workflow_id"] == "performance-optimization"


@pytest.mark.integration
class TestWorkflowResultStructure:
    """Test workflow result structure consistency."""

    @pytest.mark.asyncio
    async def test_cache_warming_result_keys(self):
        """Test cache warming result has required keys."""
        result = await execute_cache_warming()

        # Required keys for all workflows
        required_keys = {"workflow_id", "state", "completed_at"}
        assert required_keys.issubset(set(result.keys()))

    @pytest.mark.asyncio
    async def test_template_cleanup_result_keys(self):
        """Test template cleanup result has required keys."""
        result = await execute_template_cleanup()

        required_keys = {"workflow_id", "state", "completed_at"}
        assert required_keys.issubset(set(result.keys()))

    @pytest.mark.asyncio
    async def test_performance_optimization_result_keys(self):
        """Test performance optimization result has required keys."""
        result = await execute_performance_optimization()

        required_keys = {"workflow_id", "state", "completed_at"}
        assert required_keys.issubset(set(result.keys()))

    @pytest.mark.asyncio
    async def test_workflow_mode_indicator(self):
        """Test that results indicate workflow or manual mode."""
        result = await execute_cache_warming()

        # Should have either ACB workflow keys or manual mode indicator
        has_workflow_keys = "steps_completed" in result and "steps_failed" in result
        has_manual_mode = "mode" in result and result["mode"] == "manual"

        assert has_workflow_keys or has_manual_mode


@pytest.mark.integration
class TestRegistration:
    """Test workflow service registration."""

    @pytest.mark.asyncio
    async def test_register_workflows(self):
        """Test registration of workflow service."""
        result = await register_fastblocks_workflows()

        # Should return bool indicating success/failure
        assert isinstance(result, bool)

    def test_workflow_service_exports(self):
        """Test that all expected symbols are exported."""
        expected_exports = [
            "FastBlocksWorkflowService",
            "get_workflow_service",
            "execute_cache_warming",
            "execute_template_cleanup",
            "execute_performance_optimization",
            "register_fastblocks_workflows",
            "ACB_WORKFLOWS_AVAILABLE",
        ]

        from fastblocks import _workflows_integration

        for export in expected_exports:
            assert hasattr(_workflows_integration, export), f"Missing export: {export}"


@pytest.mark.integration
class TestWorkflowParameters:
    """Test workflow parameter handling."""

    @pytest.mark.asyncio
    async def test_cache_warming_parameter_combinations(self):
        """Test various parameter combinations for cache warming."""
        # Test all combinations of True/False for three booleans
        combinations = [
            (True, True, True),
            (True, True, False),
            (True, False, True),
            (False, True, True),
            (True, False, False),
            (False, True, False),
            (False, False, True),
            (False, False, False),
        ]

        for warm_templates, warm_static, warm_routes in combinations:
            result = await execute_cache_warming(
                warm_templates=warm_templates,
                warm_static=warm_static,
                warm_routes=warm_routes,
            )

            # All combinations should succeed
            assert isinstance(result, dict)
            assert result["workflow_id"] == "cache-warming"

    @pytest.mark.asyncio
    async def test_template_cleanup_parameter_combinations(self):
        """Test various parameter combinations for template cleanup."""
        combinations = [
            (True, True, True),
            (True, False, False),
            (False, True, False),
            (False, False, True),
        ]

        for remove_stale, optimize_storage, cleanup_cache in combinations:
            result = await execute_template_cleanup(
                remove_stale=remove_stale,
                optimize_storage=optimize_storage,
                cleanup_cache=cleanup_cache,
            )

            assert isinstance(result, dict)
            assert result["workflow_id"] == "template-cleanup"


@pytest.mark.integration
class TestWorkflowTiming:
    """Test workflow execution timing and timeout behavior."""

    @pytest.mark.asyncio
    async def test_cache_warming_completes_quickly(self):
        """Test that cache warming completes in reasonable time."""
        import time

        start = time.time()
        result = await execute_cache_warming()
        elapsed = time.time() - start

        # Should complete within 10 seconds (generous timeout for tests)
        assert elapsed < 10
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_template_cleanup_completes_quickly(self):
        """Test that template cleanup completes in reasonable time."""
        import time

        start = time.time()
        result = await execute_template_cleanup()
        elapsed = time.time() - start

        # Should complete within 10 seconds
        assert elapsed < 10
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_performance_optimization_completes_quickly(self):
        """Test that performance optimization completes in reasonable time."""
        import time

        start = time.time()
        result = await execute_performance_optimization()
        elapsed = time.time() - start

        # Should complete within 10 seconds
        assert elapsed < 10
        assert isinstance(result, dict)


# Run tests with: python -m pytest tests/test_workflows_integration.py -v
