from __future__ import annotations

from datetime import datetime
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
    status: Optional[str] = None
    error: Optional[str] = None
    message: str = None
    identifiers: Optional[List[IdentifierItem]] = None
    content: str = None
    content_type: ResponseContentType = Field(None, alias='content-type')


class BridgeOutputDataModel(BaseModel):
    """
    Data model for bridge output data.

    Attributes:
        deposit_time (Optional[str]): The time of the deposit, formatted as a string, aliased as 'deposit-time'.
        deposit_status (DepositStatus): The status of the deposit, aliased as 'deposit-status'.
        notes (Optional[str]): Any message or text associated with the deposit.
        response (TargetResponse): The response data associated with the deposit.
    """
    deposit_time: Optional[str] = Field(datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f"), alias='deposit-time')
    deposit_status: DepositStatus = Field(DepositStatus.UNDEFINED, alias='deposit-status')
    notes: Optional[str] = "" # This is for any message/text
    response: TargetResponse = Field(default_factory=TargetResponse)


json_output_model = {
    "deposit-time": "",
    "deposit-status": "initial",
    "duration": 0.0,
    "response": {
        "url": "",
        "status-code": 200,
        "status": "",
        "error": "",
        "message": "Any message from response.",
        "identifiers": [
            {
                "value": "doi",
                "protocol": "doi",
                "url": ""
            },
            {
                "value": "doi",
                "protocol": IdentifierProtocol.DOI
            }
        ],
        "content": "",
        "content-type": ResponseContentType.XML
    }
}
response_json = {
    "url": "",
    "status-code": 200,
    "error": "",
    "message": "Any message from response.",
    "identifiers": [],
    "content": "",
    "content-type": ResponseContentType.XML
}


