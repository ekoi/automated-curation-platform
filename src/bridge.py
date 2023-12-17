from __future__ import annotations

import os
from abc import ABC, abstractmethod

from src.models.assistant_datamodel import Target
from src.models.bridge_output_model import BridgeOutputModel
from src.commons import settings, db_manager

from src.dbz import TargetRepo, DepositStatus, DatabaseManager, Dataset, DataFile

from dataclasses import dataclass, field


@dataclass(frozen=True, kw_only=True, slots=True)
class Bridge(ABC):
    """
    Abstract base class representing a bridge between the Assistant and a specific target repository.

    Attributes:
        dataset_id (str): Identifier for the dataset.
        target (Target): Information about the target repository.
        db_manager (DatabaseManager): Database manager for interacting with the data store.
        metadata_rec (Dataset): Record representing the dataset metadata.
        app_name (str): Name of the application associated with the dataset.
        data_file_rec (DataFile): Record representing the data file associated with the dataset.
        dataset_dir (str): Directory path for the dataset.

    Methods:
        __post_init__(): Initializes the Bridge object after its creation.
        deposit() -> BridgeOutputModel: Abstract method to deposit data into the target repository.
        save_state(bridge_output_model: BridgeOutputModel = None) -> type(None): Saves the state of the deposit
        process, updating the deposit status in the database.

    Note:
        This class is expected to be subclassed with a concrete implementation of the `deposit` method.
    """

    dataset_id: str
    target: Target
    db_manager: DatabaseManager = field(init=False)
    metadata_rec: Dataset = field(init=False)  # TODO: change to dataset_rec
    app_name: str = field(init=False)
    data_file_rec: DataFile = field(init=False)
    dataset_dir: str = field(init=False)

    def __post_init__(self):
        """
        Initializes the Bridge object after its creation.

        The method sets up various attributes by querying the database using the provided dataset_id.
        It also sets default values for attributes like `db_manager`, `metadata_rec`, `app_name`, `data_file_rec`,
        and `dataset_dir`.

        Note:
            This method is automatically called by the dataclasses module after the object is created.
        """
        object.__setattr__(self, 'db_manager', db_manager)
        object.__setattr__(self, 'metadata_rec', self.db_manager.find_dataset(self.dataset_id))
        object.__setattr__(self, 'app_name', self.metadata_rec.app_name)
        object.__setattr__(self, 'data_file_rec', self.db_manager.find_files(self.dataset_id))
        object.__setattr__(self, 'dataset_dir', os.path.join(settings.DATA_TMP_BASE_DIR,
                                                             self.app_name, self.dataset_id))
        self.save_state()

    @classmethod
    @abstractmethod
    def deposit(cls) -> BridgeOutputModel:
        """
        Abstract method to deposit data into the target repository.

        Subclasses must provide a concrete implementation of this method.

        Returns:
            BridgeOutputModel: An instance of BridgeOutputModel representing the output of the deposit process.
        """
        ...

    def save_state(self, bridge_output_model: BridgeOutputModel = None) -> type(None):
        """
        Saves the state of the deposit process, updating the deposit status in the database.

        Args:
            bridge_output_model (BridgeOutputModel, optional): An instance of BridgeOutputModel representing the
                output of the deposit process. Defaults to None.
        """
        deposit_status = DepositStatus.PROGRESS
        output = ''
        if bridge_output_model:
            print(bridge_output_model)
            deposit_status = bridge_output_model.deposit_status
            output = bridge_output_model.model_dump_json()
        db_manager.update_target_repo_deposit_status(TargetRepo(ds_id=self.dataset_id, name=self.target.repo_name,
                                                                deposit_status=deposit_status, output=output))
