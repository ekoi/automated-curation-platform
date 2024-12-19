from __future__ import annotations

import os
import urllib.parse
import json

from src.bridge import Bridge
from src.commons import logger, settings
from src.dbz import DepositStatus
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

        dest_file_name = (f'{parsed_url.path}/{self.target.metadata.transformed_metadata[0].target_dir}/'
                          f'{self.target.metadata.transformed_metadata[0].name}')

        os.makedirs(os.path.dirname(dest_file_name), exist_ok=True)

        # save to file
        with open(dest_file_name, 'w') as f:
            f.write(json.dumps(metadata))

        tdm = TargetDataModel()
        tdm.deposit_status = DepositStatus.SUCCESS

        return tdm