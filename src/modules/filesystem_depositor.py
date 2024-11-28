from __future__ import annotations

import urllib.parse
import json

from src.bridge import Bridge
from src.commons import logger, settings
from src.models.bridge_output_model import TargetDataModel


class FileSystem(Bridge):
    """
    A class to handle the deposit of metadata to the filesystem.

    Inherits from:
        Bridge: The base class for all bridge implementations.
    """

    def job(self) -> TargetDataModel:
        """
        Executes the deposit process to the filesystem.

        This method logs the start of the deposit process, parses the target URL, and saves the metadata to a file.
        It raises a ValueError if the URL scheme is not 'file' or if the path is invalid.

        Returns:
        BridgeOutputDataModel: The output model for the filesystem deposit process.
        """
        logger(f'Depositing to File: {self.target.repo_name}', settings.LOG_LEVEL, self.app_name)
        metadata = json.loads(self.metadata_rec.md)

        parsed_url = urllib.parse.urlparse(self.target.target_url)

        if parsed_url.scheme != 'file' or not parsed_url.path:
            raise ValueError("Invalid file URL")

        file_path = parsed_url.path
        print(file_path)
        # save to file
        with open(f'{self.dataset_dir}/{metadata["title"]}.json', 'w') as f:
            f.write(metadata)

        bridge_output_model = TargetDataModel()

        return bridge_output_model