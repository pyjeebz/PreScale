import sys
import importlib.util
print('python:', sys.executable)
print('sys.path:')
for p in sys.path:
    print('  ', p)
print('\nuvicorn spec:', importlib.util.find_spec('uvicorn'))
print('fastapi spec:', importlib.util.find_spec('fastapi'))
if importlib.util.find_spec('uvicorn'):
    m = importlib.import_module('uvicorn')
    print('uvicorn version:', getattr(m, '__version__', 'unknown'))
if importlib.util.find_spec('fastapi'):
    m = importlib.import_module('fastapi')
    print('fastapi version:', getattr(m, '__version__', 'unknown'))
