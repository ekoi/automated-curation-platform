from __future__ import annotations

import json
import urllib

from src.bridge import Bridge
from src.commons import logger, settings, send_mail
from src.dbz import DepositStatus
from src.models.bridge_output_model import TargetDataModel


class Mail(Bridge):
    """
    A class to handle the deposit of metadata via email.

    Inherits from:
        Bridge: The base class for all bridge implementations.
    """

    def job(self) -> TargetDataModel:
        """
        Executes the deposit process via email.

        This method initializes the bridge output model and returns it.

        Returns:
        BridgeOutputDataModel: The output model for the email deposit process.
        """

        logger(f'Depositing to File: {self.target.repo_name}', settings.LOG_LEVEL, self.app_name)

        parsed_url = urllib.parse.urlparse(self.target.target_url)
        if parsed_url.scheme != 'mailto' or not parsed_url.path:
            raise ValueError("Invalid file URL")

        tdm = TargetDataModel()
        try:
            send_mail(self.metadata_rec.title, self.metadata_rec.md, [parsed_url.path])
            tdm.deposit_status = DepositStatus.SUCCESS
        except ValueError as e:
            logger(f'Failed to send email: {e}', settings.LOG_LEVEL, self.app_name)
            tdm.deposit_status = DepositStatus.FAILED

        return tdm