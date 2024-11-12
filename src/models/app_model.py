from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class ResponseDataModel(BaseModel):
    """
    Data model for response data.

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
    release_version: str


class TargetApp(BaseModel):
    """
    Data model for target application.

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
    deposit_time: str = Field(None, alias='deposit-time')
    duration: str = ''
    output_response: Dict[str, Any] = Field('', alias='output-response')


class Asset(BaseModel):
    """
    Data model for an asset.

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
    md: str = ''
    created_date: str = Field(None, alias='created-date')
    saved_date: str = Field(None, alias='saved-date')
    submitted_date: str = Field(None, alias='submitted-date')
    release_version: str = Field(None, alias='release-version')
    version: str = ''
    targets: List[TargetApp] = []


class OwnerAssetsModel(BaseModel):
    """
    Data model for owner assets.

    Attributes:
        owner_id (str): The ID of the owner, aliased as 'owner-id'.
        assets (List[Asset]): The list of assets owned by the owner.
    """
    owner_id: str = Field(None, alias='owner-id')
    assets: List[Asset] = []

json_data = {
    "owner-id": "",
    "assets": [
        {
            "dataset-id": "",
            "title": "ds.title",
            "created-date": "ds.created_date",
            "saved-date": "ds.saved_date",
            "submitted-date": "ds.submitted_date",
            "release-version": "ds.release_version",
            "version": "ds.version",
            "targets": [
                {
                    "repo-name": "",
                    "display-name": "",
                    "deposit-status": "",
                    "deposit-time": "",
                    "duration": "",
                    "output-response": {}
                }
            ]
        }
    ]
}
