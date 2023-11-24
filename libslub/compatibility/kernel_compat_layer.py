import gdb
import re 

class KernelCompatibilityLayer:
    """This class provides a compatibility layer to support multiple kernel versions
    
    In versions preceding 5.17, details about a slab (if the page is part of a slab) 
    are stored in an anonymous union within the page object. Starting from version 5.17, 
    the slab_cache, freelist, and other members related to slabs have been relocated to a distinct slab object.
    """
    

    def __init__(self, release=None):
        self.release = release
        if self.release is None:
            self.release = get_kernel_version()
        if self.release < "5.17":
            self.slab_or_page = "page"
            self.slab_type = gdb.lookup_type("struct page")
            self.slab_list = "lru"
        else:
            self.slab_or_page = "slab"
            self.slab_type = gdb.lookup_type("struct slab")
            self.slab_list = "slab_list"
        
        
        
    
def get_kernel_version():
    """read the current kernel version using gdb
    """
    version_string = gdb.parse_and_eval("(char *)linux_banner").string()
    release = re.search(r'(\d+\.\d+\.\d+)', version_string).group(1)
    return release