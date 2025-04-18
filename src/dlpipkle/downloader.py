#!/usr/bin/env python3
"""
Downloader module for dlpipkle.

This module provides functionality to download Python packages and their
dependencies using pip's download command with various options for
platform-specific binaries or source distributions.
"""

import os
import subprocess
import sys
from typing import Dict, List, Optional, Tuple, Union, Any


def download_package(
    package_name: str,
    version: str,
    output_dir: str,
    as_source: bool = False,
    platform: Optional[str] = None,
    python_version: Optional[str] = None,
    implementation: Optional[str] = None,
    abi: Optional[str] = None,
    verbose: bool = False
) -> bool:
    """
    Download a single package using pip.
    
    Args:
        package_name: The name of the package to download
        version: The version of the package to download
        output_dir: Directory to save the downloaded package
        as_source: Whether to download source distribution instead of wheel
        platform: Target platform for binaries (e.g., manylinux2014_x86_64)
        python_version: Target Python version (e.g., 3.9)
        implementation: Target Python implementation (e.g., cp, pp)
        abi: Target Python ABI (e.g., cp39)
        verbose: Whether to print verbose output
        
    Returns:
        True if download was successful, False otherwise
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
    
    if verbose:
        print(f"Downloading {package_spec}...")
        print(f"Command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        if verbose:
            print(f"Error downloading {package_spec}: {result.stderr.strip()}")
        
        # If platform-specific download fails, try without platform constraints
        if platform or python_version or implementation or abi:
            if verbose:
                print("  Trying without platform/version constraints...")
            return download_package(
                package_name, 
                version, 
                output_dir, 
                as_source,
                verbose=verbose
            )
        return False
    else:
        if verbose and result.stdout:
            print(f"  {result.stdout.strip()}")
        
        if verbose:
            print(f"  Successfully downloaded {package_spec}")
        return True


def batch_download_packages(
    packages: Dict[str, str],
    output_dir: str,
    as_source: bool = False,
    platform: Optional[str] = None,
    python_version: Optional[str] = None,
    implementation: Optional[str] = None,
    abi: Optional[str] = None,
    verbose: bool = False
) -> Tuple[List[str], List[str]]:
    """
    Download multiple packages.
    
    Args:
        packages: Dictionary mapping package names to versions
        output_dir: Directory to save the downloaded packages
        as_source: Whether to download source distributions instead of wheels
        platform: Target platform for binaries
        python_version: Target Python version
        implementation: Target Python implementation
        abi: Target Python ABI
        verbose: Whether to print verbose output
        
    Returns:
        Tuple of (successful_downloads, failed_downloads)
    """
    success = []
    failed = []
    
    for pkg_name, version in packages.items():
        result = download_package(
            pkg_name,
            version,
            output_dir,
            as_source,
            platform,
            python_version,
            implementation,
            abi,
            verbose
        )
        
        if result:
            success.append(f"{pkg_name}=={version}")
        else:
            failed.append(f"{pkg_name}=={version}")
    
    return success, failed


def download_from_requirements(
    requirements_file: str,
    output_dir: str,
    as_source: bool = False,
    platform: Optional[str] = None,
    python_version: Optional[str] = None,
    implementation: Optional[str] = None,
    abi: Optional[str] = None,
    verbose: bool = False
) -> Tuple[List[str], List[str]]:
    """
    Download all packages specified in a requirements file.
    
    This function doesn't resolve dependencies, it just downloads the packages
    specified in the requirements file. Use dependency_resolver to get the
    complete dependency tree first.
    
    Args:
        requirements_file: Path to the requirements file
        output_dir: Directory to save the downloaded packages
        as_source: Whether to download source distributions instead of wheels
        platform: Target platform for binaries
        python_version: Target Python version
        implementation: Target Python implementation
        abi: Target Python ABI
        verbose: Whether to print verbose output
        
    Returns:
        Tuple of (successful_downloads, failed_downloads)
    """
    success = []
    failed = []
    
    try:
        with open(requirements_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                if '==' in line:
                    pkg_name, version = line.split('==', 1)
                    result = download_package(
                        pkg_name,
                        version,
                        output_dir,
                        as_source,
                        platform,
                        python_version,
                        implementation,
                        abi,
                        verbose
                    )
                    
                    if result:
                        success.append(line)
                    else:
                        failed.append(line)
                else:
                    # For packages without version constraints, we need to resolve the latest version
                    # This is a simplified approach - in practice, you'd use dependency_resolver
                    if verbose:
                        print(f"Warning: No version specified for {line}. Attempting to download latest version.")
                    
                    cmd = [sys.executable, "-m", "pip", "download", "--no-deps", "--disable-pip-version-check"]
                    
                    if output_dir:
                        cmd.extend(["-d", output_dir])
                        
                    if as_source:
                        cmd.extend(["--no-binary", ":all:"])
                        
                    cmd.append(line)
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        success.append(line)
                    else:
                        failed.append(line)
    except FileNotFoundError:
        print(f"Error: Requirements file '{requirements_file}' not found")
        
    return success, failed


def verify_download(package_path: str, hash_type: str = 'sha256', expected_hash: Optional[str] = None) -> bool:
    """
    Verify the integrity of a downloaded package.
    
    Args:
        package_path: Path to the downloaded package
        hash_type: Type of hash to verify (md5, sha1, sha256, etc.)
        expected_hash: Expected hash value
        
    Returns:
        True if verification succeeds, False otherwise
    """
    import hashlib
    
    if not os.path.exists(package_path):
        return False
        
    if expected_hash is None:
        # If no hash is provided, just check that the file exists and is not empty
        return os.path.getsize(package_path) > 0
        
    hash_func = getattr(hashlib, hash_type, None)
    if hash_func is None:
        raise ValueError(f"Unsupported hash type: {hash_type}")
        
    file_hash = hash_func()
    with open(package_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            file_hash.update(chunk)
            
    return file_hash.hexdigest() == expected_hash


def get_download_size(package_name: str, version: Optional[str] = None) -> Optional[int]:
    """
    Get the download size of a package.
    
    Args:
        package_name: Name of the package
        version: Optional version of the package
        
    Returns:
        Size in bytes or None if size couldn't be determined
    """
    import json
    import urllib.request
    
    try:
        if version:
            url = f"https://pypi.org/pypi/{package_name}/{version}/json"
        else:
            url = f"https://pypi.org/pypi/{package_name}/json"
            
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        # Get the size of the wheel package if available, otherwise source
        releases = data.get('releases', {})
        
        if version:
            release_files = releases.get(version, [])
        else:
            # Get the latest version
            latest_version = data.get('info', {}).get('version')
            release_files = releases.get(latest_version, [])
            
        # Prefer wheels over source distributions
        wheels = [f for f in release_files if f.get('packagetype') == 'bdist_wheel']
        if wheels:
            return wheels[0].get('size')
            
        # Fall back to source distributions
        sdists = [f for f in release_files if f.get('packagetype') == 'sdist']
        if sdists:
            return sdists[0].get('size')
            
        return None
    except Exception:
        return None


def download_with_progress(
    package_name: str,
    version: str,
    output_dir: str,
    as_source: bool = False,
    platform: Optional[str] = None,
    python_version: Optional[str] = None,
    implementation: Optional[str] = None,
    abi: Optional[str] = None
) -> bool:
    """
    Download a package with progress reporting.
    
    This is a more advanced version of download_package that shows a progress bar.
    Note: This requires the tqdm package to be installed.
    
    Args:
        package_name: The name of the package to download
        version: The version of the package to download
        output_dir: Directory to save the downloaded package
        as_source: Whether to download source distribution instead of wheel
        platform: Target platform for binaries
        python_version: Target Python version
        implementation: Target Python implementation
        abi: Target Python ABI
        
    Returns:
        True if download was successful, False otherwise
    """
    try:
        from tqdm import tqdm
    except ImportError:
        print("Warning: tqdm package not installed. Progress bar will not be shown.")
        return download_package(
            package_name, version, output_dir, as_source, 
            platform, python_version, implementation, abi
        )
    
    package_spec = f"{package_name}=={version}"
    
    # Get the expected size
    size = get_download_size(package_name, version)
    
    cmd = [sys.executable, "-m", "pip", "download", "--no-deps", "--progress-bar", "off"]
    
    if output_dir:
        cmd.extend(["-d", output_dir])
        
    if as_source:
        cmd.extend(["--no-binary", ":all:"])
    
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
    
    with tqdm(total=size, unit='B', unit_scale=True, desc=package_name) as pbar:
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            bufsize=1,
            universal_newlines=True
        )
        
        # This is a simplified progress tracking that doesn't actually track real progress
        # For actual progress tracking, we'd need to parse pip's output or use a different approach
        while process.poll() is None:
            if size:
                # Update progress bar based on time rather than actual progress
                # This is just an approximation
                pbar.update(size // 100)
            
            import time
            time.sleep(0.1)
            
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            print(f"Error downloading {package_spec}: {stderr.strip()}")
            
            if platform or python_version or implementation or abi:
                print("  Trying without platform/version constraints...")
                return download_package(
                    package_name, 
                    version, 
                    output_dir, 
                    as_source
                )
            return False
        
        pbar.update(size if size else 0)  # Ensure the progress bar completes
        
    print(f"Successfully downloaded {package_spec}")
    return True


if __name__ == "__main__":
    # Simple CLI for testing
    if len(sys.argv) < 3:
        print("Usage: python downloader.py PACKAGE_NAME VERSION [OUTPUT_DIR]")
        sys.exit(1)
        
    pkg_name = sys.argv[1]
    version = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "."
    
    success = download_package(pkg_name, version, output_dir, verbose=True)
    
    if success:
        print(f"Successfully downloaded {pkg_name}=={version}")
    else:
        print(f"Failed to download {pkg_name}=={version}")
        sys.exit(1)
