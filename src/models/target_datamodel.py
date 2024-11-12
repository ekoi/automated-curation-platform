from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Credentials(BaseModel):
    """
    Data model for credentials.

    Attributes:
        password (Optional[str]): The password for the credentials.
        username (Optional[str]): The username for the credentials.
    """
    password: Optional[str] = None
    username: Optional[str] = None


class TargetsCredential(BaseModel):
    """
    Data model for target credentials.

    Attributes:
        target_repo_name (str): The name of the target repository, aliased as 'target-repo-name'.
        credentials (Optional[Credentials]): The credentials associated with the target repository.
    """
    target_repo_name: str = Field(..., alias='target-repo-name')
    credentials: Optional[Credentials] = None


class TargetsCredentialsModel(BaseModel):
    """
    Data model for a list of target credentials.

    Attributes:
        targets_credentials (List[TargetsCredential]): The list of target credentials, aliased as 'targets-credentials'.
    """
    targets_credentials: List[TargetsCredential] = Field(
        ..., alias='targets-credentials'
    )

json_data={"targets-credentials":
[
    {
        "target-repo-name": "dans.sword.ssh.local",
        "credentials": {"password": "01bd92cf-de58-4389-942d-ebaec52fc073"}
    },
    {
        "target-repo-name": "dans.sword.ssh.local",
        "credentials": {
            "username": "eko",
            "password": "lamaKMI"
        }
    },
    {
        "target-repo-name": "dans.sword.ssh.local",
        "credentials": {
            "username": "eko"
        }
    },
    {
        "target-repo-name": "dans.sword.ssh.local"
    }
]
}