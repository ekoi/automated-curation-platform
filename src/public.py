import json
from jsoncomparison import Compare, NO_DIFF

import requests
from fastapi import APIRouter, Request, HTTPException
from starlette.responses import Response

# from src import db
from src.commons import logger, data, db_manager, LOG_NAME_ACP, settings
from src.models.app_model import OwnerAssetsModel, Asset, TargetApp

# import logging

router = APIRouter()


@router.get("/available-modules")
async def get_modules_list():
    """
    Endpoint to retrieve a list of available modules.

    This endpoint returns a sorted list of keys from the `data` dictionary,
    which represents the available modules in the system.

    Returns:
        list: A sorted list of available module names.
    """
    return sorted(list(data.keys()))

@router.get("/progress-state/{owner_id}")
async def progress_state(owner_id: str, req: Request):
    """
    Endpoint to retrieve the progress state of assets owned by a specific owner.

    Args:
        owner_id (str): The ID of the owner whose assets' progress state is to be retrieved.

    Returns:
        list: A list of rows representing the progress state of the owner's assets.
              If no assets are found, an empty list is returned.
    """
    tc_header = req.headers.get('targets-credentials')
    if not tc_header:
        raise HTTPException(status_code=400, detail="Targets credentials are missing")

    try:
        target_creds = json.loads(tc_header)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid json format of targets-credentials")

    datasets = db_manager.find_datasets_by_owner(owner_id)
    if not datasets:
        return []

    oam = OwnerAssetsModel(owner_id=owner_id)
    for dataset in datasets:
        asset = Asset(
            dataset_id=str(dataset.id),
            release_version=dataset.release_version.name,
            title=dataset.title,
            created_date=dataset.created_date.strftime('%Y-%m-%d %H:%M:%S'),
            saved_date=dataset.saved_date.strftime('%Y-%m-%d %H:%M:%S'),
            submitted_date=dataset.submitted_date.strftime('%Y-%m-%d %H:%M:%S') if dataset.submitted_date else '',
            version=dataset.version or ''
        )

        targets_repo = db_manager.find_target_repos_by_dataset_id(str(dataset.id))
        for target_repo in targets_repo:
            target = TargetApp(
                repo_name=target_repo.name,
                display_name=target_repo.display_name,
                deposit_status=target_repo.deposit_status,
                deposit_time=target_repo.deposit_time.strftime('%Y-%m-%d %H:%M:%S') if target_repo.deposit_time else '',
                duration=str(target_repo.duration)
            )

            rsp = json.loads(target_repo.target_output) if target_repo.target_output else {}
            if rsp:
                idents = rsp['response'].get('identifiers', [])
                target.output_response = {"response": {"identifiers": idents}}
                if idents:
                    url = idents[0]['url']
                    if "dataset.xhtml" in url:
                        target.diff = await fetch_dv_json(rsp, target, target_creds, url)
            asset.targets.append(target)
        oam.assets.append(asset)
    return oam


async def fetch_dv_json(rsp, target, target_creds, url):
    """
    Fetch JSON data from a Dataverse API and compare it with the deposited metadata.

    Args:
        rsp (dict): The response dictionary containing deposited metadata.
        target (TargetApp): The target application instance.
        target_creds (list): A list of credentials for target repositories.
        url (str): The URL to fetch the JSON data from.

    Returns:
        dict: The differences between the deposited metadata and the fetched JSON data.
              If no differences are found, returns an empty dictionary.
    """
    # Modify the URL to point to the correct API endpoint
    url = url.replace("dataset.xhtml", "api/datasets/:persistentId/")

    # Iterate over the target credentials to find the matching repository
    for tc in target_creds:
        if tc["target-repo-name"] == target.repo_name:
            # Extract the API token from the credentials
            api_token = tc["credentials"]["password"]
            headers = {
                "X-Dataverse-key": api_token
            }
            # Make a GET request to the modified URL with the API token in headers
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                # Compare the deposited metadata with the fetched JSON data
                diff = Compare().check(rsp["deposited_metadata"], response.json())
                return diff
            else:
                # Log an error message if the response status code is not 200
                logger(f'Error occurs: status code: {response.status_code}', 'error', settings.LOG_LEVEL, LOG_NAME_ACP)

            # Break the loop after processing the relevant credentials
            break

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
    logger(f'find_metadata_by_metadata_id - metadata_id: {datasetId}', settings.LOG_LEVEL, LOG_NAME_ACP)
    dataset = db_manager.find_dataset_and_targets(datasetId)
    if dataset.dataset_id:
        dataset.md = json.loads(dataset.md)
        return Response(content=dataset.model_dump_json(by_alias=True), media_type="application/json")
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