import os
import sys

# We reload all modules everywhere so when we develop libslub in gdb
# our changes are reflected as soon as we reimport this main script
import importlib

# Add the root path
module_path = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
if module_path not in sys.path:
    #print("DEBUG: adding module path...")
    sys.path.insert(0, module_path)
#print(sys.path) # DEBUG

# We need that after the above so it finds it
import libslub
importlib.reload(libslub)
