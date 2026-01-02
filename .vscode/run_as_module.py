import sys, os
import runpy

workspace_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if workspace_folder not in sys.path:
    sys.path.insert(0, workspace_folder)

file = sys.argv[1] if len(sys.argv) > 1 else None

if file:
    rel = os.path.relpath(file, workspace_folder)
    module_name = rel[:-3].replace(os.path.sep, '.') if rel.endswith('.py') else None
   
    if module_name:
        # print(module_name) 
        # os.execvp("python", ["python", "-m", module_name] + sys.argv[2:])
        runpy.run_module(module_name, run_name="__main__")