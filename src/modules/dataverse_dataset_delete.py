from __future__ import annotations

from datetime import datetime
import json

import requests

from src.bridge import Bridge
from src.dbz import DepositStatus
from src.models.bridge_output_model import BridgeOutputDataModel, TargetResponse, ResponseContentType


class DataverseDatasetDelete(Bridge):

    def execute(self) -> BridgeOutputDataModel:
        md_json = json.loads(self.metadata_rec.md)
        try:
            dv_pid = md_json["datasetVersion"]["datasetPersistentId"]
        except KeyError:
            return BridgeOutputDataModel(deposit_status="Dataset ID not found in metadata", notes="Dataset ID not found in metadata")

        headers = {
            "X-Dataverse-key": self.target.password
        }

        if self.target.initial_release_version and self.target.initial_release_version == "PUBLISH":
            # Delete published version
            url = self.target.target_url + "/destroy/" + self.target.target_url_params.replace("$PID", dv_pid)
            response = requests.delete(url, headers=headers)
            if response.status_code != 200:
                return BridgeOutputDataModel(deposit_status="Failed", notes="Dataset not found")
        else:
            # Delete draft version
            url = self.target.target_url + "?" + self.target.target_url_params.replace("$PID", dv_pid)
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                return BridgeOutputDataModel(deposit_status="Failed", notes="Dataset not found")

            dv_id = response.json()["data"]["id"]
            url = self.target.base_url + "/api/datasets/" + str(dv_id)
            response = requests.delete(url, headers=headers)
            if response.status_code != 200:
                return BridgeOutputDataModel(deposit_status="Failed", notes="Dataset not found")

        target_repo = TargetResponse(url=url, status=DepositStatus.FINISH,
                                     message="", content=json.dumps(response.json()), content_type=ResponseContentType.JSON)
        target_repo.url = url
        target_repo.status_code = response.status_code
        bridge_output_model = BridgeOutputDataModel(notes="", response=target_repo)
        bridge_output_model.deposit_status = DepositStatus.FINISH
        bridge_output_model.response = target_repo
        bridge_output_model.deposit_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")

        return bridge_output_model