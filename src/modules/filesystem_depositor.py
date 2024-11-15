from __future__ import annotations

import urllib.parse
import json

from src.bridge import Bridge
from src.commons import logger, settings
from src.models.bridge_output_model import BridgeOutputDataModel


class FileSystem(Bridge):

    def execute(self) -> BridgeOutputDataModel:
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


        bridge_output_model = BridgeOutputDataModel()

        return bridge_output_model
