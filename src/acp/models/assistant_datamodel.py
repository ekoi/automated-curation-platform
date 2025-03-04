from __future__ import annotations

import urllib
from enum import StrEnum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class TransformedMetadata(BaseModel):
    """
    Represents metadata for a transformed resource.

    Attributes:
    - transformer_url (Optional[str]): The URL of the transformer, if applicable.
    - name (str): The name of the transformed result.
    - dir (str): The directory for the transformed result.
    - restricted (Optional[bool]): Indicates if the resource is restricted.
    """
    transformer_url: Optional[str] = Field(None, alias='transformer-url')
    name: str
    dir: Optional[str] = None
    generate_file: Optional[bool] = Field(None, alias='generate-file')
    restricted: Optional[bool] = None


class ProcessedMetadata(BaseModel):
    hook_name: str = Field(..., alias='hook-name')
    process_function: str = Field(..., alias='process-function')
    service_url: Optional[str] = Field(None, alias='service-url')
    name: str
    dir: Optional[str] = None


class Metadata(BaseModel):
    """
    Represents metadata for a repository.

    Attributes:
    - specification (List[str]): A list of specifications associated with the repository.
    - transformed_metadata (List[TransformedMetadata]): A list of transformed metadata instances.
    """
    specification: Optional[List[str]] = None
    transformed_metadata: Optional[List[TransformedMetadata]] = Field(None, alias='transformed-metadata')
    processed_metadata: Optional[List[ProcessedMetadata]] = Field(None, alias='processed-metadata')


class Input(BaseModel):
    """
    Represents input data for a target.

    Attributes:
    - from_target_name (str): The name of the target from which the input is derived.
    """
    from_target_name: str = Field(default=None, alias='from-target-name')


class StorageType(StrEnum):
    """
    Enum representing different types of storage.

    Attributes:
    - FILE_SYSTEM: Represents file system storage.
    - S3: Represents Amazon S3 storage.
    """
    FILE_SYSTEM = 'FILE_SYSTEM'
    S3 = 's3'


class Target(BaseModel):
    """
    Represents a target in the repository assistant application.

    Attributes:
        repo_pid (str): A unique identifier for the repository. This field is required.
        repo_name (str): The name of the repository. This field is required.
        repo_display_name (str): The display name of the repository. This field is required.
        bridge_plugin_name (str): The class name of the bridge plugin. This field is required.
        base_url (str): The base URL of the repository. This field is required.
        target_url (str): The target URL of the repository. This field is required.
        username (str): The username for authentication. This field is required.
        password (str): The password for authentication. This field is required.
        metadata (Metadata): Metadata associated with the target repository. This field is required.
        initial_release_version (Optional[str]): The initial release version of the repository. This field is optional.
        input (Optional[Input]): Input data for the target. This field is optional.
    """
    repo_pid: str = Field(..., alias='repo-pid')
    repo_name: str = Field(..., alias='repo-name')
    repo_display_name: str = Field(..., alias='repo-display-name')
    bridge_plugin_name: str = Field(..., alias='bridge-plugin-name')
    base_url: Optional[str] = Field(default=None, alias='base-url')
    target_url: str = Field(..., alias='target-url')
    target_url_params: Optional[str] = Field(default=None, alias='target-url-params')
    payload: Optional[dict] = None
    username: Optional[str] = None
    password: Optional[str] = None
    metadata: Optional[Metadata] = None
    storage_type: Optional[StorageType] = Field(default=StorageType.FILE_SYSTEM, alias='storage-type')
    initial_release_version: Optional[str] = Field(default=None, alias='initial-release-version')
    input: Optional[Input] = None

    @field_validator('target_url', 'base_url', mode='before')
    def validate_urls(cls, v, field):
        if v:
            parsed_url = urllib.parse.urlparse(v)
            if field.field_name in ['target_url', 'base_url'] and parsed_url.scheme not in ['https', 'http', 'file', 'mailto', 's3']:
                raise ValueError(f"Invalid {field.output_name} URL: {v}")
        return v
    #
    # @field_validator('metadata', mode='before')
    # def validate_metadata(cls, v):
    #     print(v)
    #     if v and not isinstance(v, Metadata):
    #         raise ValueError("Invalid metadata")
    #     return v

class NotificationItem(BaseModel):
    """
    Represents a notification item.

    Attributes:
    - type (str): The type of notification.
    - conf (str): The configuration for the notification.
    """
    type: str
    conf: str


class FileConversion(BaseModel):
    """
    Represents a file conversion process.

    Attributes:
    - id (str): The unique identifier for the file conversion.
    - origin_type (str): The original file type. This field is aliased to 'origin-type'.
    - target_type (str): The target file type. This field is aliased to 'target-type'.
    - conversion_url (str): The URL for the conversion service. This field is aliased to 'conversion-url'.
    - notification (Optional[List[NotificationItem]]): A list of notification items associated with the conversion.
    """
    id: str
    origin_type: str = Field(..., alias='origin-type')
    target_type: str = Field(..., alias='target-type')
    conversion_url: str = Field(..., alias='conversion-url')
    notification: Optional[List[NotificationItem]] = None


class Enrichment(BaseModel):
    """
    Represents an enrichment process.

    Attributes:
    - id (str): The unique identifier for the enrichment.
    - name (str): The name of the enrichment.
    - service_url (str): The URL for the enrichment service. This field is aliased to 'service-url'.
    - result_url (str): The URL where the result of the enrichment can be found. This field is aliased to 'result-url'.
    - notification (Optional[List[NotificationItem]]): A list of notification items associated with the enrichment.
    - permission (Optional[str]): The permission level for the enrichment.
    """
    id: str
    name: str
    service_url: str = Field(..., alias='service-url')
    result_url: str = Field(..., alias='result-url')
    notification: Optional[List[NotificationItem]] = None
    permission: Optional[str] = None


class RepoAssistantDataModel(BaseModel):
    """
    Represents the data model for the repository assistant.

    Attributes:
    - assistant_config_name (str): The name of the assistant configuration. This field is aliased to 'assistant-config-name'.
    - description (str): A description of the repository assistant.
    - app_name (str): The name of the application. This field is aliased to 'app-name'.
    - app_config_url (str): The URL for the application configuration. This field is aliased to 'app-config-url'.
    - targets (List[Target]): A list of target repositories.
    - file_conversions (Optional[List[FileConversion]]): A list of file conversion processes. This field is aliased to 'file-conversions'.
    - enrichments (Optional[List[Enrichment]]): A list of enrichment processes.
    """
    assistant_config_name: str = Field(..., alias='assistant-config-name')
    description: Optional[str] = None
    app_name: str = Field(..., alias='app-name')
    app_config_url: Optional[str] = Field(None, alias='app-config-url')
    targets: List[Target]
    file_conversions: Optional[List[FileConversion]] = Field(None, alias='file-conversions')
    enrichments: Optional[List[Enrichment]] = None
