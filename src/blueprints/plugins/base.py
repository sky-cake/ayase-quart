import importlib
import pkgutil
from quart import Quart


def register_blueprint_plugins(app: Quart) -> None:
    package_module = importlib.import_module('blueprints.plugins')

    for _, module_name, is_pkg in pkgutil.iter_modules(package_module.__path__, package_module.__name__ + '.'):
        if not module_name.split('.')[-1].startswith('plugin_'):
            continue

        module = importlib.import_module(module_name)
        
        if hasattr(module, 'bp'):
            print(f'Loading bp plugin: {module_name}')
            app.register_blueprint(module.bp)
