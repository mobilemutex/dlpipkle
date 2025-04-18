#!/usr/bin/env python3
"""
dlPipkle

A tool to download Python packages and their dependencies for offline installation.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from typing import List, Dict, Set, Optional, Tuple, Any

def get_package_info(package_name: str, package_version: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch package information from PyPI JSON API.
    """
    if package_version:
        url = f"https://pypi.org/pypi/{package_name}/{package_version}/json"
    else:
        url = f"https://pypi.org/pypi/{package_name}/json"
    
    try:
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"Error fetching package info for {package_name}: {e}")
        if package_version:
            print(f"Trying without version constraint...")
            return get_package_info(package_name)
        sys.exit(1)

def normalize_package_name(name: str) -> str:
    """
    Normalize package name according to PEP 503.
    """
    return re.sub(r"[-_.]+", "-", name).lower()

def parse_dependency_string(dep_string: str, extras: List[str] = None) -> Optional[Tuple[str, Optional[str]]]:
    """
    Parse a dependency string to extract package name and version constraint.
    """
    # Remove comments
    dep_string = re.sub(r'#.*$', '', dep_string).strip()
    if not dep_string:
        return None
    
    # Handle conditional dependencies
    if ";" in dep_string:
        dep_part, env_part = dep_string.split(";", 1)
        
        # This is a simplified approach to environment markers
        if any(marker in env_part for marker in ['sys_platform', 'platform_system']):
            return None
            
        dep_string = dep_part.strip()
    
    # Handle extras
    if "extra ==" in dep_string:
        if not extras:
            return None
        
        extra_match = re.search(r'extra\s*==\s*["\']([^"\']+)["\']', dep_string)
        if extra_match and extra_match.group(1) not in extras:
            return None
    
    # Extract package name and version
    match = re.match(r'([a-zA-Z0-9_\-\.]+)(?:[<>=~!].*)?', dep_string)
    if match:
        package_name = normalize_package_name(match.group(1))
        version_constraint = dep_string[len(match.group(1)):].strip()
        return package_name, version_constraint if version_constraint else None
    
    return None

def get_all_dependencies(
    package_name: str, 
    version: Optional[str] = None, 
    extras: List[str] = None,
    visited: Optional[Dict[str, str]] = None,
    exclude: Optional[Set[str]] = None
) -> Dict[str, str]:
    """
    Recursively get all dependencies of a package.
    """
    if visited is None:
        visited = {}
    
    if exclude is None:
        exclude = set()
    
    normalized_name = normalize_package_name(package_name)
    
    if normalized_name in exclude:
        return visited
        
    if normalized_name in visited:
        return visited
        
    print(f"Resolving dependencies for {normalized_name}{f' ({version})' if version else ''}...")
    
    try:
        pkg_info = get_package_info(normalized_name, version)
        
        # If version wasn't specified, get the latest version
        if not version:
            version = pkg_info.get('info', {}).get('version')
        
        visited[normalized_name] = version
        
        requires_dist = pkg_info.get('info', {}).get('requires_dist', [])
        
        if requires_dist:
            for dep in requires_dist:
                parsed_dep = parse_dependency_string(dep, extras)
                if parsed_dep:
                    dep_name, dep_version = parsed_dep
                    if dep_name not in visited and dep_name not in exclude:
                        get_all_dependencies(dep_name, None, extras, visited, exclude)
    except Exception as e:
        print(f"Warning: Error processing {normalized_name}: {e}")
                
    return visited

def download_package(
    package_name: str,
    version: str,
    output_dir: str,
    as_source: bool,
    platform: Optional[str] = None, 
    python_version: Optional[str] = None,
    implementation: Optional[str] = None,
    abi: Optional[str] = None
) -> bool:
    """
    Download a single package using pip.
    """
    package_spec = f"{package_name}=={version}"
    
    cmd = [sys.executable, "-m", "pip", "download", "--no-deps"]
    
    if output_dir:
        cmd.extend(["-d", output_dir])
        
    if as_source:
        cmd.extend(["--no-binary", ":all:"])
    
    # When using platform-specific options, --only-binary=:all: is required
    if platform or python_version or implementation or abi:
        if not as_source:
            cmd.extend(["--only-binary", ":all:"])
    
    if platform:
        cmd.extend(["--platform", platform])
        
    if python_version:
        cmd.extend(["--python-version", python_version])
        
    if implementation:
        cmd.extend(["--implementation", implementation])
        
    if abi:
        cmd.extend(["--abi", abi])
        
    cmd.append(package_spec)
    
    print(f"Downloading {package_spec}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error downloading {package_spec}: {result.stderr.strip()}")
        if platform or python_version or implementation or abi:
            print("  Trying without platform/version constraints...")
            return download_package(package_name, version, output_dir, as_source)
        return False
    else:
        if result.stdout:
            print(f"  {result.stdout.strip()}")
        print(f"  Successfully downloaded {package_spec}")
        return True

def main():
    parser = argparse.ArgumentParser(
        description="Download pip packages and their dependencies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Download a single package and its dependencies:
    dlpipkle numpy
    
  Download packages specified in requirements.txt:
    dlpipkle -r requirements.txt
    
  Download source packages:
    dlpipkle --source numpy
    
  Download packages for a specific platform and Python version:
    dlpipkle --platform manylinux2014_x86_64 --python-version 3.9 numpy
        """
    )
    parser.add_argument("packages", nargs="*", help="Package names to download")
    parser.add_argument("-d", "--directory", default=".", help="Directory to save downloaded packages (default: current directory)")
    parser.add_argument("--source", action="store_true", help="Download source packages instead of binaries")
    parser.add_argument("--platform", help="Target platform for binaries (e.g., manylinux2014_x86_64, win_amd64)")
    parser.add_argument("--python-version", help="Target Python version (e.g., 3.9)")
    parser.add_argument("--implementation", help="Target Python implementation (e.g., cp, pp)")
    parser.add_argument("--abi", help="Target Python ABI (e.g., cp39)")
    parser.add_argument("-r", "--requirements", help="Requirements file to read packages from")
    parser.add_argument("--exclude", nargs="*", default=[], help="Packages to exclude from dependency resolution")
    parser.add_argument("--extra", "-e", action="append", dest="extras", help="Extra features to include (can be used multiple times)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Check that at least one package or requirements file is specified
    if not args.packages and not args.requirements:
        parser.error("At least one package or a requirements file must be specified")
    
    packages = args.packages
    if args.requirements:
        try:
            with open(args.requirements, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        packages.append(line)
        except FileNotFoundError:
            print(f"Error: Requirements file '{args.requirements}' not found")
            sys.exit(1)
    
    # Create output directory if it doesn't exist
    if args.directory:
        os.makedirs(args.directory, exist_ok=True)
    
    # Parse package specifications
    package_specs = []
    for package in packages:
        if '==' in package:
            pkg_name, version = package.split('==', 1)
            package_specs.append((pkg_name, version))
        else:
            package_specs.append((package, None))
    
    # Get all dependencies for all packages
    all_dependencies = {}
    exclude_set = set(normalize_package_name(pkg) for pkg in args.exclude)
    
    for pkg_name, version in package_specs:
        deps = get_all_dependencies(pkg_name, version, args.extras, exclude=exclude_set)
        all_dependencies.update(deps)
    
    print(f"\nFound {len(all_dependencies)} packages to download:")
    for pkg_name, version in all_dependencies.items():
        print(f"  - {pkg_name}=={version}")
    
    # Download each package individually
    success = []
    failed = []
    
    for pkg_name, version in all_dependencies.items():
        result = download_package(
            pkg_name,
            version,
            args.directory,
            args.source,
            args.platform,
            args.python_version,
            args.implementation,
            args.abi
        )
        
        if result:
            success.append(f"{pkg_name}=={version}")
        else:
            failed.append(f"{pkg_name}=={version}")
    
    print("\nDownload summary:")
    print(f"  Successfully downloaded: {len(success)} packages")
    
    if failed:
        print(f"  Failed to download: {len(failed)} packages")
        for pkg in failed:
            print(f"    - {pkg}")
    
    print(f"All packages have been downloaded to: {os.path.abspath(args.directory)}")

if __name__ == "__main__":
    main()
