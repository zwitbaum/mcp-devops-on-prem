import importlib
import pathlib
import pkgutil

package_dir = pathlib.Path(__file__).parent
for finder, name, ispkg in pkgutil.iter_modules([str(package_dir)]):
    importlib.import_module(f"{__name__}.{name}")
