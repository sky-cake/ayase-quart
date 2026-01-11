import importlib
import pkgutil

from quart import Quart

from . import REPO_PKG


def register_blueprint_plugins(app: Quart) -> None:
    package_module = importlib.import_module(f'{REPO_PKG}.plugins.blueprints')

    for _, module_name, is_pkg in pkgutil.iter_modules(package_module.__path__, package_module.__name__ + '.'):
        module = importlib.import_module(module_name)

        if hasattr(module, 'bp'):
            print(f'Loading bp plugin: {module_name}')
            app.register_blueprint(module.bp)
