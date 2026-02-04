from .logger import Logger
import os

logger = Logger(service_name=os.environ.get("SERVICE_NAME", "NAMELESS_SERVICE"))
