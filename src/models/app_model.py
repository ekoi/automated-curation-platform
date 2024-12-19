from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class ResponseDataModel(BaseModel):
    """
    Data model for response data.
    The ResponseDataModel class is a data model defined using the BaseModel class from the pydantic library.
    This class is designed to represent the response data structure with specific attributes.
    The class includes three attributes: status, dataset_id, and start_process.
    The status attribute is a string that represents the status of the response and is initialized with an empty string

    Attributes:
        status (str): The status of the response.
        dataset_id (str): The ID of the dataset, aliased as 'dataset-id'.
        start_process (Optional[bool]): Indicates whether to start the process, aliased as 'start-process'.
    """
    status: str = ''
    dataset_id: str = Field('', alias='dataset-id')
    start_process: Optional[bool] = Field(False, alias='start-process')


@dataclass(frozen=True, kw_only=True)
class InboxDatasetDataModel:
    """
    Data model for inbox dataset.
    The InboxDatasetDataModel class is a data model defined using Python's dataclasses plugin.
    This class is designed to represent the metadata of an inbox dataset.

    Attributes:
        assistant_name (str): The name of the assistant.
        target_creds (str): The credentials for the target.
        owner_id (str): The ID of the owner.
        title (str): The title of the dataset. Defaults to an empty string.
        metadata (dict): The metadata associated with the dataset.
        release_version (str): The release version of the dataset.
    """
    assistant_name: str
    target_creds: str
    owner_id: str
    title: str = ''
    metadata: dict
    metadata_type: str = ''
    release_version: str


class TargetApp(BaseModel):
    """
    Data model for target application.
    The TargetApp class is designed to hold various attributes related to a target application, such as repo_name,
    display_name, deposit_status, deposit_time, duration, and output_response. These attributes are used
    to store information about the repository, its display name, the status and time of deposits,
    the duration of processes, and the output response from the target application.
    By including the diff attribute, the TargetApp class can also keep track of any differences or changes
    that may occur within the target application, providing a flexible way to store and manage this information.

    Attributes:
        repo_name (str): The name of the repository, aliased as 'repo-name'.
        display_name (str): The display name of the target application, aliased as 'display-name'.
        deposit_status (str): The deposit status of the target application, aliased as 'deposit-status'.
        deposit_time (str): The deposit time of the target application, aliased as 'deposit-time'.
        duration (str): The duration of the process.
        output_response (Dict[str, Any]): The output response from the target application, aliased as 'output-response'.
    """
    repo_name: str = Field(None, alias='repo-name')
    display_name: str = Field(None, alias='display-name')
    deposit_status: str = Field(None, alias='deposit-status')
    deposit_time: datetime|str = Field(None, alias='deposit-time')
    duration: float|str = ''
    output_response: dict = Field(None, alias='output-response')
    diff: dict = {}


class Asset(BaseModel):
    """
    Data model for an asset.
    The Asset class is a data model defined using the BaseModel class from the pydantic library.
    This class is designed to represent an asset with various attributes related to its metadata and
    associated target applications.
    The class includes several attributes, each with specific types and optional aliases.

    Attributes:
        dataset_id (str): The ID of the dataset, aliased as 'dataset-id'.
        title (str): The title of the asset.
        md (str): The metadata of the asset.
        created_date (str): The creation date of the asset, aliased as 'created-date'.
        saved_date (str): The saved date of the asset, aliased as 'saved-date'.
        submitted_date (str): The submitted date of the asset, aliased as 'submitted-date'.
        release_version (str): The release version of the asset, aliased as 'release-version'.
        version (str): The version of the asset.
        targets (List[TargetApp]): The list of target applications associated with the asset.
    """
    dataset_id: str = Field(None, alias='dataset-id')
    title: str = ''
    md: dict|str = ''
    created_date: datetime|str = Field(None, alias='created-date')
    saved_date: datetime|str = Field(None, alias='saved-date')
    submitted_date: datetime|str = Field(None, alias='submitted-date')
    release_version: str = Field(None, alias='release-version')
    version: str = ''
    targets: List[TargetApp] = []


class OwnerAssetsModel(BaseModel):
    """
    Data model for owner assets.
    The OwnerAssetsModel class is a data model defined using the BaseModel class from the pydantic library.
    This class is designed to represent the assets owned by a specific owner, encapsulating the owner's ID and a list of assets.
    The class includes two main attributes: owner_id and assets. The owner_id attribute is a string that is aliased
    as owner-id, which helps in mapping the attribute to a different name when working with external data sources

    Attributes:
        owner_id (str): The ID of the owner, aliased as 'owner-id'.
        assets (List[Asset]): The list of assets owned by the owner.
    """
    owner_id: str = Field(None, alias='owner-id')
    assets: List[Asset] = []
