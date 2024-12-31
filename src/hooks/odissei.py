import json

import requests
from datetime import datetime

from src.models.assistant_datamodel import ProcessedMetadata


def dataverse_metadata_fetcher(record, pm: ProcessedMetadata):
    print(record)
    print(pm.service_url)
    print(f"Fetching metadata for record: {record}")
    try:
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json'
        }

        data = {
            'doi': record['id'],
            'metadata_format': "dataverse_json",
            "base_url": record['base_url'],
        }

        response = requests.post(
            pm.service_url,
            headers=headers,
            data=json.dumps(data)
        )
        return response.json()
    except Exception as e:
        print(f"An error occurred: {e}")
    return record

def dataverse_mapper(record, pm: ProcessedMetadata):
    print(record)
    print(pm.service_url)
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }

    data = {'metadata': record}
    with open("/Users/akmi/git/INFRA/automated-curation-platform/resources/templates/odissei/base_dataverse_template.json") as f:
        template = json.load(f)
        data['template'] = template
    with open("/Users/akmi/git/INFRA/automated-curation-platform/resources/templates/odissei/base-mapping.json") as f:
        mapping = json.load(f)
        data['mapping'] = mapping
    data["has_existing_doi"] = True


    response = requests.post(
        pm.service_url,
        headers=headers, data=json.dumps(data)
    )
    print(response.json())
    return response.json()

def refine_metadata(record, pm: ProcessedMetadata):
    print(record)
    print(pm.service_url)
    print(f"Refining metadata for record: {record}")
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }

    data = {
        'metadata': record,
    }

    response = requests.post(pm.service_url,
        headers=headers, data=json.dumps(data)
    )
    print(response.json())
    return response.json()

def enrich_metadata(record, pm: ProcessedMetadata):
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }

    data = {
        "metadata": record,
    }

    response = requests.post(pm.service_url, headers=headers, data=json.dumps(data))
    if not response.ok:
        return {}
    return response.json()



def get_latest_image_tag_version(docker_username, image_repo):

    response = requests.get('https://registry.hub.docker.com/v2/repositories/'
                            f'{docker_username}/{image_repo}/tags')

    if not response.ok:
        return None

    tags = response.json()

    latest_tag = max(tags['results'], key=lambda x: x['last_updated'])
    latest_image = f'{docker_username}/{image_repo}:{latest_tag["name"]}'

    return latest_image

def get_deployed_service_version(service_url):
    response = requests.get(service_url)

    if not response.ok:
        return None

    return response.json()['version']

def get_latest_github_release_version(github_username, github_repo):

    response = requests.get('https://api.github.com/repos/'
                            f'{github_username}/{github_repo}/releases/latest')

    if not response.ok:
        return None

    return response.json()['html_url']

def get_service_version(service_url, service_name, github_username,
                        github_repo, docker_username, image_repo, endpoint):

    service_version = {
        'name': service_name,
        'version': get_deployed_service_version(service_url),
        'docker-image': get_latest_image_tag_version(docker_username,
                                                     image_repo),
        'endpoint': endpoint,
    }

    github_release = get_latest_github_release_version(
        github_username, github_repo)
    if github_release:
        service_version['github-release'] = github_release

    return service_version

def store_workflow_version(version_dict):

    url = 'https://version-tracker.labs.dansdemo.nl/store'
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }

    response = requests.post(url, headers=headers,
                             data=json.dumps(version_dict))
    if not response.ok:
        return None

    version_id = response.json()['id']
    return 'https://version-tracker.labs.dansdemo.nl/retrieve/' + version_id


def add_workflow_versioning_url(record, pm: ProcessedMetadata, pms: [ProcessedMetadata]):
    p_names = [p.name for p in pms]
    VERSION = "v3.0.1"
    print(record)
    print(pm.service_url)
    print(f"Adding workflow versioning URL for record: {record}")

    version_dict = {'workflow_orchestrator': VERSION}

    current_datetime = datetime.now()
    formatted_datetime = current_datetime.strftime("%d-%m-%Y %H:%M:%S")
    version_dict['created_on'] = formatted_datetime

    if "transformer" in p_names:
        transformer_name = 'DANS-transformer-service'
        transformer = get_service_version(
            service_url='https://transformer.labs.dansdemo.nl/',
            service_name=transformer_name,
            github_username='',
            github_repo='',
            docker_username='ekoindarto',
            image_repo='dans-transformer-service',
            endpoint='https://transformer.labs.dansdemo.nl/'
                     'transform-xml-to-json/true'
        )
        version_dict[transformer_name] = transformer

    if "mapper" in p_names:
        mapper_name = 'dataverse-mapper'
        mapper = get_service_version(
            service_url='https://dataverse-mapper.labs.dansdemo.nl/version',
            service_name=mapper_name,
            github_username='odissei-data',
            github_repo=mapper_name,
            docker_username='fjodorvr',
            image_repo=mapper_name,
            endpoint='https://dataverse-mapper.labs.dansdemo.nl/mapper'
        )
        version_dict[mapper_name] = mapper

    if "fetcher" in p_names:
        fetcher_name = 'dataverse-metadata-fetcher'
        fetcher = get_service_version(
            service_url='https://dataverse-fetcher.labs.dansdemo.nl/version',
            service_name=fetcher_name,
            github_username='odissei-data',
            github_repo=fetcher_name,
            docker_username='fjodorvr',
            image_repo=fetcher_name,
            endpoint='https://dataverse-fetcher.labs.dansdemo.nl/'
                     'dataverse-metadata-fetcher'
        )
        version_dict[fetcher_name] = fetcher

    if "minter" in p_names:
        minter_name = 'datacite-minter'
        minter = get_service_version(
            service_url='https://dataciteminter.labs.dansdemo.nl/',
            service_name=minter_name,
            github_username='',
            github_repo='',
            docker_username='ekoindarto',
            image_repo='submitmd2dc-service',
            endpoint='https://dataciteminter.labs.dansdemo.nl/'
                     'submit-to-datacite/register'
        )
        version_dict[minter_name] = minter

    if "importer" in p_names:
        importer_name = 'dataverse-importer'
        importer = get_service_version(
            service_url='https://dataverse-importer.labs.dansdemo.nl',
            service_name=importer_name,
            github_username='odissei-data',
            github_repo=importer_name,
            docker_username='fjodorvr',
            image_repo=importer_name,
            endpoint='https://dataverse-importer.labs.dansdemo.nl'
        )
        version_dict[importer_name] = importer

    if "updater" in p_names:
        updater_name = 'publication-date-updater'
        updater = get_service_version(
            service_url='https://dataverse-date-updater.labs.dansdemo.nl/'
                        'version',
            service_name=updater_name,
            github_username='odissei-data',
            github_repo=updater_name,
            docker_username='fjodorvr',
            image_repo=updater_name,
            endpoint='https://dataverse-date-updater.labs.dansdemo.nl/'
                     'publication-date-updater'
        )
        version_dict[updater_name] = updater

    if "refiner" in p_names:
        refiner_name = 'metadata-refiner'
        refiner = get_service_version(
            service_url='https://metadata-refiner.labs.dansdemo.nl/version',
            service_name=refiner_name,
            github_username='odissei-data',
            github_repo=refiner_name,
            docker_username='fjodorvr',
            image_repo=refiner_name,
            endpoint='https://metadata-refiner.labs.dansdemo.nl/metadata-refinement/datastation'
        )
        version_dict[refiner_name] = refiner

    if "enhancer" in p_names:
        enhancer_name = 'metadata-enhancer'
        enhancer = get_service_version(
            service_url='https://metadata-enhancer.labs.dansdemo.nl/version',
            service_name=enhancer_name,
            github_username='odissei-data',
            github_repo=enhancer_name,
            docker_username='fjodorvr',
            image_repo=enhancer_name,
            endpoint=[
                'https://metadata-enhancer.labs.dansdemo.nl/'
                'dataverse-ELSST-enhancer'
            ]
        )
        version_dict[enhancer_name] = enhancer
    print(json.dumps(version_dict))
    version = store_workflow_version(version_dict)
    print(version)

    keys = ['datasetVersion', 'metadataBlocks', 'provenance']
    d = record

    for key in keys:
        print(key)
        if key not in d:
            d[key] = {}
        d = d[key]

    d['fields'] = [
        {
            "typeName": "workflow",
            "multiple": False,
            "typeClass": "compound",
            "value": {
                "workflowURI": {
                    "typeName": "workflowURI",
                    "multiple": False,
                    "typeClass": "primitive",
                    "value": version
                },
            }
        }
    ]
    return record