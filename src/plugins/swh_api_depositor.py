from __future__ import annotations

import json
from time import sleep

import jmespath
import requests

from src.bridge import Bridge
from src.commons import logger, settings
from src.dbz import DepositStatus
from src.models.bridge_output_model import TargetDataModel, TargetResponse, ResponseContentType, IdentifierItem, \
    IdentifierProtocol


class SwhApiDepositor(Bridge):
    """
    A class to handle the deposit of metadata to the Software Heritage (SWH) API.

    Inherits from:
        Bridge: The base class for all bridge implementations.
    """

    def job(self) -> TargetDataModel:
        """
        Executes the deposit process to the SWH API.

        This method logs the start of the deposit process, constructs the target URL, and sends a POST request to the SWH API.
        It then polls the SWH API for the status of the deposit until it is either successful or fails, logging the progress
        and updating the bridge output model accordingly.

        Returns:
        BridgeOutputDataModel: The output model containing the response from the SWH API and the status of the deposit.
        """
        logger(f'DEPOSIT to {self.target.repo_name}', settings.LOG_LEVEL, self.app_name)
        target_response = TargetResponse()
        target_swh = jmespath.search("metadata[*].fields[?name=='repository_url'].value",
                                     json.loads(self.metadata_rec.md))
        tdm = TargetDataModel(response=target_response)
        headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {settings.SWH_ACCESS_TOKEN}'}
        logger(f'self.target.target_url: {self.target.target_url}', settings.LOG_LEVEL, self.app_name)
        swh_url = f'{self.target.target_url}/{target_swh[0][0]}/'
        logger(f'swh_url: {swh_url}', settings.LOG_LEVEL, self.app_name)
        api_resp = requests.post(swh_url, data="{}", headers=headers)
        logger(f'{api_resp.status_code} {api_resp.text}', settings.LOG_LEVEL, self.app_name)
        if api_resp.status_code == 200:
            api_resp_json = api_resp.json()
            logger(f'swh_api response json: {json.dumps(api_resp_json)}', settings.LOG_LEVEL, self.app_name)
            goto_sleep = False
            counter = 0  # TODO: Refactor using Tenancy!
            while True and (counter < settings.SWH_API_MAX_RETRIES):
                counter += 1
                swh_check_url = api_resp_json.get("request_url")
                check_resp = requests.get(swh_check_url, headers=headers)
                if check_resp.status_code == 200:
                    swh_resp_json = check_resp.json()
                    logger(f'{swh_check_url} response: {json.dumps(swh_resp_json)}', settings.LOG_LEVEL, self.app_name)
                    if swh_resp_json.get('save_task_status') == DepositStatus.FAILED:
                        tdm.deposit_status = DepositStatus.FAILED
                        logger(f"save_task_status is failed.", 'error', self.app_name)
                        target_response.content = swh_resp_json
                        target_response.content_type = ResponseContentType.JSON
                        break
                    elif swh_resp_json.get('snapshot_swhid'):
                        tdm.deposit_status = DepositStatus.FINISH
                        target_response.status_code = check_resp.status_code
                        target_response.content_type = ResponseContentType.JSON
                        target_response.content = json.dumps(swh_resp_json)
                        identifier_items = []
                        target_response.identifiers = identifier_items
                        ideni = IdentifierItem(value=swh_resp_json.get('snapshot_swhid'), url=swh_url,
                                               protocol=IdentifierProtocol('swhid'))
                        identifier_items.append(ideni)
                        break
                    else:
                        goto_sleep = True
                if goto_sleep:
                    sleep(settings.SWH_DELAY_POLLING)

        else:
            logger(f'ERROR api_resp.status_code: {api_resp.status_code}', settings.LOG_LEVEL, self.app_name)
            target_response.status_code = api_resp.status_code
            tdm.deposit_status = DepositStatus.ERROR
            target_response.error = json.dumps(api_resp.json())
            target_response.content_type = ResponseContentType.JSON
            target_response.status = DepositStatus.ERROR
            target_response.url = swh_url
            target_response.content = json.dumps(api_resp.json())
            logger(f'tdm: {tdm.model_dump(by_alias=True)}', settings.LOG_LEVEL,
                   self.app_name)

        return tdm