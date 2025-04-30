import pytest
import time
from kvm_mcp_server import VMInfoCache

def test_vm_info_cache_initialization():
    """Test the initialization of the VM info cache"""
    cache = VMInfoCache(max_size=10, ttl=30)
    assert cache.max_size == 10
    assert cache.ttl == 30
    assert len(cache.cache) == 0
    assert len(cache.timestamps) == 0

def test_vm_info_cache_set_get():
    """Test setting and getting VM info from the cache"""
    cache = VMInfoCache()
    vm_info = {"name": "test-vm", "state": "running"}
    
    # Test setting and getting valid data
    cache.set("test-vm", vm_info)
    assert cache.get("test-vm") == vm_info
    
    # Test getting non-existent data
    assert cache.get("non-existent") is None

def test_vm_info_cache_expiration():
    """Test cache entry expiration"""
    cache = VMInfoCache(ttl=0.1)  # Very short TTL for testing
    vm_info = {"name": "test-vm", "state": "running"}
    
    cache.set("test-vm", vm_info)
    assert cache.get("test-vm") == vm_info
    
    # Wait for expiration
    time.sleep(0.2)
    assert cache.get("test-vm") is None

def test_vm_info_cache_max_size():
    """Test cache size limit"""
    cache = VMInfoCache(max_size=2)
    
    # Add three items
    cache.set("vm1", {"name": "vm1"})
    cache.set("vm2", {"name": "vm2"})
    cache.set("vm3", {"name": "vm3"})
    
    # Oldest item should be removed
    assert cache.get("vm1") is None
    assert cache.get("vm2") is not None
    assert cache.get("vm3") is not None

def test_vm_info_cache_invalidate():
    """Test cache invalidation"""
    cache = VMInfoCache()
    
    # Add multiple items
    cache.set("vm1", {"name": "vm1"})
    cache.set("vm2", {"name": "vm2"})
    
    # Test invalidating specific item
    cache.invalidate("vm1")
    assert cache.get("vm1") is None
    assert cache.get("vm2") is not None
    
    # Test invalidating all items
    cache.invalidate()
    assert cache.get("vm1") is None
    assert cache.get("vm2") is None

def test_vm_info_cache_concurrent_access():
    """Test concurrent access to the cache"""
    import threading
    
    cache = VMInfoCache()
    num_threads = 5
    results = []
    
    def worker(thread_id):
        vm_name = f"vm-{thread_id}"
        vm_info = {"name": vm_name, "thread": thread_id}
        cache.set(vm_name, vm_info)
        results.append(cache.get(vm_name))
    
    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # Verify all threads could set and retrieve their data
    assert len(results) == num_threads
    for i in range(num_threads):
        assert any(r["thread"] == i for r in results) 