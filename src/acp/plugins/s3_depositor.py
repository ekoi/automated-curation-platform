from __future__ import annotations

import json
import logging

from src.acp.bridge import Bridge
from src.acp.commons import settings, create_s3_client
from src.acp.models.bridge_output_model import TargetDataModel


class S3Depositor(Bridge):
    """
    A class to handle the deposit of metadata to an S3 bucket.

    Inherits from:
        Bridge: The base class for all bridge implementations.
    """

    def job(self) -> TargetDataModel:
        """
        Executes the deposit process to the S3 bucket.

        This method logs the start of the deposit process, parses the metadata, and uploads it to the specified S3 bucket.
        It initializes the bridge output model and returns it.

        Returns:
        BridgeOutputDataModel: The output model for the S3 deposit process.
        """
        logging.info(f'Depositing to S3: {self.target.repo_name}')
        metadata = json.loads(self.metadata_rec.md)

        s3_client = create_s3_client()
        s3_client.put_object(Bucket=settings.S3_BUCKET_NAME, Key=f'{settings.S3_Key}', Body=json.dumps(metadata))

        bridge_output_model = TargetDataModel()

        return bridge_output_model
