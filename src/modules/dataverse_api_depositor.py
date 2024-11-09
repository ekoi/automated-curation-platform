import json
import math
import mimetypes
import os
import re
import time
import uuid
import zipfile
from datetime import datetime

import subprocess

import jmespath
import requests
from simple_file_checksum import get_checksum
from starlette import status

from src.bridge import Bridge, BridgeOutputDataModel
from src.commons import (
    settings,
    db_manager,
    transform,
    logger,
    handle_deposit_exceptions, dmz_dataverse_headers, upload_large_file, zip_with_progress,
    compress_zip_file, zip_a_zipfile_with_progress, escape_invalid_json_characters,
)
from src.dbz import ReleaseVersion, DataFile, DepositStatus, FilePermissions, DataFileWorkState
from src.models.bridge_output_model import IdentifierItem, IdentifierProtocol, TargetResponse, ResponseContentType


class DataverseIngester(Bridge):

    @handle_deposit_exceptions
    def execute(self) -> BridgeOutputDataModel:
        md_json = json.loads(self.metadata_rec.md)

        if self.target.input:
            input_from_prev_target = db_manager.find_target_repo(self.dataset_id, self.target.input.from_target_name)
            md_json[self.target.input.from_target_name] = json.loads(input_from_prev_target.target_output)['response']['identifiers'][0]['value']
            db_manager.update_dataset_md(self.dataset_id, json.dumps(md_json))

        files_metadata = jmespath.search('"file-metadata"[*]', md_json)

        if self.target.metadata and self.target.metadata.transformed_metadata:
            generated_files = self.__create_generated_files()
            for gf in generated_files:
                files_metadata.append({"name": gf.name, "mimetype": gf.mime_type, "private": gf.permissions == FilePermissions.PRIVATE})
            if generated_files:
                db_manager.insert_datafiles(generated_files)

        if files_metadata:
            md_json["file-metadata"] = files_metadata

        for file in db_manager.find_non_generated_files(dataset_id=self.dataset_id):
            escaped_file_name = file.name.replace('"', '\\"')
            f_json = jmespath.search(f'[?name == `{escaped_file_name}`]', files_metadata)
            f_json[0]["mimetype"] = file.mime_type

        str_updated_metadata_json = json.dumps(md_json)
        logger(f"str_updated_metadata_json: {str_updated_metadata_json}", settings.LOG_LEVEL, self.app_name)

        str_dv_metadata = self.__transform_to_dv_json_data(str_updated_metadata_json, "dataset-metadata.json")
        if isinstance(str_dv_metadata, BridgeOutputDataModel):
            return str_dv_metadata

        logger(f'deposit to "{self.target.target_url}"', settings.LOG_LEVEL, self.app_name)
        if self.target.target_url_params:
            self.target.target_url += "?" + self.target.target_url_params.replace("$PID", md_json["datasetVersion"]["datasetPersistentId"])

        dv_response = requests.post(self.target.target_url, headers=dmz_dataverse_headers('API_KEY', self.target.password), data=str_dv_metadata)
        logger(f"dv_response.status_code: {dv_response.status_code} dv_response.text: {dv_response.text}", settings.LOG_LEVEL, self.app_name)

        message = "Error"
        identifier_items = []
        logger(f'Ingesting metadata {self.dataset_id} to {self.target.target_url}', settings.LOG_LEVEL, self.app_name)

        if dv_response.status_code == 201:
            dv_response_json = dv_response.json()
            dv_id = dv_response_json["data"]["id"]
            logger(f"Data ingest successfully! {json.dumps(dv_response_json)}", settings.LOG_LEVEL, self.app_name)
            pid = dv_response_json["data"]["persistentId"]
            identifier_items.append(IdentifierItem(value=pid, url=f'{self.target.base_url}/dataset.xhtml?persistentId={pid}', protocol=IdentifierProtocol('doi')))
            logger(f"pid: {pid}", settings.LOG_LEVEL, self.app_name)
            ingest_status = DepositStatus.FINISH

            if self.target.metadata and self.target.metadata.transformed_metadata:
                ingest_file = self.__ingest_files(pid, str_updated_metadata_json)
                if ingest_file.get("status") == status.HTTP_200_OK:
                    ingest_status, message = DepositStatus.FINISH, "The dataset and its file is successfully ingested"
                    logger(f'Ingest FILE(s) successfully! {json.dumps(ingest_file)}', settings.LOG_LEVEL, self.app_name)
                    if self.target.initial_release_version == ReleaseVersion.PUBLISHED:
                        logger(f'Publish the dataset', settings.LOG_LEVEL, self.app_name)
                        publish_status = self.__publish_dataset(pid)
                        message = "The dataset is successfully published" if publish_status == status.HTTP_200_OK else "The dataset is unsuccessfully published"
                else:
                    ingest_status, message = DepositStatus.ERROR, ingest_file.get("message")
                    delete_response = requests.delete(f"{self.target.base_url}/api/datasets/{dv_id}/versions/:draft", headers=dmz_dataverse_headers('API_KEY', self.target.password))
                    logger(f"delete_response.status_code: {delete_response.status_code} delete_response.text: {delete_response.text}", settings.LOG_LEVEL, self.app_name)
        else:
            logger(f"Ingest failed with status code {dv_response.status_code}:", "error", self.app_name)
            logger(f'Response:  {dv_response.text}', "error", self.app_name)
            logger(f"Ingest metadata - str_dv_metadata {str_dv_metadata}", "error", self.app_name)
            logger(f"Ingest metadata - str_updated_metadata_json {str_updated_metadata_json}", "error", self.app_name)
            ingest_status, message = DepositStatus.ERROR, dv_response.status_code
            output_model = BridgeOutputDataModel(notes=message)
            output_model.deposit_status = ingest_status
            return output_model

        output_model = BridgeOutputDataModel(notes=message)
        output_model.deposit_status = ingest_status
        if output_model.deposit_status == DepositStatus.ERROR:
            logger(f"Error: {message}", settings.LOG_LEVEL, self.app_name)
            return output_model

        current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")
        output_model.deposit_time = current_time
        target_repo = TargetResponse(url=self.target.target_url, status=DepositStatus.FINISH, message=message,
                                     identifiers=identifier_items, content=dv_response.text)
        target_repo.content_type = ResponseContentType.JSON
        target_repo.status_code = dv_response.status_code
        output_model = BridgeOutputDataModel(notes=message, response=target_repo)
        output_model.deposit_time = current_time
        output_model.deposit_status = ingest_status
        return output_model

    def __transform_to_dv_json_data(self, str_updated_metadata_json, json_data_name: str) -> str | BridgeOutputDataModel:
        if self.target.metadata and self.target.metadata.transformed_metadata:
            transformer = [metadata for metadata in self.target.metadata.transformed_metadata if
                           metadata.name == json_data_name]
            if not transformer or len(transformer) != 1:
                logger(f"Error: Transformer not found or more than one transformer", settings.LOG_LEVEL, self.app_name)
                output_model = BridgeOutputDataModel(notes=f"Error: Transformer  '{json_data_name}' not found or more than one transformer")
                output_model.deposit_status = DepositStatus.ERROR
                return output_model
            str_dv_metadata = transform(
                transformer_url=transformer[0].transformer_url,
                str_tobe_transformed=str_updated_metadata_json
            )
            logger(f"TRANSFORMED str_dv_metadata: {str_updated_metadata_json}", settings.LOG_LEVEL, self.app_name)

            str_dv_metadata = self.__validate_json(str_dv_metadata)
            if not str_dv_metadata:
                logger(f"Error: Not valid json: {str_dv_metadata}", settings.LOG_LEVEL, self.app_name)
                output_model = BridgeOutputDataModel(notes="Error: Not valid json")
                output_model.deposit_status = DepositStatus.ERROR
                return output_model
        else:
            str_dv_metadata = str_updated_metadata_json
        return str_dv_metadata

    def __validate_json(self, str_dv_metadata):
        try:
            json.loads(str_dv_metadata)
        except json.JSONDecodeError as e:
            logger(f"Error: {e}", "error", self.app_name)
            str_dv_metadata = re.sub(r'[\x00-\x1F\x7F]', '', str_dv_metadata)
            try:
                json.loads(str_dv_metadata)
            except json.JSONDecodeError as e:
                logger(f"Error: {e}", "error", self.app_name)
                return None
            except Exception as e:
                logger(f"Error: {e}", "error", self.app_name)
                return None
        except Exception as e:
            logger(f"Error: {e}", "error", self.app_name)
            return None
        return str_dv_metadata

    def __create_generated_files(self) -> [DataFile]:
        generated_files = []
        for gnr_file in self.target.metadata.transformed_metadata:
            if gnr_file.target_dir:
                continue
            gf_path = os.path.join(self.dataset_dir, gnr_file.name)
            content = transform(gnr_file.transformer_url,
                                self.metadata_rec.md) if gnr_file.transformer_url else self.metadata_rec.md
            with open(gf_path, "wt") as f:
                f.write(content)
            gf_mimetype = mimetypes.guess_type(gf_path)[0]
            permissions = FilePermissions.PRIVATE if gnr_file.restricted else FilePermissions.PUBLIC
            generated_files.append(DataFile(
                ds_id=self.dataset_id, name=gnr_file.name, path=gf_path,
                size=os.path.getsize(gf_path), mime_type=gf_mimetype,
                checksum_value=get_checksum(gf_path, algorithm="MD5"),
                date_added=datetime.utcnow(), permissions=permissions,
                state=DataFileWorkState.GENERATED))
        return generated_files

    def __ingest_files(self, pid: str, str_updated_metadata_json: str) -> dict:
        logger(f'Ingesting files to {pid}', settings.LOG_LEVEL, self.app_name)
        str_dv_file = self.__transform_to_dv_json_data(str_updated_metadata_json, "dataset-files.json")
        if isinstance(str_dv_file, BridgeOutputDataModel):
            return {"status": "error", "message": str_dv_file.notes}

        for file in db_manager.find_non_generated_files(dataset_id=self.dataset_id):
            logger(f'Ingesting file {file.name}. Size: {file.size} Path: {file.path}', settings.LOG_LEVEL, self.app_name)
            jsonData = json.loads(str_dv_file).get(file.name)
            if not jsonData:
                continue

            start = time.perf_counter()
            data = {"jsonData": json.dumps(jsonData)}
            if file.mime_type == "application/zip":
                real_file_path = os.readlink(file.path)
                zip_file_name = f'{os.path.dirname(real_file_path)}/{file.name}'
                os.remove(file.path)
                os.rename(real_file_path, zip_file_name)
                logger(f'Start zipping file {file.name}. Real path: {zip_file_name}', settings.LOG_LEVEL, self.app_name)
                zip_a_zipfile_with_progress(zip_file_name, file.path)
                os.remove(zip_file_name)
                logger(f'Finished zipping file {file.name} to {real_file_path} in {round(time.perf_counter() - start, 2)} seconds', settings.LOG_LEVEL, self.app_name)

            url_base = f"{self.target.base_url}/api/datasets/:persistentId/add?persistentId={pid}"
            headers = dmz_dataverse_headers('API_KEY', self.target.password)
            timeout_seconds = settings.get("DATAVERSE_RESPONSE_TIMEOUT", 360000)
            logger(f'>>>> Start ingesting file {file.name}. Size: {file.size}. Ingest to {url_base}', settings.LOG_LEVEL, self.app_name)
            if file.size < settings.get("MAX_INGEST_SIZE_USING_PYTHON", 100000000):
                logger(f'++++ Ingest SMALL FILE using python: {file.name}', settings.LOG_LEVEL, self.app_name)
                with open(file.path, 'rb') as f:
                    files = {'file': (file.name, f)}
                    response_ingest_file = requests.post(url_base, files=files, data=data, headers=headers, timeout=timeout_seconds).json()
                    logger(f'>>>>>>>File {file.name} is successfully ingested', settings.LOG_LEVEL, self.app_name)
            else:
                logger(f'####### Ingest LARGE FILE using script: {file.name}', settings.LOG_LEVEL, self.app_name)
                jsonData_str = json.dumps(jsonData)
                try:
                    output = f'{settings.DATA_TMP_BASE_DIR}/{self.app_name}/{self.dataset_id}/{str(uuid.uuid4().int)}.txt'
                    logger(f'>>>>>>>Output: {output}', settings.LOG_LEVEL, self.app_name)
                    result = subprocess.run(
                        [settings.SHELL_SCRIPT_PATH, file.path, url_base, jsonData_str, self.target.password, output],
                        check=True, text=True, capture_output=True
                    )
                    logger(f'File {file.name} is successfully ingested', settings.LOG_LEVEL, self.app_name)
                    logger(f'Response: {result.stdout}', settings.LOG_LEVEL, self.app_name)
                    response_ingest_file = json.loads(result.stdout)
                except subprocess.CalledProcessError as e:
                    logger(f'File {file.name} is FAIL ingested', "error", self.app_name)
                    logger(f'Response: {e.stderr}', "error", self.app_name)
                    return {"status": "error", "message": e.stderr}
                except Exception as e:
                    logger(f'File {file.name} is FAIL ingested', "error", self.app_name)
                    logger(f'Response: {e}', "error", self.app_name)
                    return {"status": "error", "message": e}

            logger(f'Finish ingesting file {file.name} to {pid} in {round(time.perf_counter() - start, 2)} seconds.', settings.LOG_LEVEL, self.app_name)

            if jsonData.get('embargo'):
                json_data = {
                    'dateAvailable': jsonData.get('embargo'),
                    'reason': '',
                    'fileIds': [response_ingest_file['data']['files'][0]['dataFile']['id']],
                }
                response_embargo = requests.post(
                    f'{self.target.base_url}/api/datasets/:persistentId/files/actions/:set-embargo?persistentId={pid}',
                    headers=dmz_dataverse_headers('API_KEY', self.target.password), json=json_data)
                if response_embargo.status_code != status.HTTP_200_OK:
                    return {"status": "error", "message": response_embargo.text}

        return {"status": status.HTTP_200_OK}

    def __publish_dataset(self, pid) -> int:
        return requests.post(
            f"{self.target.base_url}/api/datasets/:persistentId/actions/:publish?persistentId={pid}&type=major",
            headers={"Content-Type": "application/json", "X-Dataverse-key": self.target.password},
        ).status_code
