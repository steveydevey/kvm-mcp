import time
import logging

logger = logging.getLogger('kvm_mcp')

class VMInfoCache:
    """A simple LRU cache for VM information."""
    
    def __init__(self, max_size=50, ttl=60):
        self.max_size = max_size
        self.ttl = ttl
        self.cache = {}
        self.timestamps = {}
    
    def get(self, vm_name):
        """Get a VM's info from the cache if available and not expired."""
        if vm_name in self.cache:
            if time.time() - self.timestamps[vm_name] < self.ttl:
                return self.cache[vm_name]
            # Expired
            del self.cache[vm_name]
            del self.timestamps[vm_name]
        return None
    
    def set(self, vm_name, vm_info):
        """Set a VM's info in the cache."""
        # Remove oldest item if full
        if len(self.cache) >= self.max_size:
            oldest_vm = min(self.timestamps.items(), key=lambda x: x[1])[0]
            del self.cache[oldest_vm]
            del self.timestamps[oldest_vm]
        
        self.cache[vm_name] = vm_info
        self.timestamps[vm_name] = time.time()
    
    def invalidate(self, vm_name=None):
        """Invalidate cache entry for a VM or the entire cache."""
        if vm_name:
            if vm_name in self.cache:
                del self.cache[vm_name]
                del self.timestamps[vm_name]
        else:
            self.cache.clear()
            self.timestamps.clear()

# Create a global VM info cache instance
vm_info_cache = VMInfoCache() 