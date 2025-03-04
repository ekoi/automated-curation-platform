from __future__ import annotations

import json
import logging
from datetime import datetime
from time import sleep

import requests
import sword2.deposit_receipt as dr
from requests.auth import HTTPBasicAuth

from src.acp.bridge import Bridge
from src.acp.commons import settings, DepositStatus, transform, db_manager
from src.acp.models.bridge_output_model import TargetDataModel, TargetResponse


class SwhSwordDepositor(Bridge):
    """
    A class to handle the deposit of metadata to the Software Heritage (SWH) API using the SWORD protocol.

    Inherits from:
        Bridge: The base class for all bridge implementations.
    """

    def job(self) -> TargetDataModel:
        """
        Executes the deposit process to the SWH API using the SWORD protocol.

        This method constructs the SWORD payload, sends a POST request to the SWH API, and handles the response.
        It polls the SWH API for the status of the deposit until it is either successful or fails, logging the progress
        and updating the bridge output model accordingly.

        Returns:
        BridgeOutputDataModel: The output model containing the response from the SWH API and the status of the deposit.
        """
        bridge_output_model = TargetDataModel()
        # Create SWORD payload
        swh_form_md = json.loads(self.metadata_rec.md)
        dv_target = db_manager.find_target_repo(self.dataset_id, self.target.input.from_target_name)
        if dv_target:
            swh_form_md.update({"doi": json.loads(dv_target.target_output)['response']['identifiers'][0]['value']})
        logging.info(f"SwhSwordDepositor- swh_form_md - after update (doi): {json.dumps(swh_form_md)}")
        str_sword_payload = transform(
            transformer_url=self.target.metadata.transformed_metadata[0].transformer_url,
            str_tobe_transformed=json.dumps(swh_form_md)
        )
        logging.info(f'deposit to "{self.target.target_url}"')
        logging.info(f'payload: "{str_sword_payload}"')
        headers = {
            'Content-Type': 'application/atom+xml;type=entry',
        }
        auth = HTTPBasicAuth(settings.swh_sword_username, settings.swh_sword_password)
        response = requests.post(self.target.target_url, headers=headers, auth=auth, data=str_sword_payload)
        logging.info(f'status_code: {response.status_code}. Response: {response.text}')
        if response.status_code == 200 or response.status_code == 201:  # TODO: remove 200, use only 201
            rt = response.text
            logging.info(f'sword response: {rt}')

            deposit_response = dr.Deposit_Receipt(xml_deposit_receipt=rt)
            if deposit_response.metadata['atom_deposit_status'][0] == 'deposited':
                return TargetDataModel(deposit_status=DepositStatus.DEPOSITED, deposited_metadata=rt)
            status_url = deposit_response.alternate
            logging.info(f'Status request send to {status_url}')
            counter = 0
            while True and (counter < settings.swh_api_max_retries):
                counter += 1
                sleep(settings.swh_delay_polling_sword)
                rsp = requests.get(status_url, headers=headers, auth=auth)
                if rsp.status_code == 200:
                    rsp_text = rsp.text
                    logging.info(f'response from {status_url} is {rsp_text}')
                    rsp_dep = dr.Deposit_Receipt(xml_deposit_receipt=rsp_text)
                    print(rsp_dep.metadata)
                    swh_metadata = rsp_dep.metadata
                    swh_deposit_status = swh_metadata.get('atom_deposit_status')
                    if swh_deposit_status and swh_deposit_status[0] == 'rejected':
                        return TargetDataModel(deposit_status=DepositStatus.FAILED, deposited_metadata=rsp_text)
                    if swh_deposit_status and swh_deposit_status[0] in [DepositStatus.DEPOSITED, "done"]:
                        target_repo = TargetResponse(url=self.target.target_url, status=DepositStatus.FINISH,
                                                     message=rsp_text, content=rsp_text)
                        target_repo.url = status_url
                        target_repo.status_code = rsp.status_code
                        target_repo.content = rsp_text
                        bridge_output_model.deposit_status = DepositStatus.FINISH
                        bridge_output_model.response = target_repo
                        bridge_output_model.deposit_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")
                        return bridge_output_model

                else:
                    raise ValueError(f'Error request to {status_url} with rsp.status_code: {rsp.status_code} and '
                                     f'rsp.text: {rsp.text}')
        else:
            bridge_output_model.deposit_status = DepositStatus.ERROR
            bridge_output_model.deposited_metadata = response.text
        return bridge_output_model