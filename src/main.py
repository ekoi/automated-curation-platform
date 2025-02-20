"""
Automated Curation Platform FastAPI Application

This FastAPI application provides endpoints for file uploads, public access, and protected access.
It integrates Keycloak for OAuth2-based authentication and supports token-based authentication with API keys.

Modules:
- `public`: Contains public access routes.
- `protected`: Contains protected access routes.
- `tus_files`: Contains routes for handling file uploads using the Tus protocol.
- `commons`: Contains common settings, logger setup, and utility functions.
- `InspectBridgeModule`: Provides a utility for inspecting bridge plugin classes.
- `db_manager`: Manages the creation of the database and tables.

Dependencies:
- `fastapi`: Web framework for building APIs with Python.
- `starlette`: Asynchronous framework for building APIs.
- `uvicorn`: ASGI server for running the FastAPI application.
- `keycloak`: Provides integration with Keycloak for authentication.
- `emoji`: Library for adding emoji support to Python applications.

"""
import logging
# import importlib.metadata
import os
from contextlib import asynccontextmanager
from typing import Annotated

import emoji
import uvicorn
from akmi_utils import commons as a_commons
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from keycloak import KeycloakOpenID, KeycloakAuthenticationError
from starlette import status
from starlette.middleware.cors import CORSMiddleware

from src import public, protected
from src.commons import settings, data, db_manager, inspect_bridge_plugin, \
    get_version, get_name, project_details
from src.tus_files import upload_files


@asynccontextmanager
async def lifespan(application: FastAPI):
    """
    Lifespan event handler for the FastAPI application.

    This function is executed during the startup of the FastAPI application.
    It initializes the database, iterates through saved bridge plugin directories,
    and prints available bridge classes.

    Args:
        application (FastAPI): The FastAPI application.

    Yields:
        None: The context manager does not yield any value.

    """
    print('start up')
    if not os.path.exists(settings.DB_URL):
        logging.info('Creating database')
        db_manager.create_db_and_tables()
    else:
        logging.info('Database already exists')
    iterate_saved_bridge_plugin_dir()
    print(f'Available bridge classes: {sorted(list(data.keys()))}')
    print(emoji.emojize(':thumbs_up:'))

    yield


api_keys = [settings.DANS_PACKAGING_SERVICE_API_KEY]

security = HTTPBearer()

APP_NAME = os.environ.get("APP_NAME", project_details['title'])
EXPOSE_PORT = os.environ.get("EXPOSE_PORT", 10124)
OTLP_GRPC_ENDPOINT = os.environ.get("OTLP_GRPC_ENDPOINT", "http://localhost:4317")

def auth_header(request: Request, auth_cred: Annotated[HTTPAuthorizationCredentials, Depends(security)]):
    """
    Simplified authentication header dependency function.

    This function checks the provided API key against a list of valid keys or attempts to authenticate using Keycloak.

    Args:
        request (Request): The FastAPI request object.
        auth_cred: The authorization credentials from the request.

    Raises:
        HTTPException: Raised if authentication fails.
    """
    api_key = auth_cred.credentials
    if api_key in api_keys:
        return

    keycloak_env = settings.get(f"keycloak_{request.headers['auth-env-name']}")
    if not keycloak_env:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Forbidden")

    try:
        keycloak_openid = KeycloakOpenID(server_url=keycloak_env.URL, client_id=keycloak_env.CLIENT_ID, realm_name=keycloak_env.REALMS)
        keycloak_openid.userinfo(api_key)
    except KeycloakAuthenticationError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Forbidden")

def pre_startup_routine(app: FastAPI) -> None:

    # Enable CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Upload-Offset", "Location", "Upload-Length", "Tus-Version", "Tus-Resumable", "Tus-Max-Size",
                        "Tus-Extension", "Upload-Metadata", "Upload-Defer-Length", "Upload-Concat", "Upload-Incomplete",
                        "Upload-Complete", "Upload-Draft-Interop-Version"],

    )


# create FastAPI app instance
app = FastAPI(
    title=settings.FASTAPI_TITLE,
    description=settings.FASTAPI_DESCRIPTION,
    version= project_details['version'],
    lifespan=lifespan
)

pre_startup_routine(app)
LOG_FILE = settings.LOG_FILE
log_config = uvicorn.config.LOGGING_CONFIG

if settings.otlp_enable is False:
    logging.basicConfig(filename=settings.LOG_FILE, level=settings.LOG_LEVEL,
                        format=settings.LOG_FORMAT)
else:
    a_commons.set_otlp(app, APP_NAME, OTLP_GRPC_ENDPOINT, LOG_FILE, log_config)


# register routers
    app.include_router(public.router, tags=["Public"], prefix="")
    app.include_router(protected.router, tags=["Protected"], prefix="", dependencies=[Depends(auth_header)])

    app.include_router(upload_files, prefix="/files", include_in_schema=True, dependencies=[Depends(auth_header)])
    # app.include_router(tus_files.router, prefix="", include_in_schema=False)


@app.get('/')
def info():
    """
    Root endpoint to retrieve information about the automated curation platform.

    Returns:
        dict: A dictionary containing the name and version of the automated curation platform.

    """
    return {"name": get_name(), "version": get_version()}


def iterate_saved_bridge_plugin_dir():
    """
    Iterates through saved bridge plugin directories.

    For each Python file in the plugins directory, it inspects the file for bridge classes
    and updates the data dictionary with the class name.

    """
    for filename in os.listdir(settings.PLUGINS_DIR):
        if filename.endswith(".py") and not filename.startswith('__'):
            plugins_path = os.path.join(settings.PLUGINS_DIR, filename)
            for cls_name in inspect_bridge_plugin(plugins_path):
                data.update(cls_name)



if __name__ == "__main__":
    logging.info('START Automated Curation Platform')

    uvicorn.run(app, host="0.0.0.0", port=EXPOSE_PORT, log_config=log_config)