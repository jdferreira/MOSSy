# This file recursively imports all the plugins (.py files or folders containing
# __init__.py files in them)

import os
import importlib

dirname = os.path.dirname(__file__)
for filename in os.listdir(dirname):
    fullpath = os.path.join(dirname, filename)
    
    if os.path.isdir(fullpath):
        if '__init__.py' in os.listdir(fullpath):
            module_name = "mossy.plugins." + filename
            importlib.import_module(filename)
    else:
        if filename.endswith('.py') and not filename.startswith('_'):
            module_name = "mossy.plugins." + filename[:-3]
            importlib.import_module(module_name)

# Note: Proper logging is required!
