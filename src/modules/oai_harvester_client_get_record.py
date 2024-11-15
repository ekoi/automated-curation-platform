from __future__ import annotations

import json
from datetime import datetime

from sickle import Sickle

from src.bridge import Bridge
from src.commons import logger, db_manager, transform, transform_xml, settings
from src.dbz import DepositStatus
from src.models.bridge_output_model import BridgeOutputDataModel, TargetResponse, ResponseContentType, IdentifierItem


class OaiHarvesterClientGetRecord(Bridge):

    def execute(self) -> BridgeOutputDataModel:
        logger(f'Harvesting of {self.target.repo_name}', settings.LOG_LEVEL, self.app_name)
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
        bridge_output_model = BridgeOutputDataModel(notes="", response=target_repo)
        bridge_output_model.deposit_status = DepositStatus.FINISH
        bridge_output_model.response = target_repo
        bridge_output_model.deposit_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")
        return bridge_output_model
