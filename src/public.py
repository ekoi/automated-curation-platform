import json

from fastapi import APIRouter
from starlette.responses import Response

# from src import db
from src.commons import logger, data, db_manager, LOG_NAME_ACP, settings

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
async def progress_state(owner_id: str):
    """
    Endpoint to retrieve the progress state of assets owned by a specific owner.

    Args:
        owner_id (str): The ID of the owner whose assets' progress state is to be retrieved.

    Returns:
        list: A list of rows representing the progress state of the owner's assets.
              If no assets are found, an empty list is returned.
    """
    rows = db_manager.find_owner_assets(owner_id)
    if rows:
        return rows
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