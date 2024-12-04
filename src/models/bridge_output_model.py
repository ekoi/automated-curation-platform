from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum, auto
from typing import List, Optional

from pydantic import BaseModel, Field

from src.dbz import DepositStatus


class ResponseContentType(StrEnum):
    """
    Enumeration for response content types.

    Attributes:
        XML (auto): XML content type.
        JSON (auto): JSON content type.
        TEXT (auto): Plain text content type.
        RDF (auto): RDF content type.
        UNDEFINED (auto): Undefined content type.
    """
    XML = auto()
    JSON = auto()
    TEXT = auto()
    RDF = auto()
    UNDEFINED = auto()


class IdentifierProtocol(StrEnum):
    """
    Enumeration for identifier protocols.

    Attributes:
        DOI (auto): Digital Object Identifier.
        HANDLE (auto): Handle System identifier.
        URN_NBN (str): Uniform Resource Name for National Bibliography Number.
        URN_UUID (str): Uniform Resource Name for Universally Unique Identifier.
        SWHID (auto): Software Heritage identifier.
        UNDEFINED (auto): Undefined identifier protocol.
    """
    DOI = auto()
    HANDLE = auto()
    URN_NBN = 'urn:nbn'
    URN_UUID = 'urn:uuid',
    SWHID = auto()
    UNDEFINED = auto()


class IdentifierItem(BaseModel):
    """
    Data model for an identifier item.

    Attributes:
        value (str): The value of the identifier.
        protocol (IdentifierProtocol): The protocol of the identifier.
        url (Optional[str]): The URL associated with the identifier.
    """
    value: str = None
    protocol: IdentifierProtocol = IdentifierProtocol.DOI
    url: Optional[str] = None


class TargetResponse(BaseModel):
    """
    Data model for target response.

    Attributes:
        url (Optional[str]): The URL of the target response.
        status_code (int): The status code of the target response, aliased as 'status-code'.
        duration (float): The duration of the response.
        status (Optional[str]): The status of the response.
        error (Optional[str]): The error message of the response.
        message (str): The message of the response.
        identifiers (Optional[List[IdentifierItem]]): The list of identifiers associated with the response.
        content (str): The content of the response.
        content_type (ResponseContentType): The content type of the response, aliased as 'content-type'.
    """
    url: Optional[str] = None
    status_code: int = Field(default=-10122004, alias='status-code')
    duration: float = 0.0
    error: Optional[str] = None
    identifiers: Optional[List[IdentifierItem]] = None
    content: dict|str = None
    content_type: ResponseContentType = Field(None, alias='content-type')


class TargetDataModel(BaseModel):
    """
    Data model for bridge output data.

    Attributes:
        deposit_time (Optional[str]): The time of the deposit, formatted as a string, aliased as 'deposit-time'.
        deposit_status (Optional[DepositStatus]): The status of the deposit, aliased as 'deposit-status'.
        payload (Optional[str]): The payload data associated with the deposit.
        deposited_metadata (Optional[str]): Any message or text associated with the deposit.
        response (TargetResponse): The response data associated with the deposit.
    """
    deposit_time: Optional[str] = Field(datetime.now(timezone.utc).isoformat(), alias='deposit-time')
    deposit_status: Optional[DepositStatus] = Field(None, alias='deposit-status')
    payload: Optional[dict|str] = Field(None, alias='payload')
    deposited_metadata: Optional[dict|str] = Field(None, alias='deposited-metadata')  #
    response: TargetResponse = Field(default_factory=TargetResponse)


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
