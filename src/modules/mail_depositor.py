from __future__ import annotations

from src.bridge import Bridge
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
        bridge_output_model = TargetDataModel()

        return bridge_output_model