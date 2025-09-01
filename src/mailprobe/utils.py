"""
Utility functions for cross-platform compatibility.

This module provides utility functions to handle platform-specific
differences, particularly for Windows compatibility.
"""

import os
import sys
from pathlib import Path
from typing import Union


def normalize_path(path: Union[str, Path]) -> Path:
    """
    Normalize a path for cross-platform compatibility.
    
    Args:
        path: Path to normalize
        
    Returns:
        Normalized Path object
    """
    path = Path(path).expanduser().resolve()
    
    # Handle Windows path length limitations
    if os.name == 'nt' and len(str(path)) > 260:
        try:
            # Try to get short path name on Windows
            import ctypes
            from ctypes import wintypes
            
            GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
            GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
            GetShortPathNameW.restype = wintypes.DWORD
            
            buffer = ctypes.create_unicode_buffer(260)
            if GetShortPathNameW(str(path), buffer, 260):
                path = Path(buffer.value)
        except (ImportError, AttributeError, OSError):
            # Fallback: use a shorter path
            import tempfile
            import hashlib
            
            # Create a hash-based short path
            path_hash = hashlib.md5(str(path).encode()).hexdigest()[:8]
            temp_dir = Path(tempfile.gettempdir()) / f"mailprobe-{path_hash}"
            path = temp_dir
    
    return path


def safe_open_text(filepath: Union[str, Path], mode: str = 'r', **kwargs):
    """
    Safely open a text file with proper encoding and line ending handling.
    
    Args:
        filepath: Path to file
        mode: File mode
        **kwargs: Additional arguments for open()
        
    Returns:
        File handle
    """
    # Set default encoding and line ending handling
    if 'encoding' not in kwargs:
        kwargs['encoding'] = 'utf-8'
    if 'errors' not in kwargs:
        kwargs['errors'] = 'ignore'
    if 'newline' not in kwargs and 'r' in mode:
        kwargs['newline'] = None  # Universal newlines
    elif 'newline' not in kwargs and 'w' in mode:
        kwargs['newline'] = '\n'  # Use Unix line endings
    
    return open(filepath, mode, **kwargs)


def get_default_database_path() -> Path:
    """
    Get the default database path for the current platform.
    
    Returns:
        Default database path
    """
    if os.name == 'nt':
        # Windows: Use AppData
        appdata = os.environ.get('APPDATA')
        if appdata:
            return normalize_path(Path(appdata) / 'MailProbe-Py')
        else:
            return normalize_path(Path.home() / 'AppData' / 'Roaming' / 'MailProbe-Py')
    else:
        # Unix-like: Use home directory
        return normalize_path(Path.home() / '.mailprobe-py')


def is_windows() -> bool:
    """Check if running on Windows."""
    return os.name == 'nt'


def is_long_path_supported() -> bool:
    """
    Check if long paths are supported on Windows.
    
    Returns:
        True if long paths are supported or not on Windows
    """
    if not is_windows():
        return True
    
    try:
        # Check Windows version and long path support
        import winreg
        
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\FileSystem"
        )
        value, _ = winreg.QueryValueEx(key, "LongPathsEnabled")
        winreg.CloseKey(key)
        
        return bool(value)
    except (ImportError, FileNotFoundError, OSError):
        return False


def ensure_directory_exists(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path
        
    Returns:
        Normalized directory path
    """
    path = normalize_path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_temp_directory() -> Path:
    """
    Get a temporary directory for the application.
    
    Returns:
        Temporary directory path
    """
    import tempfile
    
    temp_dir = Path(tempfile.gettempdir()) / 'mailprobe-py'
    return ensure_directory_exists(temp_dir)
