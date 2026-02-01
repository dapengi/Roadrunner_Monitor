"""Seafile client for reading and writing files directly to Seafile."""
import requests
import json
import logging
from typing import Optional, Dict, List
from pathlib import Path

logger = logging.getLogger(__name__)


class SeafileClient:
    """Client for interacting with Seafile API."""

    def __init__(self, url: str = None, token: str = None, library_id: str = None):
        """
        Initialize Seafile client.

        Args:
            url: Seafile server URL (defaults to config.SEAFILE_URL)
            token: API token (defaults to config.SEAFILE_API_TOKEN)
            library_id: Library ID (defaults to config.SEAFILE_LIBRARY_ID)
        """
        # Import here to avoid circular dependency
        from config import SEAFILE_URL, SEAFILE_API_TOKEN, SEAFILE_LIBRARY_ID

        self.base_url = (url or SEAFILE_URL).rstrip('/')
        self.token = token or SEAFILE_API_TOKEN
        self.library_id = library_id or SEAFILE_LIBRARY_ID
        self.headers = {
            'Authorization': f'Token {self.token}',
            'Accept': 'application/json'
        }

        logger.info(f"Initialized Seafile client for {self.base_url}")

    def file_exists(self, path: str) -> bool:
        """Check if a file exists in Seafile."""
        try:
            # Get file detail
            url = f"{self.base_url}/api2/repos/{self.library_id}/file/detail/"
            response = requests.get(
                url,
                headers=self.headers,
                params={'p': path},
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"File exists check failed for {path}: {e}")
            return False

    def read_file(self, path: str) -> Optional[str]:
        """Read a text file from Seafile."""
        try:
            # Get download link
            url = f"{self.base_url}/api2/repos/{self.library_id}/file/"
            response = requests.get(
                url,
                headers=self.headers,
                params={'p': path, 'reuse': '1'},
                timeout=10
            )

            if response.status_code != 200:
                logger.error(f"Failed to get download link for {path}: {response.status_code}")
                return None

            download_url = response.text.strip().strip('"')

            # Download file
            file_response = requests.get(download_url, timeout=30)
            if file_response.status_code == 200:
                return file_response.text
            else:
                logger.error(f"Failed to download file {path}: {file_response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Read file failed for {path}: {e}")
            return None

    def read_json(self, path: str) -> Optional[Dict]:
        """Read a JSON file from Seafile."""
        content = self.read_file(path)
        if content:
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode failed for {path}: {e}")
                return None
        return None

    def write_file(self, path: str, content: str) -> bool:
        """Write a text file to Seafile."""
        try:
            # Ensure parent directory exists
            parent_dir = str(Path(path).parent)
            self.ensure_dir_exists(parent_dir)

            # Get upload link
            url = f"{self.base_url}/api2/repos/{self.library_id}/upload-link/"
            response = requests.get(
                url,
                headers=self.headers,
                params={'p': parent_dir},
                timeout=10
            )

            if response.status_code != 200:
                logger.error(f"Failed to get upload link for {path}: {response.status_code}")
                return False

            upload_url = response.text.strip().strip('"')

            # Upload file
            filename = Path(path).name
            files = {'file': (filename, content.encode('utf-8'), 'text/plain')}
            data = {
                'parent_dir': parent_dir,
                'replace': '1'
            }

            upload_response = requests.post(
                upload_url,
                files=files,
                data=data,
                headers={'Authorization': f'Token {self.token}'},
                timeout=30
            )

            if upload_response.status_code in [200, 201]:
                logger.info(f"File written to {path}")
                return True
            else:
                logger.error(f"Upload failed for {path}: {upload_response.status_code} - {upload_response.text[:200]}")
                return False

        except Exception as e:
            logger.error(f"Write file failed for {path}: {e}")
            return False

    def upload_file(self, local_path: str, seafile_path: str) -> bool:
        """Upload a local file to Seafile."""
        try:
            with open(local_path, 'rb') as f:
                content = f.read()

            # Ensure parent directory exists
            parent_dir = str(Path(seafile_path).parent)
            self.ensure_dir_exists(parent_dir)

            # Get upload link
            url = f"{self.base_url}/api2/repos/{self.library_id}/upload-link/"
            response = requests.get(
                url,
                headers=self.headers,
                params={'p': parent_dir},
                timeout=10
            )

            if response.status_code != 200:
                logger.error(f"Failed to get upload link for {seafile_path}: {response.status_code}")
                return False

            upload_url = response.text.strip().strip('"')

            # Upload file
            filename = Path(seafile_path).name
            files = {'file': (filename, content)}
            data = {
                'parent_dir': parent_dir,
                'replace': '1'
            }

            upload_response = requests.post(
                upload_url,
                files=files,
                data=data,
                headers={'Authorization': f'Token {self.token}'},
                timeout=60
            )

            if upload_response.status_code in [200, 201]:
                logger.info(f"Uploaded {local_path} to {seafile_path}")
                return True
            else:
                logger.error(f"Upload failed for {seafile_path}: {upload_response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Upload file failed for {local_path} -> {seafile_path}: {e}")
            return False

    def write_json(self, path: str, data: Dict) -> bool:
        """Write a JSON file to Seafile."""
        content = json.dumps(data, indent=2)
        return self.write_file(path, content)

    def dir_exists(self, path: str) -> bool:
        """Check if a directory exists in Seafile."""
        try:
            url = f"{self.base_url}/api2/repos/{self.library_id}/dir/"
            response = requests.get(
                url,
                headers=self.headers,
                params={'p': path},
                timeout=10
            )
            # 200 means directory exists, 404 means it doesn't
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Dir exists check failed for {path}: {e}")
            return False

    def ensure_dir_exists(self, path: str) -> bool:
        """Ensure a directory exists in Seafile. Only creates if it doesn't exist."""
        try:
            # Split path and create each directory level
            path_parts = [p for p in path.strip('/').split('/') if p]
            current_path = ""

            for part in path_parts:
                current_path = f"{current_path}/{part}" if current_path else f"/{part}"

                # Check if directory already exists before creating
                if self.dir_exists(current_path):
                    logger.debug(f"Directory already exists: {current_path}")
                    continue

                # Directory doesn't exist, create it
                url = f"{self.base_url}/api2/repos/{self.library_id}/dir/"
                response = requests.post(
                    url,
                    headers=self.headers,
                    data={'operation': 'mkdir'},
                    params={'p': current_path},
                    timeout=10
                )

                # 200/201 = created, 409 = already exists (race condition), all OK
                if response.status_code in [200, 201, 409]:
                    logger.debug(f"Directory created/exists: {current_path}")
                else:
                    logger.warning(f"Dir creation issue for {current_path}: {response.status_code} - {response.text[:100]}")

            return True

        except Exception as e:
            logger.error(f"Ensure dir failed for {path}: {e}")
            return False

    def list_dir(self, path: str) -> Optional[List[Dict]]:
        """List contents of a directory in Seafile."""
        try:
            url = f"{self.base_url}/api/v2.1/repos/{self.library_id}/dir/"
            response = requests.get(
                url,
                headers=self.headers,
                params={'p': path},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return data.get('dirent_list', [])
            else:
                logger.debug(f"List dir failed for {path}: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"List dir error for {path}: {e}")
            return None

    def get_share_link(self, path: str) -> Optional[str]:
        """Get a public share link for a file or directory."""
        try:
            url = f"{self.base_url}/api/v2.1/share-links/"
            data = {
                'repo_id': self.library_id,
                'path': path,
                'permissions': 'r'  # Read-only
            }

            response = requests.post(
                url,
                headers=self.headers,
                json=data,
                timeout=10
            )

            if response.status_code in [200, 201]:
                result = response.json()
                return result.get('link')
            else:
                logger.error(f"Failed to create share link for {path}: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Get share link failed for {path}: {e}")
            return None
