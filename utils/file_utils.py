"""
File utilities module for RocotoViewer.

This module provides common file operations and utilities used throughout the application,
with enhanced support for large file handling.
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Union, Generator, Tuple, Callable
import logging
import tempfile
import mmap
from collections import deque


class FileUtils:
    """
    Utility class for file operations with enhanced large file support.
    """
    
    logger = logging.getLogger(__name__)
    
    @staticmethod
    def find_files(directory: Path, extensions: Optional[Union[str, List[str]]] = None, 
                   recursive: bool = True) -> List[Path]:
        """
        Find files in a directory with specific extensions.
        
        Args:
            directory: Directory to search in
            extensions: File extensions to look for (with or without dot)
            recursive: Whether to search recursively
            
        Returns:
            List of file paths found
        """
        if not directory.exists():
            FileUtils.logger.warning(f"Directory does not exist: {directory}")
            return []
        
        if isinstance(extensions, str):
            extensions = [extensions]
        
        # Normalize extensions to include the dot
        if extensions:
            normalized_extensions = []
            for ext in extensions:
                if not ext.startswith('.'):
                    normalized_extensions.append('.' + ext)
                else:
                    normalized_extensions.append(ext)
            extensions = normalized_extensions
        
        files = []
        if recursive:
            for root, dirs, filenames in os.walk(directory):
                for filename in filenames:
                    file_path = Path(root) / filename
                    if FileUtils._matches_extension(file_path, extensions):
                        files.append(file_path)
        else:
            for item in directory.iterdir():
                if item.is_file() and FileUtils._matches_extension(item, extensions):
                    files.append(item)
        
        return sorted(files)
    
    @staticmethod
    def _matches_extension(file_path: Path, extensions: Optional[List[str]]) -> bool:
        """
        Check if a file path matches any of the given extensions.
        
        Args:
            file_path: File path to check
            extensions: List of extensions to match against
            
        Returns:
            True if file matches any extension, False otherwise
        """
        if extensions is None:
            return True  # If no extensions specified, match all files
        
        return file_path.suffix.lower() in [ext.lower() for ext in extensions]
    
    @staticmethod
    def get_file_size(file_path: Path) -> int:
        """
        Get the size of a file in bytes.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File size in bytes
        """
        if not file_path.exists():
            FileUtils.logger.warning(f"File does not exist: {file_path}")
            return 0
        
        return file_path.stat().st_size
    
    @staticmethod
    def get_file_age(file_path: Path) -> float:
        """
        Get the age of a file in seconds.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File age in seconds
        """
        import time
        
        if not file_path.exists():
            FileUtils.logger.warning(f"File does not exist: {file_path}")
            return float('inf')
        
        return time.time() - file_path.stat().st_mtime
    
    @staticmethod
    def ensure_directory_exists(directory: Path) -> bool:
        """
        Ensure that a directory exists, creating it if necessary.
        
        Args:
            directory: Directory path to ensure
            
        Returns:
            True if directory exists or was created successfully
        """
        try:
            directory.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            FileUtils.logger.error(f"Failed to create directory {directory}: {str(e)}")
            return False
    
    @staticmethod
    def copy_file(source: Path, destination: Path, overwrite: bool = False) -> bool:
        """
        Copy a file from source to destination.
        
        Args:
            source: Source file path
            destination: Destination file path
            overwrite: Whether to overwrite if destination exists
            
        Returns:
            True if copy was successful
        """
        if not source.exists():
            FileUtils.logger.error(f"Source file does not exist: {source}")
            return False
        
        if destination.exists() and not overwrite:
            FileUtils.logger.warning(f"Destination file exists and overwrite is False: {destination}")
            return False
        
        try:
            # Ensure destination directory exists
            FileUtils.ensure_directory_exists(destination.parent)
            
            shutil.copy2(source, destination)
            return True
        except Exception as e:
            FileUtils.logger.error(f"Failed to copy file {source} to {destination}: {str(e)}")
            return False
    
    @staticmethod
    def move_file(source: Path, destination: Path, overwrite: bool = False) -> bool:
        """
        Move a file from source to destination.
        
        Args:
            source: Source file path
            destination: Destination file path
            overwrite: Whether to overwrite if destination exists
            
        Returns:
            True if move was successful
        """
        if not source.exists():
            FileUtils.logger.error(f"Source file does not exist: {source}")
            return False
        
        if destination.exists() and not overwrite:
            FileUtils.logger.warning(f"Destination file exists and overwrite is False: {destination}")
            return False
        
        try:
            # Ensure destination directory exists
            FileUtils.ensure_directory_exists(destination.parent)
            
            shutil.move(str(source), str(destination))
            return True
        except Exception as e:
            FileUtils.logger.error(f"Failed to move file {source} to {destination}: {str(e)}")
            return False
    
    @staticmethod
    def create_temp_file(suffix: str = "", prefix: str = "rocotoviewer_") -> Path:
        """
        Create a temporary file.
        
        Args:
            suffix: File suffix/extension
            prefix: File name prefix
            
        Returns:
            Path to the temporary file
        """
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix=prefix)
        temp_file.close()
        return Path(temp_file.name)
    
    @staticmethod
    def create_temp_directory(prefix: str = "rocotoviewer_") -> Path:
        """
        Create a temporary directory.
        
        Args:
            prefix: Directory name prefix
            
        Returns:
            Path to the temporary directory
        """
        return Path(tempfile.mkdtemp(prefix=prefix))
    
    @staticmethod
    def safe_read_file(file_path: Path, encoding: str = 'utf-8', 
                       max_size: int = 10 * 1024 * 1024) -> Optional[str]:  # 10MB default
        """
        Safely read a file with size limits and error handling.
        
        Args:
            file_path: Path to the file to read
            encoding: File encoding
            max_size: Maximum file size to read (in bytes)
            
        Returns:
            File content as string or None if error occurred
        """
        if not file_path.exists():
            FileUtils.logger.error(f"File does not exist: {file_path}")
            return None
        
        size = FileUtils.get_file_size(file_path)
        if size > max_size:
            FileUtils.logger.error(f"File too large to read safely: {file_path} ({size} bytes, max: {max_size})")
            return None
        
        try:
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                return f.read()
        except Exception as e:
            FileUtils.logger.error(f"Error reading file {file_path}: {str(e)}")
            return None
    
    @staticmethod
    def safe_write_file(file_path: Path, content: str, encoding: str = 'utf-8') -> bool:
        """
        Safely write content to a file.
        
        Args:
            file_path: Path to the file to write
            content: Content to write
            encoding: File encoding
            
        Returns:
            True if write was successful
        """
        try:
            # Ensure directory exists
            FileUtils.ensure_directory_exists(file_path.parent)
            
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)
            return True
        except Exception as e:
            FileUtils.logger.error(f"Error writing to file {file_path}: {str(e)}")
            return False
    
    @staticmethod
    def get_file_hash(file_path: Path, algorithm: str = 'sha256') -> Optional[str]:
        """
        Calculate the hash of a file.
        
        Args:
            file_path: Path to the file
            algorithm: Hash algorithm to use
            
        Returns:
            File hash as hex string or None if error occurred
        """
        import hashlib
        
        if not file_path.exists():
            FileUtils.logger.error(f"File does not exist: {file_path}")
            return None
        
        try:
            hash_obj = hashlib.new(algorithm)
            with open(file_path, 'rb') as f:
                # Read file in chunks to handle large files efficiently
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except Exception as e:
            FileUtils.logger.error(f"Error calculating hash for file {file_path}: {str(e)}")
            return None
    
    @staticmethod
    def read_large_file_tail(file_path: Path, num_lines: int = 100, 
                            encoding: str = 'utf-8') -> List[str]:
        """
        Efficiently read the last N lines of a large file without loading the entire file.
        
        Args:
            file_path: Path to the file
            num_lines: Number of lines to read from the end
            encoding: File encoding
            
        Returns:
            List of the last N lines
        """
        if not file_path.exists():
            FileUtils.logger.error(f"File does not exist: {file_path}")
            return []
        
        try:
            # Use memory mapping for efficient access to large files
            with open(file_path, 'rb') as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
                    # Start from the end of the file
                    size = len(mmapped_file)
                    if size == 0:
                        return []
                    
                    # Find the last N line breaks
                    lines_found = 0
                    pos = size - 1
                    
                    # Move backwards to find line breaks
                    while pos >= 0 and lines_found < num_lines:
                        if mmapped_file[pos:pos+1] == b'\n':
                            lines_found += 1
                        pos -= 1
                    
                    # If we haven't found enough lines, start from the beginning
                    if lines_found < num_lines:
                        pos = 0
                    else:
                        # Move to the start of the current line (after the newline)
                        pos += 1
                    
                    # Read the content from pos to end
                    content = mmapped_file[pos:size].decode(encoding, errors='replace')
                    
                    # Split into lines and return the requested number
                    lines = content.splitlines()
                    
                    # Return the last num_lines lines
                    return lines[-num_lines:] if len(lines) > num_lines else lines
        except Exception as e:
            FileUtils.logger.error(f"Error reading tail of large file {file_path}: {str(e)}")
            # Fallback to regular file reading
            try:
                with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                    all_lines = f.readlines()
                    result = [line.rstrip('\n\r') for line in all_lines[-num_lines:]]
                    return result
            except Exception as fallback_error:
                FileUtils.logger.error(f"Fallback read also failed for {file_path}: {str(fallback_error)}")
                return []
    
    @staticmethod
    def read_file_with_progress(file_path: Path, chunk_size: int = 8192, 
                               progress_callback: Optional[Callable[[int, int], None]] = None,
                               encoding: str = 'utf-8') -> str:
        """
        Read a file with progress reporting for large files.
        
        Args:
            file_path: Path to the file
            chunk_size: Size of chunks to read at a time
            progress_callback: Callback function to report progress (current, total bytes)
            encoding: File encoding
            
        Returns:
            File content as string
        """
        if not file_path.exists():
            FileUtils.logger.error(f"File does not exist: {file_path}")
            return ""
        
        total_size = FileUtils.get_file_size(file_path)
        content_parts = []
        bytes_read = 0
        
        try:
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    content_parts.append(chunk)
                    bytes_read += len(chunk.encode(encoding))
                    
                    if progress_callback:
                        progress_callback(bytes_read, total_size)
            
            return "".join(content_parts)
        except Exception as e:
            FileUtils.logger.error(f"Error reading file with progress {file_path}: {str(e)}")
            return ""
    
    @staticmethod
    def tail_file_generator(file_path: Path, max_lines: int = 1000, 
                           encoding: str = 'utf-8') -> Generator[str, None, None]:
        """
        Generator that yields the last N lines of a file.
        
        Args:
            file_path: Path to the file
            max_lines: Maximum number of lines to yield
            encoding: File encoding
            
        Yields:
            Lines from the end of the file
        """
        lines = FileUtils.read_large_file_tail(file_path, max_lines, encoding)
        for line in lines:
            yield line
    
    @staticmethod
    def get_file_inode(file_path: Path) -> Optional[int]:
        """
        Get the inode of a file, useful for detecting file rotation.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Inode number or None if error occurred
        """
        if not file_path.exists():
            return None
        
        try:
            stat_info = file_path.stat()
            return stat_info.st_ino
        except Exception as e:
            FileUtils.logger.error(f"Error getting inode for file {file_path}: {str(e)}")
            return None
    
    @staticmethod
    def is_file_unchanged(file_path: Path, reference_inode: Optional[int], 
                         reference_size: Optional[int]) -> bool:
        """
        Check if a file has changed since a reference point.
        
        Args:
            file_path: Path to the file
            reference_inode: Reference inode number
            reference_size: Reference file size
            
        Returns:
            True if file is unchanged, False otherwise
        """
        if not file_path.exists():
            return False
        
        try:
            stat_info = file_path.stat()
            current_inode = stat_info.st_ino
            current_size = stat_info.st_size
            
            # If inode changed, file was rotated
            if reference_inode is not None and current_inode != reference_inode:
                return False
            
            # If size changed, file was modified
            if reference_size is not None and current_size != reference_size:
                return False
            
            return True
        except Exception as e:
            FileUtils.logger.error(f"Error checking if file unchanged {file_path}: {str(e)}")
            return False
    
    @staticmethod
    def get_file_growth_info(file_path: Path, reference_size: int) -> Tuple[int, int]:
        """
        Get information about how a file has grown since a reference point.
        
        Args:
            file_path: Path to the file
            reference_size: Reference file size
            
        Returns:
            Tuple of (current_size, growth_bytes)
        """
        current_size = FileUtils.get_file_size(file_path)
        growth = current_size - reference_size
        return current_size, growth