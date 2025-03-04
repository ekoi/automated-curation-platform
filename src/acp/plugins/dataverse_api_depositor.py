import json
import logging
import mimetypes
import os
import re
import subprocess
import time
import uuid
from datetime import datetime, timezone

import jmespath
import requests
from simple_file_checksum import get_checksum
from starlette import status

from src.acp.bridge import Bridge, TargetDataModel
from src.acp.commons import (
    settings,
    db_manager,
    transform,
    handle_deposit_exceptions, dmz_dataverse_headers, zip_a_zipfile_with_progress, transform_xml,
    processed_metadata_handler,
)
from src.acp.dbz import ReleaseVersion, DataFile, DepositStatus, FilePermissions, DataFileWorkState, MetadataType
from src.acp.models.bridge_output_model import IdentifierItem, IdentifierProtocol, TargetResponse, ResponseContentType


class DataverseIngester(Bridge):
    """
    Class for ingesting metadata and files into Dataverse.
    The following is an example of the configuration for the Dataverse ingester in Repository Assistant:
    "dataset-metadata.json" is the default name for the dataverse metadata. It corresponds to the repoassistant configuration.
    "transformed-metadata": [
                        {
                           "name": "dataset-metadata.json",
                            "transformer-url": "http://localhost:1745/transform/ohsmart-form-metadata-to-DV-metadata-v4.xsl",
                            "target-dir": "metadata"
                        }

    "dataset-metadata.json" is the default name for the dataverse metadata. It corresponds to the repoassistant configuration.
    "transformed-metadata": [
                         {
                             "name": "dataset-files.json",
                          "transformer-url": "http://localhost:1745/transform/ohsmart-form-metadata-to-DV-metadata-v4.xsl",
                             "target-dir": "metadata"
                        }
    Methods:
        execute(): Executes the ingestion process and returns the result as a BridgeOutputDataModel.
    """

    @handle_deposit_exceptions
    def job(self) -> TargetDataModel:
        """
        Executes the ingestion process.

        Returns:
            TargetDataModel: The result of the ingestion process.
        """
        target_repo = TargetResponse(url=self.target.target_url)
        tdm = TargetDataModel(response=target_repo)

        if self.metadata_rec.md_type == MetadataType.JSON:
            md_json = json.loads(self.metadata_rec.md)

            if self.target.input:
                input_from_prev_target = db_manager.find_target_repo(self.dataset_id, self.target.input.from_target_name)
                md_json[self.target.input.from_target_name] = json.loads(input_from_prev_target.target_output)['response']['identifiers'][0]['value']
                db_manager.update_dataset_md(self.dataset_id, json.dumps(md_json))

            if self.target.metadata:
                files_metadata = jmespath.search('"file-metadata"[*]', md_json)
                if self.target.metadata.transformed_metadata:
                    # When transformed metadata is available, transform the metadata
                    # Add generated files to the metadata
                    generated_files = self.__create_generated_files()
                    for gf in generated_files:
                        files_metadata.append({"name": gf.name, "mimetype": gf.mime_type, "private": gf.permissions == FilePermissions.PRIVATE})
                    if generated_files:
                        db_manager.insert_datafiles(generated_files)

                    if files_metadata:
                        md_json["file-metadata"] = files_metadata

                if self.target.metadata.processed_metadata:
                    # When processed metadata is available, process the metadata
                    md_json = processed_metadata_handler(self.target.metadata.processed_metadata, md_json)
                    # for pm in self.target.metadata.processed_metadata:
                    #     pm.dir = f'{self.dataset_dir}/{pm.dir}' if pm.dir else self.dataset_dir
                    #     processed_metadata_handler(pm, md_json)

                for file in db_manager.find_non_generated_files(dataset_id=self.dataset_id):
                    escaped_file_name = file.name.replace('"', '\\"')
                    f_json = jmespath.search(f'[?name == `{escaped_file_name}`]', files_metadata)
                    f_json[0]["mimetype"] = file.mime_type

            str_updated_metadata = json.dumps(md_json)
        else:
            str_updated_metadata = self.metadata_rec.md

        logging.info(f"str_updated_metadata_json: {str_updated_metadata}")

        # The metadata will be transformed if name is "dataset-metadata.json" and the transformed metadata is available.
        try:
            str_dv_metadata = self.__transform_metadata_to_dataverse_json(str_updated_metadata,
                                                                          settings.get("DV_METADATA", "dataset-metadata.json"), self.metadata_rec.md_type)
        except ValueError as e:
            tdm.deposited_metadata = str(e)
            tdm.deposit_status = DepositStatus.ERROR
            return tdm
        if self.metadata_rec.md_type == MetadataType.JSON:
            tdm.payload = json.loads(str_dv_metadata)
            # TOOD tdm.payload for other than json metadata

        logging.info(f'deposit to "{self.target.target_url}"')
        # If the target URL has parameters, replace the placeholder with the dataset PID. It corresponds to the repoassistant configuration.
        # "target-url-params": "pid=$PID&release=no",
        if self.target.target_url_params:
            self.target.target_url += "?" + self.target.target_url_params.replace("$PID", md_json["datasetVersion"]["datasetPersistentId"])

        dv_response = requests.post(self.target.target_url, headers=dmz_dataverse_headers('API_KEY', self.target.password), data=str_dv_metadata)
        logging.info(f"dv_response.status_code: {dv_response.status_code} dv_response.text: {dv_response.text}")

        identifier_items = []
        logging.info(f'Ingesting metadata {self.dataset_id} to {self.target.target_url}')

        if dv_response.status_code == 201:
            dv_response_json = dv_response.json()
            logging.info(f"Data ingest successfully! {json.dumps(dv_response_json)}")
            pid = dv_response_json["data"]["persistentId"]
            self.__set_repo_identifiers(identifier_items, pid, target_repo)

            if self.target.metadata and self.target.metadata.transformed_metadata:
                try:
                    if self.metadata_rec.md_type == MetadataType.JSON:
                        self.__ingest_files(pid, str_updated_metadata)
                    tdm.deposit_status = DepositStatus.FINISH
                    tdm.deposited_metadata = "The dataset and its file is successfully ingested"
                    logging.info(f'Ingest FILE(s) successfully!')
                    target_repo.status_code = status.HTTP_200_OK
                    if self.target.initial_release_version == ReleaseVersion.PUBLISHED:
                        logging.info(f'Publish the dataset')
                        target_repo.status_code = self.__publish_dataset(pid)
                        tdm.deposited_metadata = "The dataset and its files successfully published" if target_repo.status_code == status.HTTP_200_OK else "The dataset is unsuccessfully published"
                except ValueError as e:
                    tdm.deposit_status = DepositStatus.ERROR
                    tdm.deposited_metadata = str(e)
                    tdm.deposited_metadata = "The dataset and its file is unsuccessfully ingested"
                    #Rollback: Delete the dataset
                    dv_id = dv_response_json["data"]["id"]
                    delete_response = requests.delete(f"{self.target.base_url}/api/datasets/{dv_id}/versions/:draft", headers=dmz_dataverse_headers('API_KEY', self.target.password))
                    logging.info(f"delete_response.status_code: {delete_response.status_code} delete_response.text: {delete_response.text}")
                    return tdm

            tdm.deposit_status = DepositStatus.FINISH


        else:
            logging.error(f"Ingest failed with status code {dv_response.status_code}:")
            logging.error(f'Response:  {dv_response.text}')
            logging.error(f"Ingest metadata - str_dv_metadata {str_dv_metadata}")
            tdm.deposit_status = DepositStatus.ERROR
            tdm.deposited_metadata = str_dv_metadata
            return tdm


        current_time = datetime.now(timezone.utc).isoformat()
        tdm.deposit_time = current_time
        target_repo.content = dv_response.json()
        target_repo.content_type = ResponseContentType.JSON
        target_repo.status_code = dv_response.status_code

        dv_resp_deposited = requests.get(f'{self.target.base_url}/api/datasets/:persistentId/?persistentId={pid}',
                                   headers=dmz_dataverse_headers('API_KEY', self.target.password), data=str_dv_metadata)
        if dv_resp_deposited.status_code == 200:
            tdm.deposited_metadata = dv_resp_deposited.json()
        else:
            logging.info(f"Error: {dv_resp_deposited.text} status code: {dv_resp_deposited.status_code}")
            pass #TODO: Handle this case

        tdm.response = target_repo
        return tdm

    def __set_repo_identifiers(self, identifier_items, pid, target_repo):
        identifier_items.append(
            IdentifierItem(value=pid, url=f'{self.target.base_url}/dataset.xhtml?persistentId={pid}',
                           protocol=IdentifierProtocol('doi')))
        logging.info(f"pid: {pid}")
        target_repo.identifiers = identifier_items

    # When the transformation is done successfully, the transformed metadata is returned otherwise an error message is returned.
    def __transform_metadata_to_dataverse_json(self, str_updated_metadata_json, json_data_name: str, md_type: MetadataType = MetadataType.JSON) -> str:
        if self.target.metadata and self.target.metadata.transformed_metadata:
            transformer = [metadata for metadata in self.target.metadata.transformed_metadata if
                           metadata.name == json_data_name]
            if not transformer or len(transformer) != 1:
                logging.info(f"Error: Transformer not found or more than one transformer")
                #Skip transformation
                return str_updated_metadata_json
                # raise ValueError(f"Error: Transformer '{json_data_name}' not found or more than one transformer")
            if md_type == MetadataType.XML:
                str_dv_metadata = transform_xml(
                    transformer_url=transformer[0].transformer_url,
                    str_tobe_transformed=str_updated_metadata_json
                )
            elif md_type == MetadataType.JSON:
                str_dv_metadata = transform(
                    transformer_url=transformer[0].transformer_url,
                    str_tobe_transformed=str_updated_metadata_json
                )

                logging.info(f"TRANSFORMED str_dv_metadata: {str_updated_metadata_json}")

                str_dv_metadata = self.__validate_json(str_dv_metadata)
                if not str_dv_metadata:
                    logging.info(f"Error: Not valid json: {str_dv_metadata}")
                    raise ValueError("Error: Not valid json")
            else:
                str_dv_metadata = str_updated_metadata_json
        else:
            str_dv_metadata = str_updated_metadata_json

        return str_dv_metadata

    def __validate_json(self, str_dv_metadata):
        try:
            json.loads(str_dv_metadata)
        except json.JSONDecodeError as e:
            logging.error(f"Error: {e}")
            str_dv_metadata = re.sub(r'[\x00-\x1F\x7F]', '', str_dv_metadata)
            try:
                json.loads(str_dv_metadata)
            except json.JSONDecodeError as e:
                logging.error(f"Error: {e}")
                return None
            except Exception as e:
                logging.error(f"Error: {e}")
                return None
        except Exception as e:
            logging.error(f"Error: {e}")
            return None
        return str_dv_metadata

    def __create_generated_files(self) -> [DataFile]:
        generated_files = []
        for tm in self.target.metadata.transformed_metadata:
            if tm.generate_file:
                gf_path = os.path.join(self.dataset_dir, tm.name)
                content = transform(tm.transformer_url,
                                    self.metadata_rec.md) if tm.transformer_url else self.metadata_rec.md
                with open(gf_path, "wt") as f:
                    f.write(content)
                gf_mimetype = mimetypes.guess_type(gf_path)[0]
                permissions = FilePermissions.PRIVATE if tm.restricted else FilePermissions.PUBLIC
                generated_files.append(DataFile(
                    ds_id=self.dataset_id, name=tm.name, path=gf_path,
                    size=os.path.getsize(gf_path), mime_type=gf_mimetype,
                    checksum_value=get_checksum(gf_path, algorithm="MD5"),
                    date_added=datetime.utcnow(), permissions=permissions,
                    state=DataFileWorkState.GENERATED))
        return generated_files

    def __ingest_files(self, pid: str, str_updated_metadata_json: str) -> int:
        logging.info(f'Ingesting files to {pid}')

        str_dv_file = self.__transform_metadata_to_dataverse_json(str_updated_metadata_json, settings.get("DV_FILES", "dataset-files.json"))

        for file in db_manager.find_non_generated_files(dataset_id=self.dataset_id):
            logging.info(f'Ingesting file {file.name}. Size: {file.size} Path: {file.path}')
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
                logging.info(f'Start zipping file {file.name}. Real path: {zip_file_name}')
                zip_a_zipfile_with_progress(zip_file_name, file.path)
                os.remove(zip_file_name)
                logging.info(f'Finished zipping file {file.name} to {real_file_path} in {round(time.perf_counter() - start, 2)} seconds')

            url_base = f"{self.target.base_url}/api/datasets/:persistentId/add?persistentId={pid}"
            headers = dmz_dataverse_headers('API_KEY', self.target.password)
            timeout_seconds = settings.get("DATAVERSE_RESPONSE_TIMEOUT", 360000)
            logging.info(f'Start ingesting file {file.name}. Size: {file.size}. Ingest to {url_base}')
            if file.size < settings.get("MAX_INGEST_SIZE_USING_PYTHON", 100000000):
                logging.info(f'Ingest SMALL FILE using python: {file.name}')
                with open(file.path, 'rb') as f:
                    files = {'file': (file.name, f)}
                    response_ingest_file = requests.post(url_base, files=files, data=data, headers=headers, timeout=timeout_seconds).json()
                    logging.info(f'File {file.name} is successfully ingested')
            else:
                logging.info(f'Ingest LARGE FILE using script: {file.name}')
                logging.info("")
                jsonData_str = json.dumps(jsonData)
                try:
                    output = f'{settings.DATA_TMP_BASE_DIR}/{self.app_name}/{self.dataset_id}/{str(uuid.uuid4().int)}.txt'
                    logging.info(f'Output: {output}')
                    result = subprocess.run(
                        [settings.SHELL_SCRIPT_PATH, file.path, url_base, jsonData_str, self.target.password, output],
                        check=True, text=True, capture_output=True
                    )
                    logging.info(f'File {file.name} is successfully ingested')
                    logging.info(f'Response: {result.stdout}')
                    response_ingest_file = json.loads(result.stdout)
                except subprocess.CalledProcessError as e:
                    logging.error(f'File {file.name} is FAIL ingested')
                    logging.error(f'Response: {e.stderr}')
                    raise ValueError(str(e.stderr))
                except Exception as e:
                    logging.error(f'File {file.name} is FAIL ingested')
                    logging.error(f'Response: {e}')
                    raise ValueError(str(e))

            logging.info(f'Finish ingesting file {file.name} to {pid} in {round(time.perf_counter() - start, 2)} seconds.')

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
                    raise ValueError(response_embargo.text)

    def __publish_dataset(self, pid) -> int:
        return requests.post(
            f"{self.target.base_url}/api/datasets/:persistentId/actions/:publish?persistentId={pid}&type=major",
            headers={"Content-Type": "application/json", "X-Dataverse-key": self.target.password},
        ).status_code
