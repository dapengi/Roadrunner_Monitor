"""
SFTP client for uploading transcript files to remote server.
Uses paramiko for secure file transfer.
"""

import os
import logging
from pathlib import Path
from typing import Optional, List
import paramiko
from stat import S_ISDIR

logger = logging.getLogger(__name__)


class SFTPClient:
    """Client for uploading files to SFTP server."""

    def __init__(self, host: str, port: int, username: str, password: str, upload_path: str):
        """
        Initialize SFTP client.

        Args:
            host: SFTP server hostname or IP
            port: SFTP port (usually 22)
            username: SFTP username
            password: SFTP password
            upload_path: Remote directory path for uploads
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.upload_path = upload_path.rstrip('/')

        self.ssh_client = None
        self.sftp_client = None

        logger.info(f"Initialized SFTP client for {self.host}:{self.port}")

    def is_connected(self) -> bool:
        """
        Check if the SFTP connection is still alive.

        Returns:
            True if connected and responsive, False otherwise
        """
        if not self.sftp_client or not self.ssh_client:
            return False

        try:
            # Test the connection by getting the current working directory
            self.sftp_client.getcwd()
            return True
        except Exception as e:
            logger.debug(f"Connection check failed: {e}")
            return False

    def ensure_connection(self) -> bool:
        """
        Ensure we have a valid connection, reconnecting if necessary.

        Returns:
            True if connected (or reconnected), False if connection failed
        """
        if self.is_connected():
            return True

        # Connection is dead or doesn't exist, clean up and reconnect
        logger.info("Connection stale or closed, reconnecting...")
        self.disconnect()
        return self.connect()

    def connect(self):
        """Establish SFTP connection with keepalive settings."""
        try:
            logger.info(f"Connecting to SFTP server {self.host}:{self.port}...")

            # Create SSH client
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Connect
            self.ssh_client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=30,
                look_for_keys=False,
                allow_agent=False
            )

            # Enable SSH keepalive to prevent connection timeout during long operations
            # Send keepalive every 60 seconds
            transport = self.ssh_client.get_transport()
            if transport:
                transport.set_keepalive(60)

            # Open SFTP session
            self.sftp_client = self.ssh_client.open_sftp()

            logger.info(f"✅ Connected to SFTP server {self.host}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to SFTP server: {e}")
            self.disconnect()
            return False

    def disconnect(self):
        """Close SFTP connection."""
        try:
            if self.sftp_client:
                self.sftp_client.close()
                self.sftp_client = None
            
            if self.ssh_client:
                self.ssh_client.close()
                self.ssh_client = None
            
            logger.info("Disconnected from SFTP server")
            
        except Exception as e:
            logger.warning(f"Error during disconnect: {e}")

    def mkdir_p(self, remote_path: str):
        """
        Create remote directory recursively (like mkdir -p).
        
        Args:
            remote_path: Remote directory path to create
        """
        if not self.sftp_client:
            raise Exception("Not connected to SFTP server")
        
        dirs = []
        path = remote_path
        
        # Build list of directories to create
        while path and path != '/':
            dirs.append(path)
            path = os.path.dirname(path)
        
        # Create directories from root to leaf
        for directory in reversed(dirs):
            try:
                self.sftp_client.stat(directory)
            except FileNotFoundError:
                try:
                    self.sftp_client.mkdir(directory)
                    logger.debug(f"Created directory: {directory}")
                except Exception as e:
                    logger.warning(f"Could not create directory {directory}: {e}")

    def upload_file(self, local_path: str, remote_filename: Optional[str] = None) -> bool:
        """
        Upload a file to SFTP server.
        
        Args:
            local_path: Path to local file to upload
            remote_filename: Optional custom remote filename (defaults to local filename)
            
        Returns:
            True if upload successful, False otherwise
        """
        if not os.path.exists(local_path):
            logger.error(f"Local file not found: {local_path}")
            return False

        # Ensure we have a valid connection (reconnect if stale)
        if not self.ensure_connection():
            return False

        try:
            # Determine remote filename
            if remote_filename is None:
                remote_filename = os.path.basename(local_path)
            
            # Full remote path
            remote_path = f"{self.upload_path}/{remote_filename}"
            
            # Ensure remote directory exists
            remote_dir = os.path.dirname(remote_path)
            self.mkdir_p(remote_dir)
            
            # Get file size for logging
            file_size = os.path.getsize(local_path)
            file_size_mb = file_size / (1024 * 1024)
            
            logger.info(f"Uploading {local_path} ({file_size_mb:.2f} MB) to {remote_path}...")
            
            # Upload file
            self.sftp_client.put(local_path, remote_path)
            
            # Verify upload
            remote_stat = self.sftp_client.stat(remote_path)
            if remote_stat.st_size == file_size:
                logger.info(f"✅ Successfully uploaded to {remote_path}")
                return True
            else:
                logger.error(f"Upload size mismatch: local={file_size}, remote={remote_stat.st_size}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to upload {local_path}: {e}")
            return False

    def upload_files(self, file_paths: List[str], subfolder: Optional[str] = None) -> dict:
        """
        Upload multiple files to SFTP server.
        
        Args:
            file_paths: List of local file paths to upload
            subfolder: Optional subfolder within upload_path
            
        Returns:
            Dictionary with upload results: {filename: success_bool}
        """
        results = {}

        # Ensure we have a valid connection before starting uploads
        if not self.ensure_connection():
            return {os.path.basename(f): False for f in file_paths}

        for local_path in file_paths:
            filename = os.path.basename(local_path)
            
            if subfolder:
                remote_filename = f"{subfolder}/{filename}"
            else:
                remote_filename = filename
            
            success = self.upload_file(local_path, remote_filename)
            results[filename] = success
        
        return results

    def list_directory(self, remote_path: Optional[str] = None) -> List[str]:
        """
        List files in remote directory.
        
        Args:
            remote_path: Remote directory path (defaults to upload_path)
            
        Returns:
            List of filenames
        """
        if not self.ensure_connection():
            return []

        path = remote_path or self.upload_path

        try:
            files = self.sftp_client.listdir(path)
            logger.info(f"Listed {len(files)} files in {path}")
            return files
        except Exception as e:
            logger.error(f"Failed to list directory {path}: {e}")
            return []

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
