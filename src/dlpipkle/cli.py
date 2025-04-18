#!/usr/bin/env python3
"""Command-line interface for dlpipkle."""

import argparse
import os
import sys
from typing import List, Optional, Set

from .dependency_resolver import get_all_dependencies, print_dependency_tree
from .downloader import download_package
from .platform_utils import list_platforms


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
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
    
  List available platforms for a package:
    dlpipkle --list-platforms numpy
        """
    )
    parser.add_argument("packages", nargs="*", help="Package names to download")
    parser.add_argument("-d", "--directory", default=".", 
                        help="Directory to save downloaded packages (default: current directory)")
    parser.add_argument("--source", action="store_true", 
                        help="Download source packages instead of binaries")
    parser.add_argument("--platform", 
                        help="Target platform for binaries (e.g., manylinux2014_x86_64, win_amd64)")
    parser.add_argument("--python-version", 
                        help="Target Python version (e.g., 3.9)")
    parser.add_argument("--implementation", 
                        help="Target Python implementation (e.g., cp, pp)")
    parser.add_argument("--abi", 
                        help="Target Python ABI (e.g., cp39)")
    parser.add_argument("-r", "--requirements", 
                        help="Requirements file to read packages from")
    parser.add_argument("--exclude", nargs="*", default=[], 
                        help="Packages to exclude from dependency resolution")
    parser.add_argument("--extra", "-e", action="append", dest="extras", 
                        help="Extra features to include (can be used multiple times)")
    parser.add_argument("--list-platforms", action="store_true", 
                        help="Lists available platforms for specified package and then exits")
    parser.add_argument("--print-dep-tree", action="store_true",
                        help="Prints a hierarchical dependency tree for a package and then exits")
    parser.add_argument("--verbose", "-v", action="store_true", 
                        help="Enable verbose output")
    
    return parser


def parse_requirements(requirements_file: str) -> List[str]:
    """Parse a requirements file and return a list of package specifications."""
    packages = []
    try:
        with open(requirements_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    packages.append(line)
    except FileNotFoundError:
        print(f"Error: Requirements file '{requirements_file}' not found")
        sys.exit(1)
    return packages


def handle_list_platforms(packages: List[str], python_version: Optional[str] = None) -> None:
    """Handle the --list-platforms option."""
    if not packages:
        print("Error: Must specify at least one package with --list-platforms")
        sys.exit(1)
        
    for package in packages:
        pkg_name = package.split('==')[0] if '==' in package else package
        version = package.split('==')[1] if '==' in package else None
        
        print(f"\nAvailable platforms for {package}:")
        try:
            platforms = list_platforms(pkg_name, version)
            if platforms:
                print("\n".join(f"  - {plat}" for plat in sorted(platforms)))
            else:
                print("  No platform-specific packages available")
        except Exception as e:
            print(f"  Error: {str(e)}")


def main() -> None:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Check that at least one package or requirements file is specified
    if not args.packages and not args.requirements and not args.list_platforms:
        parser.error("At least one package or a requirements file must be specified")
    
    # Handle platform listing
    if args.list_platforms:
        handle_list_platforms(args.packages, args.python_version)
        sys.exit(0)

    if args.print_dep_tree:
        print_dependency_tree(args.packages[0], verbose=args.verbose)
        sys.exit(0)
    
    # Collect packages from arguments and requirements file
    packages = list(args.packages)
    if args.requirements:
        packages.extend(parse_requirements(args.requirements))
    
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
    
    #print(f"Package specs: {package_specs}")

    # Get all dependencies for all packages
    all_dependencies = {}
    exclude_set: Set[str] = set(args.exclude)
    
    for pkg_name, version in package_specs:
        if args.verbose:
            print(f"Resolving dependencies for {pkg_name}{f' ({version})' if version else ''}...")
        deps = get_all_dependencies(pkg_name, version, args.extras, exclude=exclude_set, verbose=args.verbose)
        all_dependencies.update(deps)
    
    if args.verbose or len(all_dependencies) > 1:
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
            args.abi,
            verbose=args.verbose
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
