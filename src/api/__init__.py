import importlib
from pathlib import Path
from fastapi import APIRouter
from src.utils import logger

main_router = APIRouter(prefix="/api")

current_dir = Path(__file__).parent

# Iterate through all items in the current directory
for item in current_dir.iterdir():
    module_name = None
    module_path = None

    # Handle Python files (excluding private modules)
    if item.is_file() and item.suffix == ".py" and not item.name.startswith("_"):
        module_name = item.stem
        module_path = f"{__package__}.{module_name}"

    # Handle directories with __init__.py (subpackages)
    elif item.is_dir() and not item.name.startswith("_"):
        init_file = item / "__init__.py"
        if init_file.exists():
            module_name = item.name
            module_path = f"{__package__}.{module_name}"

    # Try to import and include the router
    if module_path:
        try:
            module = importlib.import_module(module_path)
            router = getattr(module, "router", None)
            if router:
                main_router.include_router(router)
        except Exception as e:
            logger.error(f"Could not import {module_path}: {e}")
            ...
