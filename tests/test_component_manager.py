"""Test ComponentManager."""
import asyncio
import pytest

from schedule_zero.component_manager import ComponentManager, load_component_config


@pytest.mark.asyncio
async def test_load_default_config():
    """Test loading default configuration."""
    config = load_component_config("default")
    
    assert config['deployment']['name'] == 'default'
    assert config['deployment']['mode'] == 'full'
    assert config['components']['tornado']['enabled'] is True
    assert config['components']['scheduler']['enabled'] is True


@pytest.mark.asyncio
async def test_start_scheduler_only():
    """Test starting just the scheduler component."""
    config = {
        'components': {
            'scheduler': {
                'enabled': True,
                'datastore': {
                    'type': 'memory'
                }
            },
            'event_broker': {
                'enabled': False
            },
            'tornado': {
                'enabled': False
            },
            'handlers': {
                'local': {'enabled': False},
                'remote': {'enabled': False}
            },
            'zmq_client': {
                'enabled': False
            }
        }
    }
    
    manager = ComponentManager(config)
    
    async with manager:
        assert manager.components['scheduler'] is not None
        assert manager.components['tornado'] is None
        assert manager.components['local_handlers'] is None


@pytest.mark.asyncio
async def test_start_scheduler_with_event_broker():
    """Test starting scheduler with ZMQ event broker."""
    config = {
        'components': {
            'scheduler': {
                'enabled': True,
                'datastore': {
                    'type': 'memory'
                }
            },
            'event_broker': {
                'enabled': True,
                'type': 'zmq',
                'publish_address': 'tcp://127.0.0.1:15570',
                'subscribe_addresses': [],
                'instance_id': 'test-instance'
            },
            'tornado': {
                'enabled': False
            },
            'handlers': {
                'local': {'enabled': False},
                'remote': {'enabled': False}
            },
            'zmq_client': {
                'enabled': False
            }
        }
    }
    
    manager = ComponentManager(config)
    
    async with manager:
        scheduler = manager.components['scheduler']
        assert scheduler is not None
        assert scheduler.event_broker is not None
        assert scheduler.event_broker.instance_id == 'test-instance'


@pytest.mark.asyncio
async def test_start_local_handlers():
    """Test starting local handler registry."""
    config = {
        'components': {
            'scheduler': {
                'enabled': False
            },
            'tornado': {
                'enabled': False
            },
            'handlers': {
                'local': {
                    'enabled': True,
                    'modules': []  # No modules to import for testing
                },
                'remote': {
                    'enabled': False
                }
            },
            'zmq_client': {
                'enabled': False
            }
        }
    }
    
    manager = ComponentManager(config)
    
    async with manager:
        assert manager.components['local_handlers'] is not None
        
        # Register a test handler
        def test_func():
            return "test"
        
        manager.components['local_handlers'].register("test", test_func)
        result = await manager.components['local_handlers'].execute("test", "test_func")
        assert result == "test"


@pytest.mark.asyncio
async def test_minimal_mode():
    """Test minimal mode (scheduler + local handlers only)."""
    config = {
        'deployment': {
            'mode': 'minimal'
        },
        'components': {
            'tornado': {
                'enabled': False
            },
            'scheduler': {
                'enabled': True,
                'datastore': {
                    'type': 'memory'
                }
            },
            'event_broker': {
                'enabled': False
            },
            'handlers': {
                'local': {
                    'enabled': True,
                    'modules': []
                },
                'remote': {
                    'enabled': False
                }
            },
            'zmq_client': {
                'enabled': False
            }
        }
    }
    
    manager = ComponentManager(config)
    
    async with manager:
        # Scheduler and local handlers should be running
        assert manager.components['scheduler'] is not None
        assert manager.components['local_handlers'] is not None
        
        # Remote components should be disabled
        assert manager.components['tornado'] is None
        assert manager.components['remote_handlers'] is None
        assert manager.components['zmq_client'] is None


@pytest.mark.asyncio
async def test_autonomous_mode_config():
    """Test autonomous mode configuration."""
    config = {
        'deployment': {
            'mode': 'autonomous'
        },
        'components': {
            'tornado': {
                'enabled': False  # No web UI
            },
            'scheduler': {
                'enabled': True,
                'datastore': {
                    'type': 'sqlite',
                    'path': 'test_autonomous.db'
                }
            },
            'event_broker': {
                'enabled': False  # Single instance
            },
            'handlers': {
                'local': {
                    'enabled': True,
                    'modules': []
                },
                'remote': {
                    'enabled': False
                }
            },
            'zmq_client': {
                'enabled': False  # Can be true to connect to central
            }
        }
    }
    
    manager = ComponentManager(config)
    
    async with manager:
        # Autonomous: scheduler + local handlers
        assert manager.components['scheduler'] is not None
        assert manager.components['local_handlers'] is not None
        
        # No web UI or remote components
        assert manager.components['tornado'] is None
        assert manager.components['remote_handlers'] is None


@pytest.mark.asyncio
async def test_component_count():
    """Test that component count is reported correctly."""
    config = {
        'components': {
            'tornado': {'enabled': False},
            'scheduler': {
                'enabled': True,
                'datastore': {'type': 'memory'}
            },
            'event_broker': {'enabled': False},
            'handlers': {
                'local': {'enabled': True, 'modules': []},
                'remote': {'enabled': False}
            },
            'zmq_client': {'enabled': False}
        }
    }
    
    manager = ComponentManager(config)
    
    async with manager:
        enabled = [c for c in manager.components.values() if c is not None]
        # Should have scheduler + local_handlers = 2
        assert len(enabled) == 2


if __name__ == "__main__":
    # Run tests manually
    asyncio.run(test_load_default_config())
    print("✓ Load default config test passed")
    
    asyncio.run(test_start_scheduler_only())
    print("✓ Start scheduler only test passed")
    
    asyncio.run(test_start_scheduler_with_event_broker())
    print("✓ Start scheduler with event broker test passed")
    
    asyncio.run(test_start_local_handlers())
    print("✓ Start local handlers test passed")
    
    asyncio.run(test_minimal_mode())
    print("✓ Minimal mode test passed")
    
    asyncio.run(test_autonomous_mode_config())
    print("✓ Autonomous mode config test passed")
    
    asyncio.run(test_component_count())
    print("✓ Component count test passed")
    
    print("\n✅ All ComponentManager tests passed!")
