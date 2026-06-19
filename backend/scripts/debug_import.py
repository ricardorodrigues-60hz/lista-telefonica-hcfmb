import importlib
import traceback

try:
    m = importlib.import_module('app.core.init_db')
    print('OK', hasattr(m, 'seeds'))
    names = [n for n in dir(m) if not n.startswith('_')]
    print('names:', names)
except Exception:
    traceback.print_exc()
