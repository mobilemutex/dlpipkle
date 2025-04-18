#!/usr/bin/env python3
"""
Platform utilities module for dlpipkle.

This module provides functionality to identify and list available platforms
for Python packages on PyPI, helping users select the appropriate platform
when downloading packages.
"""

import re
import json
import platform
import urllib.request
from typing import Dict, List, Optional, Set, Any, Tuple


class InvalidFilenameError(Exception):
    """Exception raised when a wheel filename cannot be parsed."""
    def __init__(self, filename: str):
        self.filename = filename
        super().__init__(f"Invalid wheel filename: {filename}")


def parse_wheel_filename(filename: str) -> Set[str]:
    """
    Parse wheel filename to extract platform tags.
    
    Args:
        filename: The wheel filename to parse
        
    Returns:
        Set of platform tags
        
    Raises:
        InvalidFilenameError: If the filename is not a valid wheel filename
    """
    # Wheel filename format: {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
    wheel_file_re = re.compile(
        r"^(?P<namever>.+?)-(?P<pyver>.+?)-(?P<abi>.+?)-(?P<plat>.+?)\.whl$",
        re.IGNORECASE
    )
    match = wheel_file_re.match(filename)
    if not match:
        raise InvalidFilenameError(filename)
    
    platform_tag = match.group('plat')
    # Platform tag can be multiple tags separated by '.'
    platform_tags = platform_tag.split('.')
    return set(platform_tags)


def get_package_info(package_name: str, package_version: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch package information from PyPI JSON API.
    
    Args:
        package_name: The name of the package to fetch information for
        package_version: Optional specific version to fetch information for
        
    Returns:
        Dictionary containing package information from PyPI
        
    Raises:
        urllib.error.HTTPError: If the package or version cannot be found
    """
    if package_version:
        url = f"https://pypi.org/pypi/{package_name}/{package_version}/json"
    else:
        url = f"https://pypi.org/pypi/{package_name}/json"
    
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode('utf-8'))


def list_platforms(package_name: str, version: Optional[str] = None) -> Set[str]:
    """
    List all available platforms for a specific package version.
    
    Args:
        package_name: The name of the package to list platforms for
        version: Optional specific version to list platforms for
        
    Returns:
        Set of platform tags available for the package
    """
    platforms = set()
    pkg_info = get_package_info(package_name, version)
    releases = pkg_info.get('releases', {})
    
    # If version is specified, only look at that version
    if version and version in releases:
        versions_to_check = {version: releases[version]}
    # Otherwise, look at all versions
    else:
        versions_to_check = releases
    
    for release_version, files in versions_to_check.items():
        for file_info in files:
            filename = file_info.get('filename', '')
            if filename.endswith('.whl'):
                try:
                    platforms.update(parse_wheel_filename(filename))
                except InvalidFilenameError:
                    continue
            else:
                # Source distributions
                platforms.add('source')
    
    return platforms


def get_current_platform() -> str:
    """
    Get the platform tag for the current system.
    
    This is a simplified version that returns a platform tag that can be used
    with pip's --platform option. For a more accurate platform tag, the
    packaging library should be used.
    
    Returns:
        Platform tag for the current system
    """
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == 'windows':
        if machine == 'amd64' or machine == 'x86_64':
            return 'win_amd64'
        elif machine == 'x86' or machine == 'i386':
            return 'win32'
        else:
            return f'win_{machine}'
    
    elif system == 'darwin':
        # macOS platform tags are more complex, this is simplified
        if machine == 'x86_64':
            return 'macosx_10_9_x86_64'
        elif machine == 'arm64':
            return 'macosx_11_0_arm64'
        else:
            return f'macosx_{machine}'
    
    elif system == 'linux':
        # Linux platform tags are complex due to manylinux standard
        # This is a simplified version
        if machine == 'x86_64':
            return 'manylinux2014_x86_64'
        elif machine == 'aarch64':
            return 'manylinux2014_aarch64'
        else:
            return f'linux_{machine}'
    
    # Default fallback
    return f'{system}_{machine}'


def get_python_tag() -> str:
    """
    Get the Python implementation and version tag for the current Python.
    
    Returns:
        Python tag (e.g., 'cp39' for CPython 3.9)
    """
    implementation = platform.python_implementation().lower()
    version = platform.python_version_tuple()
    
    impl_map = {
        'cpython': 'cp',
        'pypy': 'pp',
        'ironpython': 'ip',
        'jython': 'jy'
    }
    
    impl_tag = impl_map.get(implementation, implementation[:2])
    version_tag = ''.join(version[:2])  # Major and minor version
    
    return f"{impl_tag}{version_tag}"


def get_abi_tag() -> str:
    """
    Get the ABI tag for the current Python.
    
    This is a simplified version that returns a basic ABI tag.
    For a more accurate ABI tag, the packaging library should be used.
    
    Returns:
        ABI tag (e.g., 'cp39' for CPython 3.9)
    """
    # For simplicity, we just use the Python tag
    # In reality, the ABI tag is more complex and depends on build flags
    return get_python_tag()


def categorize_platforms(platforms: Set[str]) -> Dict[str, List[str]]:
    """
    Categorize platform tags into groups.
    
    Args:
        platforms: Set of platform tags
        
    Returns:
        Dictionary mapping platform categories to lists of platform tags
    """
    categories = {
        'Windows': [],
        'macOS': [],
        'Linux': [],
        'Other': []
    }
    
    for plat in platforms:
        if plat == 'any' or plat == 'source':
            categories['Other'].append(plat)
        elif plat.startswith('win'):
            categories['Windows'].append(plat)
        elif plat.startswith('macosx'):
            categories['macOS'].append(plat)
        elif plat.startswith('manylinux') or plat.startswith('linux'):
            categories['Linux'].append(plat)
        else:
            categories['Other'].append(plat)
    
    # Remove empty categories
    return {k: sorted(v) for k, v in categories.items() if v}


def print_platform_compatibility(package_name: str, version: Optional[str] = None) -> None:
    """
    Print platform compatibility information for a package.
    
    Args:
        package_name: The name of the package to check
        version: Optional specific version to check
    """
    try:
        platforms = list_platforms(package_name, version)
        current_platform = get_current_platform()
        
        print(f"Platform compatibility for {package_name}{f' {version}' if version else ''}:")
        
        categories = categorize_platforms(platforms)
        
        for category, plats in categories.items():
            print(f"\n{category}:")
            for plat in plats:
                is_current = plat == current_platform
                print(f"  - {plat}{' (current)' if is_current else ''}")
        
        if current_platform in platforms:
            print(f"\nPackage is compatible with your current platform ({current_platform}).")
        elif 'any' in platforms:
            print("\nPackage is compatible with any platform.")
        elif 'source' in platforms:
            print("\nSource distribution is available, which can be built for your platform.")
        else:
            print(f"\nWarning: No direct compatibility with your platform ({current_platform}).")
            print("You may need to build from source or use a different package version.")
    
    except urllib.error.HTTPError as e:
        print(f"Error: Could not find package {package_name}{f' {version}' if version else ''} on PyPI.")
        print(f"HTTP Error: {e.code} {e.reason}")
    except Exception as e:
        print(f"Error checking platform compatibility: {e}")


def suggest_platform_option(package_name: str, version: Optional[str] = None) -> Optional[str]:
    """
    Suggest a platform option for downloading a package.
    
    This function tries to find the best platform option for the current system.
    
    Args:
        package_name: The name of the package to check
        version: Optional specific version to check
        
    Returns:
        Suggested platform option or None if no suitable platform is found
    """
    try:
        platforms = list_platforms(package_name, version)
        current_platform = get_current_platform()
        
        # First, check if the current platform is available
        if current_platform in platforms:
            return current_platform
        
        # If not, try to find a compatible platform
        # This is a simplified version that just checks for platform prefixes
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        if system == 'linux' and machine == 'x86_64':
            for plat in platforms:
                if plat.endswith('x86_64') and ('manylinux' in plat or 'linux' in plat):
                    return plat
        
        elif system == 'windows':
            for plat in platforms:
                if plat.startswith('win'):
                    return plat
        
        elif system == 'darwin':
            for plat in platforms:
                if plat.startswith('macosx'):
                    return plat
        
        # If no compatible platform is found, check if 'any' is available
        if 'any' in platforms:
            return 'any'
        
        # If only source is available, return None
        return None
    
    except Exception:
        return None


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python platform_utils.py PACKAGE_NAME [VERSION]")
        sys.exit(1)
    
    package = sys.argv[1]
    version = sys.argv[2] if len(sys.argv) > 2 else None
    
    print_platform_compatibility(package, version)
