#!/usr/bin/env python3
"""
Dependency resolver module for dlpipkle.

This module provides functionality to resolve dependencies for Python packages
by querying the PyPI JSON API and building a complete dependency tree.
"""

import json
import re
import sys
import urllib.request
from typing import Dict, List, Optional, Set, Tuple, Any
from packaging.requirements import Requirement, InvalidRequirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version

class DependencyResolutionError(Exception):
    """Exception raised for errors in dependency resolution."""

NORMALIZE_REGEX = r"[-_.]+"

def normalize_package_name(name: str) -> str:
    """
    Normalize package name according to PEP 503 by replacing all 
    underscores, hyphens, and periods with a single hyphen..
    
    Args:
        name (str): The package name to normalize.
        
    Returns:
        str: The normalized package name.
    """
    return re.sub(NORMALIZE_REGEX, "-", name).lower()


def get_package_info(package_name: str, package_version: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch package information from PyPI JSON API.
    
    Args:
        package_name: The name of the package to fetch information for
        package_version: Optional specific version to fetch information for
        
    Returns:
        Dictionary containing package information from PyPI
    """
    normalized_name = normalize_package_name(package_name)
    
    if package_version:
        url = f"https://pypi.org/pypi/{normalized_name}/{package_version}/json"
    else:
        url = f"https://pypi.org/pypi/{normalized_name}/json"
    
    try:
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        #print(f"Error fetching package info for {normalized_name}: {e}")
        if package_version:
            #print(f"Trying without version constraint...")
            return get_package_info(normalized_name)
        print(f"Error fetching package info for {normalized_name}: {e}")
        return None


def parse_dependency_string(
    dep_string: str,
    extras: Optional[List[str]] = None,
    target_platform: Optional[str] = None,
    target_python_version: Optional[str] = None
) -> Optional[Tuple[str, Optional[str]]]:
    """
    Parse a dependency string with proper environment marker evaluation.

    Args:
        dep_string (str): The dependency string to parse
        extras (Optional([List[str]])): List of extra features to consider for the package
        target_platform (Optional[str]): Target platform name (e.g., 'win', 'linux', 'macos')
        target_python_version (Optional[str]): Target Python version in the format 'X.Y'

    Returns:
        Optional[Tuple[str, Optional[str]]]: A tuple containing the normalized package 
        name and its version constraint, or None if the dependency is not applicable 
        for the given environment.
    """
    try:
        req = Requirement(dep_string)
    except InvalidRequirement:
        return None

    # Handle environment markers
    if req.marker:
        env = {
            'sys_platform': '',
            'platform_system': '',
            'platform_machine': '',
            'python_version': target_python_version or f"{sys.version_info.major}.{sys.version_info.minor}",
            'extra': ''
        }

        # Set platform-specific values
        if target_platform:
            if 'win' in target_platform.lower():
                env.update({
                    'sys_platform': 'win32',
                    'platform_system': 'Windows'
                })
            elif 'linux' in target_platform.lower():
                env.update({
                    'sys_platform': 'linux',
                    'platform_system': 'Linux'
                })
            elif 'macos' in target_platform.lower():
                env.update({
                    'sys_platform': 'darwin',
                    'platform_system': 'Darwin'
                })

            if 'x86_64' in target_platform.lower() or 'amd64' in target_platform.lower():
                env['platform_machine'] = 'x86_64'
            elif 'aarch64' in target_platform.lower() or 'arm64' in target_platform.lower():
                env['platform_machine'] = 'aarch64'

        # Evaluate the marker
        if not req.marker.evaluate(environment=env):
            return None

    # Handle extras
    if req.extras:
        if not extras or not any(extra in req.extras for extra in extras):
            return None

    version_constraint = str(req.specifier) if req.specifier else None
    return normalize_package_name(req.name), version_constraint

def get_compatible_version(
    package_name: str,
    version_constraint: Optional[str],
    verbose: bool = False
) -> Optional[str]:
    """
    Find the latest version compatible with the given version constraints.
    
    Args:
        package_name (str): The name of the package.
        version_constraint (Optional[str]): Version constraint string.
        verbose (bool): Whether to print detailed output.
        
    Returns:
        Optional[str]: The latest compatible version or None if no compatible version is found.
    """
    try:
        pkg_info = get_package_info(package_name)
        versions = list(pkg_info.get('releases', {}).keys())
        
        if not versions:
            return None

        if version_constraint:
            try:
                specifier = SpecifierSet(version_constraint)
            except ValueError as e:
                if verbose:
                    print(f"Invalid version constraint: {version_constraint}. Error: {e}")
                return None

            compatible_versions = []
            for v in versions:
                try:
                    if specifier.contains(v, prereleases=False):
                        compatible_versions.append(Version(v))
                except ValueError as e:
                    if verbose:
                        print(f"Error evaluating version {v}: {e}")
                    continue

            if not compatible_versions:
                return None

            return str(max(compatible_versions))
        else:
            # Return latest version if no constraint
            return max((Version(v) for v in versions), default=None)
    except Exception as e:
        if verbose:
            print(f"Error getting compatible version for {package_name}: {e}")
        return None


def get_all_dependencies(
    package_name: str,
    version: Optional[str] = None,
    extras: Optional[List[str]] = None,
    visited: Optional[Dict[str, str]] = None,
    exclude: Optional[Set[str]] = None,
    target_platform: Optional[str] = None,
    target_python_version: Optional[str] = None,
    dependency_path: Optional[List[str]] = None,
    verbose: bool = False
) -> Dict[str, str]:
    """
    Recursively get all dependencies of a package with proper version resolution.
    
    Args:
        package_name (str): The name of the package.
        version (Optional[str]): Version of the package.
        extras (Optional[List[str]]): List of extras to include.
        visited (Optional[Dict[str, str]]): Dictionary of visited packages and their versions.
        exclude (Optional[Set[str]]): Set of package names to exclude from resolution.
        target_platform (Optional[str]): Target platform for dependency resolution.
        target_python_version (Optional[str]): Target Python version for dependency resolution.
        dependency_path (Optional[List[str]]): Path to track dependencies to detect circular references.
        verbose (bool): Whether to print detailed output.
        
    Returns:
        Dict[str, str]: Dictionary mapping package names to their resolved versions.
    """
    if visited is None:
        visited = {}
    if exclude is None:
        exclude = set()
    if dependency_path is None:
        dependency_path = []

    normalized_name = normalize_package_name(package_name)
    
    if normalized_name in exclude:
        return visited
        
    # Check for circular dependencies
    if normalized_name in dependency_path:
        if verbose:
            print(f"Circular dependency detected: {' -> '.join(dependency_path)} -> {normalized_name}")
        return visited
        
    if normalized_name in visited:
        return visited
        
    try:
        # Resolve version if not specified
        if not version:
            version = get_compatible_version(normalized_name, None, verbose)
            if not version:
                return visited

        # Check if we already have a compatible version
        existing_version = visited.get(normalized_name)
        if existing_version:
            try:
                if Version(version) <= Version(existing_version):
                    return visited
            except ValueError as e:
                if verbose:
                    print(f"Version comparison error: {e}")

        if verbose:
            print(f"Resolving {normalized_name}=={version}...")

        visited[normalized_name] = version
        pkg_info = get_package_info(normalized_name, version)
        requires_dist = pkg_info.get('info', {}).get('requires_dist', [])

        new_path = dependency_path + [normalized_name]

        for dep in requires_dist:
            parsed_dep = parse_dependency_string(
                dep,
                extras,
                target_platform,
                target_python_version
            )
            
            if not parsed_dep:
                continue

            dep_name, dep_constraint = parsed_dep
            if dep_name in visited or dep_name in exclude:
                continue

            compatible_version = get_compatible_version(dep_name, dep_constraint, verbose)
            if not compatible_version:
                if verbose:
                    print(f"No compatible version found for {dep_name} with constraint {dep_constraint}")
                continue

            get_all_dependencies(
                dep_name,
                compatible_version,
                extras,
                visited,
                exclude,
                target_platform,
                target_python_version,
                new_path,
                verbose
            )

    except Exception as e:
        if verbose:
            print(f"Unexpected error processing {normalized_name}: {str(e)}")

    if verbose:
        print(visited)
    return visited


def get_package_dependencies_from_pypi(package_name: str) -> List[str]:
    """
    Get direct dependencies for a package using PyPI's JSON API.
    
    Args:
        package_name (str): The name of the package to get dependencies for.
        
    Returns:
        List[str]: List of dependency strings.
    """
    pypi_url = f'https://pypi.python.org/pypi/{package_name}/json'
    
    try:
        with urllib.request.urlopen(pypi_url) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        reqs = data['info']['requires_dist']
        return reqs if reqs else []
    except Exception as e:
        print(f"Error fetching dependencies for {package_name}: {e}")
        return []


def resolve_dependencies_from_requirements(requirements_file: str, 
                                          exclude: Optional[Set[str]] = None,
                                          extras: Optional[List[str]] = None,
                                          verbose: bool = False) -> Dict[str, str]:
    """
    Resolve dependencies from a requirements file.
    
    Args:
        requirements_file (str): Path to the requirements file.
        exclude (Optional[Set[str]]): Set of package names to exclude from dependency resolution.
        extras (Optional[List[str]]): Optional list of extras to include.
        verbose (bool): Whether to print detailed output.
        
    Returns:
        Dict[str, str]: Dictionary mapping package names to versions for all dependencies.
    """
    if exclude is None:
        exclude = set()
        
    all_dependencies = {}
    
    try:
        with open(requirements_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                if '==' in line:
                    pkg_name, version = line.split('==', 1)
                    deps = get_all_dependencies(pkg_name, version, extras, exclude=exclude, verbose=verbose)
                else:
                    deps = get_all_dependencies(line, None, extras, exclude=exclude, verbose=verbose)
                    
                all_dependencies.update(deps)
    except FileNotFoundError as e:
        print(f"Error: Requirements file '{requirements_file}' not found. {e}")
        sys.exit(1)
        
    return all_dependencies


def print_dependency_tree(
    package_name: str,
    version: Optional[str] = None,
    indent: int = 0,
    visited: Optional[Set[str]] = None,
    verbose: bool = False
) -> None:
    """
    Print a hierarchical dependency tree for a package.
    
    Args:
        package_name (str): The name of the package.
        version (Optional[str]): Version of the package.
        indent (int): Indentation level for printing.
        visited (Optional[Set[str]]): Set to track visited packages and detect circular references.
    """
    if visited is None:
        visited = set()

    normalized_name = normalize_package_name(package_name)
    #print(f"Normalized name: {normalized_name}")

    if not version:
            version = get_compatible_version(normalized_name, None, verbose)
            if not version:
                return
            
    pkg_key = f"{normalized_name}=={version}" if version else normalized_name

    if pkg_key in visited:
        print(f"{'  ' * indent}└── {pkg_key} (circular reference)")
        return

    visited.add(pkg_key)

    try:
        pkg_info = get_package_info(normalized_name, version)
        version = version or pkg_info.get('info', {}).get('version', 'unknown')
        
        print(f"{'  ' * indent}└── {normalized_name}=={version}")
        
        requires_dist = pkg_info.get('info', {}).get('requires_dist', [])
        
        if requires_dist:
            for dep in requires_dist:
                parsed_dep = parse_dependency_string(dep)
                if parsed_dep:
                    dep_name, dep_version = parsed_dep
                    compat_version = get_compatible_version(dep_name, dep_version, verbose)
                    print_dependency_tree(dep_name, compat_version, indent + 1, visited)
    except Exception as e:
        print(f"{'  ' * indent}└── Error resolving {pkg_key}: {e}")


if __name__ == "__main__":
    # Simple CLI for testing
    if len(sys.argv) < 2:
        print("Usage: python dependency_resolver.py PACKAGE_NAME [VERSION]")
        sys.exit(1)
        
    package = sys.argv[1]
    version = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"Dependency tree for {package}{f' ({version})' if version else ''}:")
    print_dependency_tree(package, version)
