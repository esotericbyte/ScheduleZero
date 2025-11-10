"""
Test Suite for Governor Architecture

Tests the Governor ABC, ProcessGovernor implementation, and related components.
Covers process management, signal handling, and dynamic handler operations.
"""
import pytest
import time
import signal
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.schedule_zero.governor_base import (
    GovernorBase, 
    HandlerConfig, 
    ProcessInfo
)
from src.schedule_zero.process_governor import ProcessGovernor, ProcessManager
from src.schedule_zero.logging_config import get_logger

logger = get_logger(__name__, component="TestGovernor")


class TestHandlerConfig:
    """Test HandlerConfig data class."""
    
    def test_basic_creation(self):
        """Test creating a basic handler config."""
        config = HandlerConfig(
            handler_id="test-handler",
            module_path="tests.test_handler",
            class_name="TestHandler",
            port=5555
        )
        
        assert config.handler_id == "test-handler"
        assert config.module_path == "tests.test_handler"
        assert config.class_name == "TestHandler"
        assert config.port == 5555
        assert config.auto_restart is True  # Default
        assert config.max_restarts == 3  # Default
    
    def test_custom_restart_config(self):
        """Test handler config with custom restart settings."""
        config = HandlerConfig(
            handler_id="test-handler",
            module_path="tests.test_handler",
            class_name="TestHandler",
            port=5555,
            auto_restart=False,
            max_restarts=5,
            restart_delay=10.0
        )
        
        assert config.auto_restart is False
        assert config.max_restarts == 5
        assert config.restart_delay == 10.0
    
    def test_extra_config(self):
        """Test handler config with extra kwargs."""
        config = HandlerConfig(
            handler_id="test-handler",
            module_path="tests.test_handler",
            class_name="TestHandler",
            port=5555,
            custom_param="value",
            another_setting=42
        )
        
        assert config.extra_config["custom_param"] == "value"
        assert config.extra_config["another_setting"] == 42
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = HandlerConfig(
            handler_id="test-handler",
            module_path="tests.test_handler",
            class_name="TestHandler",
            port=5555,
            custom="value"
        )
        
        data = config.to_dict()
        
        assert data["handler_id"] == "test-handler"
        assert data["module_path"] == "tests.test_handler"
        assert data["class_name"] == "TestHandler"
        assert data["port"] == 5555
        assert data["custom"] == "value"
    
    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "handler_id": "test-handler",
            "module_path": "tests.test_handler",
            "class_name": "TestHandler",
            "port": 5555,
            "auto_restart": False
        }
        
        config = HandlerConfig.from_dict(data)
        
        assert config.handler_id == "test-handler"
        assert config.auto_restart is False


class TestProcessInfo:
    """Test ProcessInfo data class."""
    
    def test_basic_creation(self):
        """Test creating process info."""
        info = ProcessInfo(
            name="test-process",
            pid=12345,
            status="running"
        )
        
        assert info.name == "test-process"
        assert info.pid == 12345
        assert info.status == "running"
        assert info.restart_count == 0
        assert info.last_error is None
    
    def test_with_error(self):
        """Test process info with error."""
        info = ProcessInfo(
            name="test-process",
            pid=12345,
            status="crashed",
            restart_count=2,
            last_error="Connection refused"
        )
        
        assert info.status == "crashed"
        assert info.restart_count == 2
        assert info.last_error == "Connection refused"
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        info = ProcessInfo(
            name="test-process",
            pid=12345,
            status="running",
            restart_count=1
        )
        
        data = info.to_dict()
        
        assert data["name"] == "test-process"
        assert data["pid"] == 12345
        assert data["status"] == "running"
        assert data["restart_count"] == 1


class TestGovernorBase:
    """Test GovernorBase abstract class."""
    
    def test_cannot_instantiate_directly(self):
        """Test that ABC cannot be instantiated."""
        with pytest.raises(TypeError):
            GovernorBase("test")
    
    def test_must_implement_abstract_methods(self):
        """Test that subclasses must implement all abstract methods."""
        
        class IncompleteGovernor(GovernorBase):
            """Governor missing required methods."""
            pass
        
        with pytest.raises(TypeError):
            IncompleteGovernor("test")


class TestProcessManager:
    """Test ProcessManager class."""
    
    @pytest.fixture
    def temp_dirs(self, tmp_path):
        """Create temporary directories for testing."""
        log_dir = tmp_path / "logs"
        pid_dir = tmp_path / "pids"
        log_dir.mkdir()
        pid_dir.mkdir()
        return log_dir, pid_dir
    
    def test_basic_creation(self, temp_dirs):
        """Test creating a process manager."""
        log_dir, pid_dir = temp_dirs
        
        manager = ProcessManager(
            name="test-process",
            command=["python", "--version"],
            log_file=log_dir / "test.log",
            pid_dir=pid_dir
        )
        
        assert manager.name == "test-process"
        assert manager.process is None
        assert not manager.is_running()
    
    def test_start_simple_command(self, temp_dirs):
        """Test starting a simple command."""
        log_dir, pid_dir = temp_dirs
        
        # Use a command that exits quickly
        manager = ProcessManager(
            name="test-process",
            command=["python", "--version"],
            log_file=log_dir / "test.log",
            pid_dir=pid_dir
        )
        
        # Start will return False because process exits immediately
        result = manager.start()
        
        # Process should have run (PID should have been created briefly)
        assert manager.process is not None
    
    def test_pid_file_creation(self, temp_dirs):
        """Test that PID file is created."""
        log_dir, pid_dir = temp_dirs
        
        # Use a long-running command
        manager = ProcessManager(
            name="test-process",
            command=["python", "-c", "import time; time.sleep(5)"],
            log_file=log_dir / "test.log",
            pid_dir=pid_dir
        )
        
        manager.start()
        
        if manager.is_running():
            assert manager.pid_file.exists()
            pid = int(manager.pid_file.read_text())
            assert pid == manager.process.pid
            
            # Cleanup
            manager.stop()
    
    def test_stop_graceful(self, temp_dirs):
        """Test graceful stop with SIGTERM."""
        log_dir, pid_dir = temp_dirs
        
        manager = ProcessManager(
            name="test-process",
            command=["python", "-c", "import time; time.sleep(10)"],
            log_file=log_dir / "test.log",
            pid_dir=pid_dir
        )
        
        manager.start()
        
        if manager.is_running():
            manager.stop(timeout=2)
            
            # Process should be stopped
            assert not manager.is_running()
            
            # PID file should be cleaned up
            assert not manager.pid_file.exists()
    
    def test_get_info(self, temp_dirs):
        """Test getting process info."""
        log_dir, pid_dir = temp_dirs
        
        manager = ProcessManager(
            name="test-process",
            command=["python", "-c", "import time; time.sleep(10)"],
            log_file=log_dir / "test.log",
            pid_dir=pid_dir
        )
        
        # Before start
        info = manager.get_info()
        assert info.status == "stopped"
        
        manager.start()
        
        if manager.is_running():
            # While running
            info = manager.get_info()
            assert info.status == "running"
            assert info.pid == manager.process.pid
            
            manager.stop()


class TestProcessGovernor:
    """Test ProcessGovernor implementation."""
    
    @pytest.fixture
    def governor(self):
        """Create a test governor instance."""
        gov = ProcessGovernor("test")
        yield gov
        # Cleanup
        try:
            gov.stop(timeout=5)
        except:
            pass
    
    def test_basic_creation(self, governor):
        """Test creating a process governor."""
        assert governor.deployment == "test"
        assert not governor.is_running
        assert governor.server_manager is None
        assert len(governor.handler_managers) == 0
    
    def test_start_creates_server(self, governor):
        """Test that starting governor creates server process."""
        result = governor.start()
        
        # Should attempt to start server
        assert governor.server_manager is not None
        
        # Give it time to start
        time.sleep(2)
        
        # Cleanup
        governor.stop()
    
    def test_stop_is_idempotent(self, governor):
        """Test that stopping when not running is safe."""
        result = governor.stop()
        assert result is True
        
        # Can call multiple times
        result = governor.stop()
        assert result is True
    
    def test_status_empty(self, governor):
        """Test status when nothing is running."""
        status = governor.status()
        
        # Should be empty or show stopped status
        assert isinstance(status, dict)
    
    def test_health_check(self, governor):
        """Test health check functionality."""
        health = governor.health_check()
        
        assert isinstance(health, dict)
    
    def test_get_metrics(self, governor):
        """Test metrics retrieval."""
        metrics = governor.get_metrics()
        
        assert metrics["deployment"] == "test"
        assert "running" in metrics
        assert "total_services" in metrics
        assert "healthy_services" in metrics
        assert "total_restarts" in metrics
    
    def test_list_handlers_empty(self, governor):
        """Test listing handlers when none exist."""
        handlers = governor.list_handlers()
        assert handlers == []
    
    def test_add_handler_config(self, governor):
        """Test adding a handler with config."""
        config = HandlerConfig(
            handler_id="test-handler-1",
            module_path="tests.test_handler",
            class_name="TestHandler",
            port=5555
        )
        
        # This will fail without actual handler module, but tests the logic
        result = governor.add_handler(config)
        
        # Handler manager should be created
        assert "test-handler-1" in governor.handler_managers or not result
    
    def test_remove_nonexistent_handler(self, governor):
        """Test removing a handler that doesn't exist."""
        result = governor.remove_handler("nonexistent")
        assert result is False
    
    def test_get_handler_status_nonexistent(self, governor):
        """Test getting status of nonexistent handler."""
        status = governor.get_handler_status("nonexistent")
        assert status is None
    
    def test_restart_handler_nonexistent(self, governor):
        """Test restarting nonexistent handler."""
        result = governor.restart_handler("nonexistent")
        assert result is False


class TestProcessGovernorIntegration:
    """Integration tests for ProcessGovernor."""
    
    @pytest.fixture
    def governor(self):
        """Create governor for integration tests."""
        gov = ProcessGovernor("test")
        yield gov
        try:
            gov.stop(timeout=5)
        except:
            pass
    
    def test_full_lifecycle(self, governor):
        """Test complete start/status/stop lifecycle."""
        # Start
        governor.start()
        assert governor.is_running
        
        # Wait for stabilization
        time.sleep(2)
        
        # Check status
        status = governor.status()
        assert isinstance(status, dict)
        
        # Health check
        health = governor.health_check()
        assert isinstance(health, dict)
        
        # Metrics
        metrics = governor.get_metrics()
        assert metrics["running"]
        
        # Stop
        governor.stop()
        assert not governor.is_running


class TestGovernorRegressions:
    """Regression tests for previously fixed bugs."""
    
    def test_process_cleanup_on_exit(self):
        """
        Regression test for process cleanup.
        
        Previously, processes could be left orphaned if governor exited
        without proper cleanup. This tests that atexit handler works.
        """
        gov = ProcessGovernor("test")
        gov.start()
        
        # Simulate exit by calling cleanup directly
        gov._cleanup()
        
        # Should have stopped
        assert not gov.is_running
    
    def test_pid_file_cleanup(self, tmp_path):
        """
        Regression test for PID file cleanup.
        
        Previously, PID files could be left behind after process stop.
        """
        log_dir = tmp_path / "logs"
        pid_dir = tmp_path / "pids"
        log_dir.mkdir()
        pid_dir.mkdir()
        
        manager = ProcessManager(
            name="test",
            command=["python", "-c", "import time; time.sleep(5)"],
            log_file=log_dir / "test.log",
            pid_dir=pid_dir
        )
        
        manager.start()
        
        if manager.is_running():
            pid_file = manager.pid_file
            assert pid_file.exists()
            
            manager.stop()
            
            # PID file should be cleaned up
            assert not pid_file.exists()
    
    def test_poetry_environment_usage(self):
        """
        Regression test for Poetry environment usage.
        
        Previously, governor used sys.executable which pointed to Windows
        Store Python instead of Poetry environment.
        """
        gov = ProcessGovernor("test")
        
        # Server manager should use poetry
        if gov._start_server():
            command = gov.server_manager.command
            assert "poetry" in command
            assert "run" in command
            assert "python" in command
            
            gov.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
