# Import necessary plugins and packages
# Import necessary libraries and plugins
import hashlib
import json
import logging
import mimetypes
import os
import shutil
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Awaitable, Optional

import httpx
import jmespath
import requests
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.responses import FileResponse

from src.commons import settings, data, db_manager, get_class, assistant_repo_headers, handle_ps_exceptions, \
    send_mail, LOG_NAME_ACP, delete_symlink_and_target
from src.dbz import TargetRepo, DataFile, Dataset, ReleaseVersion, DepositStatus, FilePermissions, \
    DatasetWorkState, DataFileWorkState, MetadataType
from src.models.app_model import ResponseDataModel, InboxDatasetDataModel
# Import custom plugins and classes
from src.models.assistant_datamodel import RepoAssistantDataModel, Target
from src.models.bridge_output_model import TargetsCredentialsModel

# Create an API router instance
router = APIRouter()


# Endpoint to register a bridge plugin
@router.post("/register-bridge-plugin/{name}/{overwrite}")
async def register_plugin(name: str, bridge_file: Request, overwrite: bool | None = False) -> {}:
    """
    Endpoint to register a bridge plugin.

    This endpoint registers a new bridge plugin by saving the provided Python file
    to the specified plugins directory. If the plugin already exists and overwrite
    is not specified, an error is raised.

    Args:
        name (str): The name of the bridge plugin to be registered.
        bridge_file (Request): The request containing the bridge plugin file.
        overwrite (bool, optional): Flag to indicate if the existing plugin should be overwritten. Defaults to False.

    Returns:
        dict: A dictionary containing the status and the name of the registered bridge plugin.

    Raises:
        HTTPException: If the plugin already exists and overwrite is not specified.
        HTTPException: If the content type of the provided file is not 'text/x-python'.
        HTTPException: If the file type of the provided file is not 'text/x-python'.
    """
    logging.error(f'Registering {name}')
    if not overwrite and name in data["bridge-plugins"]:
        raise HTTPException(status_code=400,
                            detail=f'The {name} is already exist. Consider /register-bridge-plugin/{name}/true')

    if bridge_file.headers['Content-Type'] != 'text/x-python':
        raise HTTPException(status_code=400, detail="Unsupported content type")

    m_file = await bridge_file.body()
    bridge_path = os.path.join(settings.PLUGINS_DIR, name)
    with open(bridge_path, "w+") as file:
        file.write(m_file.decode())

    if mimetypes.guess_type(bridge_path)[0] != 'text/x-python':
        os.remove(bridge_path)
        raise HTTPException(status_code=400, detail='Unsupported file type')

    return {"status": "OK", "bridge-plugin-name": name}


# Helper function to process inbox dataset metadata
@handle_ps_exceptions
async def get_inbox_dataset_dc(request: Request, release_version: ReleaseVersion) -> (
        Callable)[[Request, ReleaseVersion], Awaitable[InboxDatasetDataModel]]:
    """
    Process inbox dataset metadata.

    This function processes the metadata of an inbox dataset for the given release version.
    It extracts necessary information from the request headers and body to create an
    InboxDatasetDataModel instance.

    Args:
        request (Request): The request object containing the dataset metadata.
        release_version (ReleaseVersion): The release version of the dataset.

    Returns:
        Callable[[Request, ReleaseVersion], Awaitable[InboxDatasetDataModel]]:
        An awaitable function that returns an InboxDatasetDataModel instance.
    """
    ct = request.headers.get('content-type', MetadataType.JSON)
    if ct == MetadataType.XML:
        # for payload type xml, the title is in the headers
        title = request.headers.get('title', 'no-title')
        req_body = await request.body()
        req_body = req_body.decode('utf-8')
    else:
        req_body = await request.json()
        title = jmespath.search('title', req_body)

    return InboxDatasetDataModel(assistant_name=request.headers.get('assistant-config-name'),
                                 release_version=release_version, owner_id=request.headers.get('user-id'),
                                 metadata_type = MetadataType(ct), title=title,
                                 target_creds=request.headers.get('targets-credentials'), metadata=req_body)


# Endpoint to process inbox dataset metadata
@router.post("/inbox/dataset")
async def process_inbox_dataset_submit(request: Request) -> {}:  # ReleaseVersion
    """
    Endpoint to process and submit inbox dataset metadata.

    This endpoint processes the metadata of an inbox dataset and submitted it.

    Args:
        request (Request): The request object containing the dataset metadata.

    Returns:
        dict: A dictionary representation of the processed dataset metadata.

    Raises:
        HTTPException: If there is an error during the processing of the dataset metadata.
    """
    logging.info(f'Process inbox dataset metadata')
    rdm = await process_inbox(ReleaseVersion.SUBMIT, request)
    return rdm.model_dump(by_alias=True)

@router.post("/inbox/dataset/{release_version}")
async def process_inbox_dataset_metadata(request: Request, release_version: Optional[ReleaseVersion] = None) -> {}:
    """
    Endpoint to process inbox dataset metadata for a specific release version.

    This endpoint processes the metadata of an inbox dataset for the given release version.

    Args:
        request (Request): The request object containing the dataset metadata.
        release_version (Optional[ReleaseVersion]): The release version of the dataset. Defaults to None.

    Returns:
        dict: A dictionary representation of the processed dataset metadata.

    Raises:
        HTTPException: If there is an error during the processing of the dataset metadata.
    """
    logging.info(f'Process inbox dataset metadata for release version: {release_version}')
    rdm = await process_inbox(release_version, request)
    return rdm.model_dump(by_alias=True)


async def process_inbox(release_version, request):
    """
    Process the inbox dataset metadata.

    This function processes the metadata of an inbox dataset for the given release version.
    It validates the dataset, retrieves the repository configuration, processes target repositories,
    metadata records, and database records. It also checks if the dataset is ready for submission.

    Args:
        release_version (ReleaseVersion): The release version of the dataset.
        request (Request): The request object containing the dataset metadata.

    Returns:
        ResponseDataModel: A data model containing the status and dataset ID.

    Raises:
        HTTPException: If the dataset is already submitted.
    """

    idh = await get_inbox_dataset_dc(request, release_version)

    if request.headers.get('dataset_id'):
        dataset_id = request.headers.get('dataset_id')
    elif idh.metadata_type == MetadataType.JSON:
        dataset_id = jmespath.search("id", idh.metadata)
    else:
        dataset_id = uuid.uuid4().hex

    logging.info(f'Start inbox for metadata id: {dataset_id} - release version: {release_version} - assistant name: '
           f'{idh.assistant_name}')
    if db_manager.is_dataset_submitted(dataset_id):
        raise HTTPException(status_code=400, detail='Dataset is already submitted.')

    repo_config = retrieve_targets_configuration(idh.assistant_name)
    repo_assistant = RepoAssistantDataModel.model_validate_json(repo_config)
    dataset_dir = os.path.join(settings.DATA_TMP_BASE_DIR, repo_assistant.app_name,
                               dataset_id.replace(":", "_").replace("/", "-"))
    if not os.path.exists(dataset_dir):
        os.makedirs(dataset_dir)

    db_recs_target_repo = process_target_repos(repo_assistant, idh.target_creds)
    db_record_metadata, registered_files = process_metadata_record(dataset_id, idh, repo_assistant, dataset_dir)
    process_db_records(dataset_id, db_record_metadata, db_recs_target_repo, registered_files)
    if db_manager.is_dataset_ready(dataset_id) and db_manager.are_files_uploaded(dataset_id):
        logging.info(f'SUBMIT DATASET with version {release_version.name} is_dataset_ready {dataset_id}')
        bridge_job(dataset_id, f"/inbox/dataset/{idh.release_version}")
    else:
        logging.info(f'NOT READY to submit dataset with version {release_version.name} dataset_id: {dataset_id} '
               f'\nNumber still registered: {len(db_manager.find_registered_files(dataset_id))}')
    rdm = ResponseDataModel(status="OK")
    rdm.dataset_id = dataset_id
    rdm.start_process = db_manager.is_dataset_ready(dataset_id)
    return rdm


@router.delete("/inbox/dataset/{dataset_id:path}")
def delete_dataset_metadata(request: Request, dataset_id: str):
    """
    Endpoint to delete dataset metadata.

    This endpoint deletes the metadata of a dataset identified by the given metadata ID.
    It checks if the user is authorized and if the dataset can be deleted based on its deposit status.

    Args:
        request (Request): The request object containing headers with user information.
        dataset_id (str): The ID of the dataset metadata to be deleted.

    Returns:
        dict: A dictionary containing the status of the deletion.

    Raises:
        HTTPException: If the user ID is not provided in the request headers.
        HTTPException: If the dataset is not found for the given user ID.
        HTTPException: If the dataset cannot be deleted based on its deposit status.
    """
    logging.info(f'Delete dataset: {dataset_id}')
    user_id = request.headers.get('user-id')
    if not user_id:
        raise HTTPException(status_code=401, detail='No user id provided')
    if dataset_id not in db_manager.find_dataset_ids_by_owner(user_id):
        raise HTTPException(status_code=404, detail='No Dataset found')
    target_repos = db_manager.find_target_repos_by_dataset_id(dataset_id)
    if not target_repos:
        logging.info(f'Delete dataset: {dataset_id}, NOT target_repos')
        return delete_dataset_and_its_folder(dataset_id)
    if target_repos:
        can_be_deleted = False
        for target_repo in target_repos:
            if target_repo.deposit_status not in (DepositStatus.ACCEPTED, DepositStatus.DEPOSITED, DepositStatus.FINISH):
                can_be_deleted = True
                logging.info(f'Delete of {dataset_id} is allowed. Deposit status: {target_repo.deposit_status}')
                break
        if can_be_deleted:
            return delete_dataset_and_its_folder(dataset_id)

    raise HTTPException(status_code=404, detail=f'Delete of {dataset_id} is not allowed.')


def delete_dataset_and_its_folder(dataset_id):
    """
    Delete a dataset and its associated folder.

    This function deletes the dataset identified by the given metadata ID and its associated folder.
    It first checks if the dataset folder exists and deletes it if found. It then deletes the dataset
    record from the database and checks again if the folder exists to ensure it is removed.

    Args:
        dataset_id (str): The ID of the dataset metadata to be deleted.

    Returns:
        dict: A dictionary containing the status of the deletion and the metadata ID.
    """
    dataset_folder = os.path.join(settings.DATA_TMP_BASE_DIR, db_manager.find_app_name(dataset_id),
                                  dataset_id)
    logging.info(f'Delete dataset folder: {dataset_folder}')
    if os.path.exists(dataset_folder):
        delete_symlink_and_target(dataset_folder)
    else:
        logging.info(f'Dataset folder: {dataset_folder} not found')
    db_manager.delete_by_dataset_id(dataset_id)
    if os.path.exists(dataset_folder):
        logging.info(f'Delete dataset folder: {dataset_folder}')
        shutil.rmtree(dataset_folder)
    else:
        logging.info(f'Dataset folder: {dataset_folder} not found')
    return {"status": "ok", "metadata-id": dataset_id}


@handle_ps_exceptions
def process_db_records(datasetId, db_record_metadata, db_recs_target_repo, registered_files) -> type(None):
    """
    Process database records for a dataset.

    This function processes the database records for the given dataset ID by either inserting new records
    or updating existing ones. It handles dataset metadata, target repository records, and registered files.

    Args:
        datasetId (str): The ID of the dataset to process the records for.
        db_record_metadata (Dataset): The dataset metadata record to be processed.
        db_recs_target_repo (list[TargetRepo]): A list of target repository records to be processed.
        registered_files (list[DataFile]): A list of registered files to be processed.

    Returns:
        None
    """
    if not db_manager.is_dataset_exist(datasetId):
        logging.info(f'Insert dataset and target repo records for {datasetId}')
        db_manager.insert_dataset_and_target_repo(db_record_metadata, db_recs_target_repo)
    else:
        logging.info(f'Update dataset and target repo records for {datasetId}')
        db_manager.update_metadata(db_record_metadata)
        db_manager.replace_targets_record(datasetId, db_recs_target_repo)
    if registered_files:
        logging.info(f'Insert datafiles records for {datasetId}')
        logging.info(f'Number registered_files: {len(registered_files)}')
        try:
            db_manager.insert_datafiles(registered_files)
            logging.info(f'SUCCESSFUL  INSERT datafiles records for {datasetId}, number of files: {len(registered_files)}')
        except ValueError as e:
            logging.error(f'Error inserting datafiles: {e}')

@handle_ps_exceptions
def process_metadata_record(dataset_id, idh, repo_assistant, tmp_dir):
    """
    Process the metadata record for a dataset.

    This function processes the metadata record for the given dataset ID by validating and updating file permissions,
    deleting files that are no longer needed, and registering new files. It also updates the dataset state based on
    the presence of new files.

    Args:
        datasetId (str): The ID of the dataset to process the metadata for.
        idh (InboxDatasetDataModel): The data model containing the dataset metadata.
        repo_assistant (RepoAssistantDataModel): The assistant data model containing repository information.
        tmp_dir (str): The temporary directory path where files are stored.

    Returns:
        tuple: A tuple containing the dataset metadata record and a list of registered files.
    """
    logging.info(f'Processing metadata record for {dataset_id}')

    if idh.metadata_type == MetadataType.JSON:
        logging.info(f'Processing json metadata')
        registered_files = []
        file_names = []
        file_names_from_input = jmespath.search('"file-metadata"[*].name', idh.metadata)
        if file_names_from_input:
            for file_name in file_names_from_input:
                data_file = db_manager.find_file_by_name(dataset_id, file_name)
                if data_file:
                    logging.info(f'File {file_name} already exist')
                    escaped_file_name = file_name.replace('"', '\\"')
                    f_permission = jmespath.search(f'"file-metadata"[?name == `{escaped_file_name}`].private', idh.metadata)
                    permission = FilePermissions.PRIVATE if f_permission[0] else FilePermissions.PUBLIC
                    db_manager.update_file_permission(dataset_id, file_name, permission)
                    continue
                else:
                    file_names.append(file_name)
        else:
            file_names_from_input = []

        logging.info(f'Number of file_names: {len(file_names)}')
        already_uploaded_files_name = db_manager.execute_l(dataset_id)
        logging.info(f'Number of already_uploaded_files: {len(already_uploaded_files_name)}')

        files_name_to_be_deleted = set(already_uploaded_files_name) - set(file_names_from_input)
        logging.info(
            f'Number of files_name_to_be_deleted: {len(files_name_to_be_deleted)} --LIST:  {files_name_to_be_deleted}')
        files_name_to_be_added = set(file_names) - set(already_uploaded_files_name)
        logging.info(f'Number of files_name_to_be_added: {len(files_name_to_be_added)}')

        for f_name in files_name_to_be_deleted:
            file_path = os.path.join(tmp_dir, f_name)
            if os.path.exists(file_path):
                delete_symlink_and_target(file_path)
                logging.info(f'{file_path} is deleted')
            else:
                logging.info(f'{file_path} not found')
            db_manager.delete_datafile(dataset_id, f_name)

        for f_name in files_name_to_be_added:
            file_path = os.path.join(tmp_dir, f_name)
            # Escape special characters in the filename
            escaped_filename = f_name.replace('"', '\\"')

            f_permission = jmespath.search(f'"file-metadata"[?name == `{escaped_filename}`].private', idh.metadata)
            permission = FilePermissions.PRIVATE if f_permission[0] else FilePermissions.PUBLIC
            registered_files.append(DataFile(name=f_name, path=file_path, ds_id=dataset_id, permissions=permission))

        logging.info(f'registered_files: {registered_files}')

        # Update file permission
        already_uploaded_files = db_manager.find_uploaded_files(dataset_id)
        logging.info(f'Number of already_uploaded_files: {len(already_uploaded_files)}')

        dataset_state = DatasetWorkState.READY if not files_name_to_be_added else DatasetWorkState.NOT_READY
        metadata = json.dumps(idh.metadata)
    else:
        logging.info(f'Processing xml metadata')
        dataset_state = DatasetWorkState.READY
        metadata = idh.metadata
        registered_files = None

    db_record_metadata = Dataset(id=dataset_id, title=idh.title, owner_id=idh.owner_id,
                                 app_name=repo_assistant.app_name, release_version=idh.release_version,
                                 state=dataset_state, md=metadata, md_type=MetadataType(idh.metadata_type))
    return db_record_metadata, registered_files


@handle_ps_exceptions
def process_target_repos(repo_assistant, target_creds) -> [TargetRepo]:
    """
    Process target repositories for a given assistant.

    This function processes the target repositories for the given assistant by validating
    the target credentials and updating the repository configuration.

    Args:
        repo_assistant (RepoAssistantDataModel): The assistant data model containing target repository information.
        target_creds (str): A JSON string containing the target credentials.

    Returns:
        list[TargetRepo]: A list of TargetRepo objects representing the processed target repositories.

    Raises:
        HTTPException: If a specified bridge plugin class is not found in the data keys.
    """
    db_recs_target_repo = []
    tgc = {"targets-credentials": json.loads(target_creds)}
    input_target_cred_model = TargetsCredentialsModel.model_validate(tgc)
    for repo_target in repo_assistant.targets:
        if repo_target.bridge_plugin_name not in data.keys():
            raise HTTPException(status_code=404, detail=f'Module "{repo_target.bridge_plugin_name}" not found.',
                                headers={})
        target_repo_name = repo_target.repo_name
        logging.info(f'target_repo_name: {target_repo_name}')
        for depositor_cred in input_target_cred_model.targets_credentials:
            if (depositor_cred.target_repo_name == repo_target.repo_name and depositor_cred.credentials and
                    depositor_cred.credentials.username):
                repo_target.username = depositor_cred.credentials.username
            if (depositor_cred.target_repo_name == repo_target.repo_name and depositor_cred.credentials and
                    depositor_cred.credentials.password):
                repo_target.password = depositor_cred.credentials.password

        db_recs_target_repo.append(TargetRepo(name=repo_target.repo_name, url=repo_target.target_url,
                                              display_name=repo_target.repo_display_name,
                                              config=repo_target.model_dump_json(by_alias=True, exclude_none=True)))
    return db_recs_target_repo


def count_files_in_directory(directory: str) -> int:
    """
    Count the number of files in a directory.

    This function lists all items in the specified directory, filters the list to include only files,
    and returns the count of files.

    Args:
        directory (str): The path of the directory to count files in.

    Returns:
        int: The number of files in the directory.

    Raises:
        FileNotFoundError: If the specified directory does not exist.
        Exception: If any other error occurs during the process.
    """
    try:
        # List all items in the directory
        items = os.listdir(directory)
        # Filter the list to include only files
        files = [item for item in items if os.path.isfile(os.path.join(directory, item))]
        # Return the count of files
        return len(files)
    except FileNotFoundError:
        print(f"The directory {directory} does not exist.")
        return 0
    except Exception as e:
        print(f"An error occurred: {e}")
        return 0


def list_files_with_suffix(directory: str, suffix: str) -> list:
    """
    List all files in the given directory that end with the specified suffix.

    Parameters:
    directory (str): The directory to search in.
    suffix (str): The suffix to filter files by.

    Returns:
    list: A list of file names that end with the given suffix.
    """
    return [file for file in os.listdir(directory) if
            os.path.isfile(os.path.join(directory, file)) and file.endswith(suffix)]


async def delete_file(file_id: str):
    logging.info(f"Deleting file {file_id}")
    url = f'{settings.TUS_BASE_URL}/files/{file_id}'
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {settings.dans_packaging_service_api_key}"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(url, headers=headers, timeout=10)
            if response.status_code == 204:
                logging.info(f"TUS File  successfully deleted. {file_id}")
            else:
                logging.info(f"File id: {file_id} Failed to delete file. Status code: {response.status_code}")

            return response.status_code
        except Exception as e:
            logging.error(f"File id: {file_id} Error deleting file: {e}")

        return 500


@router.patch("/inbox/files/{metadata_id}/{file_uuid}")
async def update_file_metadata(metadata_id: str, file_uuid: str) -> {}:
    """
    Endpoint to update file metadata.

    This endpoint updates the metadata of a file identified by the given metadata ID and file UUID.
    It processes the file, creates a symlink, and updates the database with the new file information.

    Args:
        metadata_id (str): The ID of the dataset metadata.
        file_uuid (str): The UUID of the file.

    Returns:
        dict: A dictionary containing the status and the dataset ID.

    Raises:
        HTTPException: If the file info or file is not found.
        HTTPException: If the file size is 0.
        HTTPException: If there is a file size mismatch.
    """
    logging.info(f'PATCH file metadata for metadata_id: {metadata_id} and file_uuid: {file_uuid}' )
    tus_file = os.path.join(settings.DATA_TMP_BASE_TUS_FILES_DIR, file_uuid)
    file_info_path = f'{tus_file}.info'
    if not os.path.exists(file_info_path):
        logging.error(f'File info NOT FOUND for {file_uuid}: {file_info_path}')
        raise HTTPException(status_code=404, detail='File not found')
    if not os.path.exists(tus_file):
        logging.error(f'File NOT FOUND for {file_uuid}: {tus_file}')
        raise HTTPException(status_code=404, detail='File not found')
    if os.path.getsize(tus_file) == 0:
        logging.error(f'File SIZE IS 0 for {file_uuid}: {tus_file}')
        raise HTTPException(status_code=400, detail='File size is 0')

    with open(file_info_path, "r") as file:
        file_metadata = json.load(file)
    file_name = file_metadata['metadata']['fileName']
    if file_metadata.get('size', 0) == 0:
        logging.error(f'File SIZE IS 0 for {file_uuid}: {tus_file}')
        raise HTTPException(status_code=400, detail='File size is 0')

    logging.info(f'file_name: {file_name}')
    if os.path.getsize(tus_file) != file_metadata.get('size', 0):
        logging.error(f'FILE SIZE MISMATCH for {file_uuid}: {tus_file}')
        raise HTTPException(status_code=400, detail='File size mismatch')

    db_record_metadata = db_manager.find_dataset(metadata_id)
    dataset_folder = os.path.join(settings.DATA_TMP_BASE_DIR, db_record_metadata.app_name, metadata_id)
    source_file_path = os.path.join(settings.DATA_TMP_BASE_TUS_FILES_DIR, file_uuid)
    dest_file_path = os.path.join(dataset_folder, file_name)
    # Process the files
    logging.info(f'Processing using symlink {source_file_path} to {dest_file_path}')
    target = source_file_path
    link_name = dest_file_path
    try:
        md5_hash = ""
        if settings.get("use_md5_hash", False):
            with open(source_file_path, 'rb') as file:
                md5_hash = hashlib.md5(file.read()).hexdigest()
            # with open(source_file_path, "rb") as f:
            #     file_hash = hashlib.md5()
            #     while chunk := f.read(8192):
            #         file_hash.update(chunk)
            # md5_hash = file_hash.hexdigest()

        file_type = file_metadata['metadata'].get('filetype', mimetypes.guess_type(dest_file_path)[0])
        db_manager.update_file(DataFile(ds_id=metadata_id, name=file_name, checksum_value=md5_hash,
                                        size=os.path.getsize(source_file_path), mime_type=file_type,
                                        path=dest_file_path, date_added=datetime.utcnow(),
                                        state=DataFileWorkState.UPLOADED))
        new_name = f'{target}-{metadata_id}.{db_record_metadata.app_name}'
        os.rename(target, new_name)
        os.symlink(new_name, link_name)
        logging.info(f'Symlink created: {link_name} -> {target}')
        logging.info(f'Deleting {source_file_path}.info')
        deleted_status = await delete_file(file_uuid)
        logging.info(f'Deleted status: {deleted_status}')
    except FileExistsError:
        logging.error(f'The symlink {link_name} already exists.')
    except FileNotFoundError:
        logging.error(f'The target {target} does not exist.')
    except OSError as e:
        logging.error(f'Error creating symlink: {e}')
    all_files_uploaded = len(db_manager.find_registered_files(metadata_id)) == 0
    if all_files_uploaded:
        logging.info(f'All files are UPLOADED for {metadata_id}')
        db_manager.set_dataset_ready_for_ingest(metadata_id)
    else:
        db_manager.set_dataset_ready_for_ingest(metadata_id, DatasetWorkState.NOT_READY)
        logging.info(f'Not all files uploaded for {metadata_id}')

    start_process = db_manager.is_dataset_ready(metadata_id)
    if start_process:
        logging.info(f'Start Bridge task for {metadata_id} from the PATCH file endpoint')
        bridge_job(metadata_id, f'/inbox/files/{metadata_id}/{file_uuid}')
        logging.info(f'Bridge task for {metadata_id} started successfully')
    else:
        logging.info(f'Bridge task for {metadata_id} NOT started')

    registerd_files = db_manager.find_registered_files(metadata_id)
    logging.info(f'Number of registered files: {len(registerd_files)}')
    rdm = ResponseDataModel(status="OK")
    rdm.dataset_id = metadata_id
    rdm.start_process = start_process
    return rdm.model_dump(by_alias=True)


def bridge_job(datasetId: str, msg: str) -> None:
    """
    Start a new thread to follow the bridge process for a dataset.

    This function starts a new thread to execute the `follow_bridge` function for the given dataset ID.
    It logs the start of the threading process and handles any exceptions that occur.

    Args:
        datasetId (str): The ID of the dataset to follow the bridge process for.
        msg (str): A message to log when starting the threading process.

    Returns:
        None
    """
    logging.info(f"Starting threading for {msg} with datasetId: {datasetId}")
    try:
        threading.Thread(target=follow_bridge, args=(datasetId,)).start()
        logging.info(f"Threading for {datasetId} started successfully.")
    except Exception as e:
        logging.error(f"Error starting thread for {datasetId}: {e}")


def follow_bridge(dataset_id) -> type(None):
    """
    Follow the bridge process for a dataset.

    This function logs the start time of the thread, marks the dataset as submitted,
    retrieves the target repositories associated with the dataset, and executes the bridge process.

    Args:
        dataset_id (str): The ID of the dataset to follow the bridge process for.

    Returns:
        None
    """
    # Log the start time of the thread
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"Thread for datasetId: {dataset_id} started at {start_time}")

    logging.info("Follow bridge")
    logging.info(f">>> EXECUTE follow_bridge for datasetId: {dataset_id}")
    db_manager.submitted_now(dataset_id)
    target_repo_recs = db_manager.find_target_repos_by_dataset_id(dataset_id)
    execute_bridges(dataset_id, target_repo_recs)


def execute_bridges(datasetId, targets) -> None:
    """
    Execute the bridge process for a dataset.

    This function iterates over the target repositories associated with the dataset,
    executes the bridge process for each target, and handles the results.

    Args:
        datasetId (str): The ID of the dataset to execute the bridge process for.
        targets (list): A list of target repositories to process.

    Returns:
        None
    """
    logging.info("execute_bridges")
    results = []
    for target_repo_rec in targets:
        bridge_class = data[Target(**json.loads(target_repo_rec.config)).bridge_plugin_name]
        logging.info(f'EXECUTING {bridge_class} for target_repo_id: {target_repo_rec.id}')

        start = time.perf_counter()
        bridge_instance = get_class(bridge_class)(dataset_id=datasetId,
                                                  target=Target(**json.loads(target_repo_rec.config)))
        deposit_result = bridge_instance.job()
        deposit_result.response.duration = round(time.perf_counter() - start, 2)

        logging.info(f'Result from Deposit: {deposit_result.model_dump_json()}')
        bridge_instance.save_state(deposit_result)

        if deposit_result.deposit_status in [DepositStatus.FINISH, DepositStatus.ACCEPTED, DepositStatus.SUCCESS]:
            results.append(deposit_result)
        else:
            send_mail(f'Executing {bridge_class} is FAILED.', f'Resp:\n {deposit_result.model_dump_json()}')
            break

    if len(results) == len(targets):
        dataset_folder = os.path.join(settings.DATA_TMP_BASE_DIR, db_manager.find_dataset(ds_id=datasetId).app_name,
                                      datasetId)
        logging.info(f'Ingest SUCCESSFULL, DELETE {dataset_folder}')

        for file in Path(dataset_folder).glob('*'):
            if file.is_file():
                delete_symlink_and_target(file)
        if os.path.exists(dataset_folder):
            shutil.rmtree(dataset_folder)
        logging.info(f'DELETED successfully: {dataset_folder}')
    else:
        logging.info(f'Ingest FAILED for datasetId: {datasetId}')


@handle_ps_exceptions
def retrieve_targets_configuration(assistant_config_name: str) -> str:
    """
    Retrieve the configuration for the specified assistant.

    This function retrieves the configuration for the given assistant by making a request
    to the assistant configuration URL.

    Args:
        assistant_config_name (str): The name of the assistant configuration to retrieve.

    Returns:
        str: The JSON response containing the assistant configuration.

    Raises:
        HTTPException: If the configuration URL returns a status code other than 200.
    """
    repo_url = f'{settings.ASSISTANT_CONFIG_URL}/{assistant_config_name}'
    logging.info(f'Retrieve targets configuration from {repo_url}')
    rsp = requests.get(repo_url, headers=assistant_repo_headers)
    if rsp.status_code != 200:
        raise HTTPException(status_code=404, detail=f"{repo_url} not found")
    return rsp.json()


@router.post("/inbox/resubmit/{datasetId}")
async def resubmit(datasetId: str):
    """
    Endpoint to resubmit a dataset.

    This endpoint resubmits a dataset identified by the given dataset ID. It finds unfinished target repositories
    associated with the dataset and attempts to resubmit them.

    Args:
        datasetId (str): The ID of the dataset to be resubmitted.

    Returns:
        str: A message indicating whether there are targets to resubmit or not.

    Raises:
        Exception: If there is an error starting the resubmission thread.
    """
    logging.info(f'Resubmit {datasetId}')
    targets = db_manager.find_unfinished_target_repo(datasetId)
    if not targets:
        return 'No targets'

    logging.info(f'Resubmitting {len(targets)}')
    try:
        execute_bridges_task = threading.Thread(target=execute_bridges, args=(datasetId, targets,))
        execute_bridges_task.start()
        logging.info(f'follow_bridge_task {execute_bridges_task} started')
    except Exception as e:
        logging.error(f"ERROR: Follow bridge: {targets}. For datasetId: {datasetId}. Exception: "
               f"{e.with_traceback(e.__traceback__)}")


#
@router.delete("/inbox/{datasetId}", include_in_schema=False)
def delete_inbox(datasetId: str):
    """
    Endpoint to delete an inbox dataset.

    This endpoint deletes the dataset identified by the given dataset ID from the database.

    Args:
        datasetId (str): The ID of the dataset to be deleted.

    Returns:
        dict: A dictionary containing the status of the deletion and the number of rows deleted.
    """
    num_rows_deleted = db_manager.delete_by_dataset_id(datasetId)
    return {"Deleted": "OK", "num-row-deleted": num_rows_deleted}


def remove_files_and_directories(dir_path):
    """
    Remove all files and directories within the specified directory.

    This function iterates through all items in the given directory path and removes them.
    It logs the removal of each file and directory.

    Args:
        dir_path (str): The path of the directory to be cleaned.
    """
    for item in os.listdir(dir_path):
        item_path = os.path.join(dir_path, item)
        if os.path.isfile(item_path):
            os.remove(item_path)
            logging.info(f"File {item_path} has been removed")
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)
            logging.info(f"Directory {item_path} and all its contents have been removed")


@router.delete("/delete-dir/{dir}", include_in_schema=False)
def delete_inbox(dir: str):
    """
    Endpoint to delete a directory.

    This endpoint deletes the specified directory and all its contents.

    Args:
        dir (str): The name of the directory to be deleted.

    Returns:
        dict: A dictionary containing the status of the deletion and the name of the deleted directory.

    Raises:
        HTTPException: If the specified directory is not found.
    """
    directory = f"{settings.DATA_TMP_BASE_DIR}/{dir}"
    if not os.path.exists(directory):
        return HTTPException(status_code=404, detail=f"{directory} not found")
    logging.info(f'Delete directory: {directory}')
    remove_files_and_directories(directory)
    return {"Deleted": "OK", "directory": directory}


# Endpoint to retrieve application settings
@router.get("/settings-reload", include_in_schema=False)
async def get_settings():
    """
    Endpoint to retrieve and reload application settings.

    This endpoint retrieves the current application settings, reloads them, and returns the updated settings.

    Returns:
        dict: A dictionary containing the updated application settings.
    """
    logging.info(f"Getting settings Before Load: {settings.as_dict()}")
    logging.info("Reload settings")
    settings.reload()
    logging.info(f"Getting settings After Load: {settings.as_dict()}")
    return settings.as_dict()

@router.get("/dataset/{datasetId}/md", include_in_schema=False)
def get_md(datasetId: str):
    """
    Endpoint to retrieve the metadata of a dataset.

    This endpoint retrieves the metadata of the dataset identified by the given dataset ID.

    Args:
        datasetId (str): The ID of the dataset to retrieve the metadata for.

    Returns:
        dict: A dictionary containing the metadata of the dataset.

    Raises:
        HTTPException: If the dataset is not found.
    """
    dataset = db_manager.get_decrypted_md(datasetId)
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset {datasetId} not found")
    return json.loads(dataset.md)


@router.get('/logs/{app_name}', include_in_schema=False)
def get_log(app_name: str):
    """
    Endpoint to retrieve a specific log file.

    This endpoint returns the log file for the specified application name.

    Args:
        app_name (str): The name of the application whose log file is to be retrieved.

    Returns:
        FileResponse: A response object that allows the client to download the log file.

    Logs:
        Logs the action of retrieving the log file.
    """
    logging.info('logs')
    return FileResponse(path=f"{os.environ['BASE_DIR']}/logs/{app_name}.log", filename=f"{app_name}.log",
                        media_type='text/plain')


@router.get("/logs-list", include_in_schema=False)
def get_log_list():
    """
    Endpoint to retrieve the list of log files.

    This endpoint returns a list of log files present in the logs directory.

    Returns:
        list: A list of log file names.

    Raises:
        FileNotFoundError: If the logs directory does not exist.
    """
    logging.info('logs-list')
    return os.listdir(path=f"{os.environ['BASE_DIR']}/logs")


@router.get("/db-download", include_in_schema=False)
def get_db():
    """
    Endpoint to download the database file.

    This endpoint returns the database file as a downloadable response.

    Returns:
        FileResponse: A response object that allows the client to download the database file.

    Logs:
        Logs the action of downloading the database file.
    """
    logging.info('db-download')
    return FileResponse(path=settings.DB_URL, filename="acp.db",
                        media_type='application/octet-stream')


@router.delete("/db-delete-all", include_in_schema=False)
def delete_all_recs():
    """
    Endpoint to delete all records from the database.

    This endpoint deletes all records from the database by calling the `delete_all` method
    of the `db_manager` object.

    Returns:
        dict: A dictionary containing the status of the deletion.

    Logs:
        Logs the action of deleting all records.
    """
    logging.info('Deleting all')
    return db_manager.delete_all()

@router.get("/datasets", include_in_schema=False)
async def get_db():
    """
    Endpoint to retrieve datasets.

    This endpoint retrieves datasets from the database by executing a raw SQL query.

    Returns:
        JSONResponse: A JSON response containing the datasets retrieved from the database.
    """
    logging.info("Finding datasets")
    return JSONResponse(content=db_manager.execute_raw_sql())