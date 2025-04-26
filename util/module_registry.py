import os
import importlib.util as importlib_util
import inspect

class ModuleRegistry:
    def __init__(self):
        self.modules = {}

    def register(self, module_name, module_instance):
        """Register a module instance with a given name."""
        self.modules[module_name] = module_instance

    def load_modules(self, modules_dir):
        """Load all modules from the specified directory, respecting load_after dependencies."""
        modules_to_load = {}

        # Discover all modules and their classes
        for filename in os.listdir(modules_dir):
            if filename.endswith(".py"):
                module_name = filename[:-3]
                module_path = os.path.join(modules_dir, filename)
                spec = importlib_util.spec_from_file_location(module_name, module_path)
                module = importlib_util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Look for a class with the same name as the module
                for _, obj in inspect.getmembers(module, inspect.isclass):
                    if obj.__module__ == module_name:
                        modules_to_load[module_name] = obj

        # Load modules in the correct order
        loaded_modules = set()
        while modules_to_load:
            loaded_in_iteration = False
            for module_name, module_class in list(modules_to_load.items()):
                # Check if the module has a load_after attribute
                load_after = getattr(module_class, "load_after", [])
                if all(dep in loaded_modules for dep in load_after):
                    # Instantiate the class and register it
                    module_instance = module_class()
                    self.register(module_name, module_instance)
                    loaded_modules.add(module_name)
                    del modules_to_load[module_name]
                    loaded_in_iteration = True

            if not loaded_in_iteration:
                # If no modules were loaded in this iteration, there is a circular dependency
                raise RuntimeError(
                    f"Circular dependency detected among modules: {', '.join(modules_to_load.keys())}"
                )

    def get_module(self, module_name):
        """Retrieve a registered module instance by name."""
        module_name = module_name.lower()
        if module_name in self.modules:
            return self.modules[module_name]
        else:
            raise ValueError(f"Module '{module_name}' not found.")

    def list_modules(self):
        """List all registered module names."""
        return list(self.modules.keys())


# Create a global instance of ModuleRegistry
module_registry = ModuleRegistry()