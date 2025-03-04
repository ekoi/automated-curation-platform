from __future__ import annotations

from typing import List

from pydantic import BaseModel


class Metadata(BaseModel):
    """
    Data model for metadata.

    Attributes:
        relativePath (str): The relative path of the file.
        name (str): The name of the file.
        type (str): The type of the file.
        filetype (str): The file type of the file.
        filename (str): The filename of the file.
    """
    relativePath: str
    name: str
    type: str
    filetype: str
    filename: str


class Storage(BaseModel):
    """
    Data model for storage.

    Attributes:
        type (str): The type of storage.
        path (str): The path of the storage.
    """
    type: str
    path: str


class Model(BaseModel):
    """
    Data model for a file upload.

    Attributes:
        uuid (str): The unique identifier of the file.
        offset (int): The offset of the file.
        size (int): The size of the file.
        is_size_deferred (bool): Whether the size is deferred.
        metadata (Metadata): The metadata of the file.
        is_partial (bool): Whether the file is a partial upload.
        is_final (bool): Whether the file is the final upload.
        partial_uploads (List): The list of partial uploads.
        expires (str): The expiration date of the file.
        storage (Storage): The storage information of the file.
        created_at (str): The creation date of the file.
    """
    uuid: str
    offset: int
    size: int
    is_size_deferred: bool
    metadata: Metadata
    is_partial: bool
    is_final: bool
    partial_uploads: List
    expires: str
    storage: Storage
    created_at: str


json_data = '''{
  "uuid": "fd9ac8fbe56b4d6f931be890e5d0eb0b",
  "offset": 53668,
  "size": 53668,
  "is_size_deferred": false,
  "metadata": {
    "relativePath": "null",
    "name": "amalin.jpeg",
    "type": "image/jpeg",
    "filetype": "image/jpeg",
    "filename": "amalin.jpeg"
  },
  "is_partial": false,
  "is_final": true,
  "partial_uploads": [],
  "expires": "2023-12-13T05:29:02.880462",
  "storage": {
    "type": "filestore",
    "path": "./files/fd9ac8fbe56b4d6f931be890e5d0eb0b"
  },
  "created_at": "2023-12-12T04:29:02.865944"
}'''