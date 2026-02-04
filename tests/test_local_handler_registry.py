"""Test local handler registry."""
import asyncio
import pytest

from schedule_zero.local_handler_registry import (
    LocalHandlerRegistry,
    local_handler,
    register_local,
    default_local_registry
)


def sync_add(a, b):
    """Synchronous test handler."""
    return a + b


async def async_multiply(a, b):
    """Asynchronous test handler."""
    await asyncio.sleep(0.01)  # Simulate async work
    return a * b


@pytest.mark.asyncio
async def test_register_sync_function():
    """Test registering a synchronous function."""
    registry = LocalHandlerRegistry()
    
    success = registry.register("math_add", sync_add, ["add"])
    assert success
    
    # Execute the handler
    result = await registry.execute("math_add", "add", 5, 3)
    assert result == 8
    
    # Check handler info
    info = registry.get_handler("math_add")
    assert info is not None
    assert info['methods'] == ["add"]
    assert info['is_async'] is False
    assert info['type'] == 'local'


@pytest.mark.asyncio
async def test_register_async_function():
    """Test registering an asynchronous function."""
    registry = LocalHandlerRegistry()
    
    success = registry.register("math_multiply", async_multiply, ["multiply"])
    assert success
    
    # Execute the handler
    result = await registry.execute("math_multiply", "multiply", 6, 7)
    assert result == 42
    
    # Check handler info
    info = registry.get_handler("math_multiply")
    assert info is not None
    assert info['is_async'] is True


@pytest.mark.asyncio
async def test_decorator_registration():
    """Test using the decorator for registration."""
    registry = LocalHandlerRegistry()
    
    @local_handler(registry, handler_id="greeting", methods=["greet"])
    def say_hello(name):
        return f"Hello, {name}!"
    
    # Function should still work normally
    assert say_hello("World") == "Hello, World!"
    
    # Should also be registered
    result = await registry.execute("greeting", "greet", "Alice")
    assert result == "Hello, Alice!"


@pytest.mark.asyncio
async def test_default_method_name():
    """Test that method name defaults to function name."""
    registry = LocalHandlerRegistry()
    
    def calculate_total(items):
        return sum(items)
    
    registry.register("calculator", calculate_total)  # No methods specified
    
    info = registry.get_handler("calculator")
    assert info['methods'] == ["calculate_total"]
    
    result = await registry.execute("calculator", "calculate_total", [1, 2, 3, 4])
    assert result == 10


@pytest.mark.asyncio
async def test_unregister_handler():
    """Test unregistering a handler."""
    registry = LocalHandlerRegistry()
    
    registry.register("temp_handler", sync_add)
    assert registry.get_handler("temp_handler") is not None
    
    success = registry.unregister("temp_handler")
    assert success
    assert registry.get_handler("temp_handler") is None
    
    # Trying to unregister again should return False
    success = registry.unregister("temp_handler")
    assert not success


@pytest.mark.asyncio
async def test_handler_not_found():
    """Test error handling when handler not found."""
    registry = LocalHandlerRegistry()
    
    with pytest.raises(KeyError, match="Handler 'nonexistent' not found"):
        await registry.execute("nonexistent", "some_method")


@pytest.mark.asyncio
async def test_method_not_supported():
    """Test error handling when method not in handler's methods list."""
    registry = LocalHandlerRegistry()
    
    registry.register("limited_handler", sync_add, ["add_only"])
    
    with pytest.raises(ValueError, match="Method 'subtract' not in handler methods"):
        await registry.execute("limited_handler", "subtract", 5, 3)


@pytest.mark.asyncio
async def test_get_all_handlers():
    """Test getting list of all handlers."""
    registry = LocalHandlerRegistry()
    
    registry.register("handler1", sync_add, ["add"])
    registry.register("handler2", async_multiply, ["multiply"])
    
    all_handlers = registry.get_all_handlers()
    assert len(all_handlers) == 2
    
    handler_ids = {h['id'] for h in all_handlers}
    assert handler_ids == {"handler1", "handler2"}
    
    # Check types
    for handler in all_handlers:
        assert handler['type'] == 'local'


@pytest.mark.asyncio
async def test_global_registry_decorator():
    """Test using the global registry decorator."""
    # Note: This modifies global state, but for testing purposes it's okay
    
    @register_local(handler_id="global_test", methods=["test_method"])
    def global_test_func(x):
        return x * 2
    
    result = await default_local_registry.execute("global_test", "test_method", 21)
    assert result == 42
    
    # Cleanup
    default_local_registry.unregister("global_test")


@pytest.mark.asyncio
async def test_handler_with_kwargs():
    """Test handler execution with keyword arguments."""
    registry = LocalHandlerRegistry()
    
    def formatter(template, name, age):
        return template.format(name=name, age=age)
    
    registry.register("formatter", formatter)
    
    result = await registry.execute(
        "formatter",
        "formatter",
        "{name} is {age} years old",
        name="Bob",
        age=30
    )
    assert result == "Bob is 30 years old"


if __name__ == "__main__":
    # Run tests manually
    asyncio.run(test_register_sync_function())
    print("✓ Sync function registration test passed")
    
    asyncio.run(test_register_async_function())
    print("✓ Async function registration test passed")
    
    asyncio.run(test_decorator_registration())
    print("✓ Decorator registration test passed")
    
    asyncio.run(test_default_method_name())
    print("✓ Default method name test passed")
    
    asyncio.run(test_unregister_handler())
    print("✓ Unregister handler test passed")
    
    asyncio.run(test_handler_not_found())
    print("✓ Handler not found test passed")
    
    asyncio.run(test_method_not_supported())
    print("✓ Method not supported test passed")
    
    asyncio.run(test_get_all_handlers())
    print("✓ Get all handlers test passed")
    
    asyncio.run(test_global_registry_decorator())
    print("✓ Global registry decorator test passed")
    
    asyncio.run(test_handler_with_kwargs())
    print("✓ Handler with kwargs test passed")
    
    print("\n✅ All local handler tests passed!")
