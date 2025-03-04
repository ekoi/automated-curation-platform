import json
import logging

from fastapi import APIRouter, Request, HTTPException
from starlette.responses import Response

# from src import db
from src.acp.commons import data, db_manager, settings, fetch_dv_json
from src.acp.dbz import ReleaseVersion
from src.acp.models.app_model import OwnerAssetsModel, Asset, TargetApp

router = APIRouter()


@router.get("/available-plugins")
async def get_plugins_list():
    """
    Endpoint to retrieve a list of available plugins.

    This endpoint returns a sorted list of keys from the `data` dictionary,
    which represents the available plugins in the system.

    Returns:
        list: A sorted list of available plugin names.
    """
    return sorted(list(data.keys()))

@router.get("/progress-state/{owner_id}")
async def progress_state(owner_id: str, req: Request):
    """
    Endpoint to retrieve the progress state of assets owned by a specific owner.

    Args:
        req: Request: The incoming request object.
        owner_id (str): The ID of the owner whose assets' progress state is to be retrieved.

    Returns:
        list: A list of rows representing the progress state of the owner's assets.
              If no assets are found, an empty list is returned.
    """
    tc_header = req.headers.get('targets-credentials')
    if tc_header is None:
        raise HTTPException(status_code=400, detail="Targets credentials are missing")

    try:
        target_creds = json.loads(tc_header)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid json format of targets-credentials")

    datasets = db_manager.find_datasets_by_owner(owner_id)
    if datasets:
        oam = OwnerAssetsModel()
        oam.owner_id = owner_id
        for dataset in datasets:
            asset = Asset()
            asset.dataset_id = str(dataset.id)
            asset.release_version = dataset.release_version.name
            asset.title = dataset.title
            asset.created_date = dataset.created_date.strftime('%Y-%m-%d %H:%M:%S')
            asset.saved_date = dataset.saved_date.strftime('%Y-%m-%d %H:%M:%S')
            asset.submitted_date = dataset.submitted_date.strftime(
                '%Y-%m-%d %H:%M:%S') if dataset.submitted_date else ''
            asset.release_version = dataset.release_version.name
            asset.version = dataset.version if dataset.version else ''
            targets_repo = db_manager.find_target_repos_by_dataset_id(str(dataset.id))
            logging.info(f'dataset release version: {dataset.release_version}')
            print(dataset.release_version)
            if dataset.release_version is not ReleaseVersion.DRAFT:
                for target_repo in targets_repo:
                    target = TargetApp()
                    target.repo_name = target_repo.name
                    target.display_name = target_repo.display_name
                    target.deposit_status = target_repo.deposit_status
                    target.deposit_time = target_repo.deposit_time.strftime(
                        '%Y-%m-%d %H:%M:%S') if target_repo.deposit_time else ''
                    target.duration = str(target_repo.duration)
                    rsp = json.loads(target_repo.target_output) if target_repo.target_output else {}
                    if rsp:
                        idents =  rsp['response']['identifiers']
                        target.output_response = {"response": {"identifiers": idents}}
                        if idents:
                            url = rsp['response']['identifiers'][0]['url']
                            # Dataverse only. TODO: Think more generic solution
                            if url.find("dataset.xhtml") > 0:
                                logging.info(f'fetching diff for {target.repo_name}')
                                target.diff = await fetch_dv_json(rsp, target, target_creds, url)
                        else:
                            target.output_response = {}
                    else:
                        target.output_response = {}

                    asset.targets.append(target)
            oam.assets.append(asset)
        return oam
    return []


@router.get("/dataset/{datasetId}")
async def find_dataset(datasetId: str):
    """
    Endpoint to retrieve a dataset and its associated targets by dataset ID.

    Args:
        datasetId (str): The ID of the dataset to be retrieved.

    Returns:
        Response: A JSON response containing the dataset and its associated targets if found,
                  otherwise an empty dictionary.
    """
    # logging.debug(f'find_metadata_by_metadata_id - metadata_id: {metadata_id}')
    logging.info(f'find_metadata_by_metadata_id - metadata_id: {datasetId}')
    dataset = db_manager.find_dataset_and_targets(datasetId)
    if dataset.dataset_id:
        try:
            dataset.md = json.loads(dataset.md)
            return Response(content=dataset.model_dump_json(by_alias=True), media_type="application/json")
        except json.JSONDecodeError:
            return Response(content=dataset.md, media_type="application/xml")

    return {}


@router.get("/utils/languages")
async def get_languages():
    """
    Endpoint to retrieve the list of supported languages.

    This endpoint reads a JSON file specified by the `LANGUAGES_PATH` setting
    and returns its contents, which represent the supported languages.

    Returns:
        dict: A dictionary containing the supported languages.

    Example:
        Request:
            GET /utils/languages

        Response:
            {
                "en": "English",
                "fr": "French",
                "es": "Spanish"
            }
    """
    with open(settings.LANGUAGES_PATH, "r") as f:
        languages = json.load(f)
    return languages