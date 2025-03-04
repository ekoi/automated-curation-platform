from __future__ import annotations

import json
import logging
from datetime import datetime

import requests
from sickle import Sickle

from src.acp.bridge import Bridge
from src.acp.commons import db_manager, transform_xml
from src.acp.dbz import DepositStatus
from src.acp.models.bridge_output_model import TargetDataModel, TargetResponse, ResponseContentType, IdentifierItem


class OaiHarvesterClientGetRecord(Bridge):
    """
    A class to handle the harvesting of metadata records from an OAI-PMH (Open Archives Initiative Protocol for Metadata Harvesting) repository.

    Inherits from:
        Bridge: The base class for all bridge implementations.
    """

    def job(self) -> TargetDataModel:
        """
        Executes the harvesting process from the OAI-PMH repository.

        This method logs the start of the harvesting process, retrieves the metadata record from the OAI-PMH repository,
        transforms the metadata, updates the dataset metadata in the database, and constructs the bridge output model.

        Returns:
        BridgeOutputDataModel: The output model containing the response from the OAI-PMH repository and the status of the harvesting process.
        """
        logging.info(f'Harvesting of {self.target.repo_name}')
        oai_metadata = json.loads(self.metadata_rec.md)

        sickle = Sickle(self.target.target_url)
        query_dict = dict(pair.split('=') for pair in self.target.target_url_params.split('&'))
        record = sickle.GetRecord(metadataPrefix=query_dict["metadataPrefix"], identifier=oai_metadata['title'])
        print(record)
        dv_metadata = transform_xml(
            transformer_url=self.target.metadata.transformed_metadata[0].transformer_url,
            str_tobe_transformed=record.raw
        )
        print(dv_metadata)

        db_manager.update_dataset_md(self.dataset_id, dv_metadata)
        target_repo = TargetResponse(url=self.target.target_url, status=DepositStatus.FINISH,
                                     message="", content=record.raw, content_type=ResponseContentType.XML)
        target_repo.url = self.target.target_url
        target_repo.status_code = 200
        identi = IdentifierItem(value=oai_metadata['title'], url="")
        target_repo.identifiers = [identi]
        bridge_output_model = TargetDataModel(deposited_metadata="", response=target_repo)
        bridge_output_model.deposit_status = DepositStatus.FINISH
        bridge_output_model.response = target_repo
        bridge_output_model.deposit_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")
        return bridge_output_model

    def _version(self) -> str:
        """
        Returns the version of the OAI-PMH harvester client.

        Returns:versioning

        str: The version of the OAI-PMH harvester client.
        """
        return {"workflow_orchestrator": None, "created_on": "26-11-2024 12:05:19", "DANS-transformer-service": {"name": "DANS-transformer-service", "version": "0.5.9", "docker-image": "ekoindarto/dans-transformer-service:0.5.9", "endpoint": "https://transformer.labs.dansdemo.nl/transform-xml-to-json/true"}, "dataverse-importer": {"name": "dataverse-importer", "version": None, "docker-image": "fjodorvr/dataverse-importer:0.1.1", "endpoint": "https://dataverse-importer.labs.dansdemo.nl", "github-release": "https://github.com/odissei-data/dataverse-importer/releases/tag/v0.1.0-alpha"}}

    def store_workflow_version(version_dict):
        """ Stores the workflow version dictionary.

        The workflow version dictionary is stored using the version-tracker.
        A POST request is made to store the dict, which then response with an ID.
        This ID is used to formulate a GET request that can be used to fetch
        the dictionary.

        :param version_dict: The complete version dictionary of the workflow.
        :return: A GET request.
        """
        url = 'https://version-tracker.labs.dansdemo.nl/store'
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json'
        }

        response = requests.post(url, headers=headers,
                                 data=json.dumps(version_dict))
        if not response.ok:
            print(response.text)
            return None

        version_id = response.json()['id']
        return 'https://version-tracker.labs.dansdemo.nl/retrieve/' + version_id