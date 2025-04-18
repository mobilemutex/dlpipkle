"""Tool for downloading pip packages and their dependencies."""

__version__ = "0.1.0"

from .downloader import download_package
from .dependency_resolver import get_all_dependencies
from .platform_utils import list_platforms
