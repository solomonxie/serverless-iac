"""
REF: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/apigateway.html
"""

import re
import yaml
import logging

import settings
from aws.utils import common_utils

rest_client = settings.rest_client
logger = logging.getLogger(__name__)


def render_specs(specs: dict) -> dict:
    specs['full-name'] = get_api_full_name(specs['name'])
    if any([
        settings.DEPLOY_TYPE not in ['full', 'restapi'],
        settings.DEPLOY_TYPE == 'restapi' and settings.DEPLOY_TARGET != specs['name'],
    ]):
        specs['no-deploy'] = True
    return specs


def render_swagger(path: str, specs: dict) -> dict:
    raw = common_utils.render_text_file(path)
    ptn = re.compile(r'"(arn:aws:.+)"')
    arn_list = sorted(set(ptn.findall(raw)))
    for arn in arn_list:
        info = common_utils.parse_arn(arn)
        if info.get('region'):
            raw = raw.replace(info['region'], settings.AWS_REGION)
        if info.get('account'):
            raw = raw.replace(info['account'], settings.AWS_ACCOUNT_ID)
    swagger = yaml.safe_load(raw)
    api_name = get_api_full_name(specs['name'])
    swagger['info']['title'] = api_name
    swagger.pop('host', None)
    return swagger


def get_api_full_name(name: str):
    full_name = f'{settings.STAGE_NAME}-{settings.STAGE_SUBNAME}-{settings.APPLICATION_NAME}-{name}'
    return full_name


def get_api_by_name(full_name: str):
    api = {}
    paginator = rest_client.get_paginator('get_rest_apis')
    response_iterator = paginator.paginate()
    for resp in response_iterator:
        for item in resp.get("items", []):
            if str(item.get('name')).startswith(str(full_name)):
                api = item
                print('FOUND API [{}]: {}'.format(full_name, item['id']))
                break
    api.pop('ResponseMetadata', None)
    return api


def get_api_stages(api_id: str) -> list:
    if not api_id:
        return []
    response = rest_client.get_stages(restApiId=api_id)
    stages = [x['stageName'] for x in response['item']]
    print('FOUND API STAGES: {}'.format(stages))
    return stages


def create_api_stage(api_id: str, stage_name: str, deployment_id: str) -> dict:
    print('CREATING STAGE [{}] FOR API'.format(stage_name))
    args = {
        'restApiId': api_id,
        'stageName': stage_name,
        'deploymentId': deployment_id,
        'description': stage_name,
        'tracingEnabled': True,
    }
    response = rest_client.create_stage(**args)
    print('OK: CREATED STAGE [{}]'.format(stage_name))
    return response


def get_api_latest_deployment(api_id: str) -> dict:
    if not api_id:
        return {}
    paginator = rest_client.get_paginator('get_deployments')
    response_iterator = paginator.paginate(restApiId=api_id)
    deployments = {}
    for resp in response_iterator:
        deployments.update({x['createdDate']: x for x in resp['items']})
    latest = deployments[max(deployments)] if deployments else {}
    return latest


def create_api_deployment(api_id: str) -> dict:
    args = {
        'restApiId': api_id,
    }
    response = rest_client.create_deployment(**args)
    print(f'DONE: CREATED A DEPLOYMENT FOR API: [{api_id}]')
    return response


def create_api(api_name: str, info: dict) -> dict:
    api_type = 'PRIVATE' if settings.ENABLE_VPC else 'REGIONAL'
    args = {
        'name': api_name,  # REQUIRED
        'description': api_name,
        'endpointConfiguration': {
            'types': [api_type],
        },
        'binaryMediaTypes': [
            '*/*',
            'appliation/gzip',
            'image/*',
        ],
        'tags': {'app_name': settings.APPLICATION_NAME},
    }
    if settings.ENABLE_VPC:
        args['endpointConfiguration']['vpcEndpointIds'] = str(info['vpc-endpoint-ids']).split(',')
        args['policy'] = 'string'  # TODO
    print('CREATING API...')
    response = rest_client.create_rest_api(**args)
    response.pop('ResponseMetadata', None)
    print(f'DONE: CREATED API: [{api_name}]')
    return response


def get_api_route_map(api_id: str) -> dict:
    if not api_id:
        return {}
    paginator = rest_client.get_paginator('get_resources')
    response_iterator = paginator.paginate(restApiId=api_id)
    route_map = {}
    for resp in response_iterator:
        for item in resp['items']:
            for method in item.get('resourceMethods', {}):
                route = item['path']
                info = {'id': item['id'], 'method': method, 'route': item['path']}
                route_map[(method, route)] = info
    print(f'DONE: FOUND {len(route_map)} ROUTES')
    return route_map


def import_routes(api_id: str, swagger_definition: dict):
    swagger_content = yaml.safe_dump(swagger_definition)
    args = {
        'restApiId': api_id,
        'body': swagger_content,
        'mode': 'overwrite',
        'failOnWarnings': True,
    }
    response = rest_client.put_rest_api(**args)
    response.pop('ResponseMetadata', None)
    print('DONE: IMPORTED ROUTES FROM SWAGGER')
    return response


def get_api_integration(api_id: str, resource_id: str, method: str):
    if not api_id or not resource_id or not method:
        return {}
    response = {}
    args = {'restApiId': api_id, 'resourceId': resource_id, 'httpMethod': method}
    try:
        response = rest_client.get_integration(**args)
        response.pop('ResponseMetadata', None)
    except Exception:
        pass
    return response


def delete_api_integration(api_id: str, resource_id: str, method: str):
    response = {}
    args = {'restApiId': api_id, 'resourceId': resource_id, 'httpMethod': method}
    try:
        response = rest_client.delete_integration(**args)
        print(f'DONE: DELETED INTEGRATION FOR ROUTE [{resource_id}]')
        response.pop('ResponseMetadata', None)
    except Exception:
        pass
    return response


def integrate_api_with_lambda(api_id: str, resource_id: str, func_arn: str, method: str):
    uri = f'arn:aws:apigateway:{settings.AWS_REGION}:lambda:path/2015-03-31/functions/{func_arn}/invocations'
    args = {
        'restApiId': api_id,
        'resourceId': resource_id,
        'uri': uri,
        'httpMethod': method,
        'type': 'AWS_PROXY',
        'integrationHttpMethod': 'POST',  # CONFUSING: THIS IS THE "httpMethod" in response
    }
    response = rest_client.put_integration(**args)
    print(f'DONE: CREATED INTEGRATION FOR ROUTE [{resource_id}]')
    response.pop('ResponseMetadata', None)
    return response


def integrate_api_with_stepfunc(*args, **kwargs):
    pass


def integrate_api_with_s3(api_id: str, route_id: str, method: str, *args, **kwargs):
    func_arn = ''  # FIXME
    uri = f'arn:aws:apigateway:{settings.AWS_REGION}:lambda:path/2015-03-31/functions/{func_arn}/invocations'
    args = {
        'restApiId': api_id,
        'resourceId': route_id,
        'uri': uri,
        'httpMethod': method,
        'type': 'AWS',
        'integrationHttpMethod': method,
    }
    response = rest_client.put_integration(**args)
    print(f'DONE: CREATED INTEGRATION FOR ROUTE [{route_id}]')
    response.pop('ResponseMetadata', None)
    return response


def update_route_authorizor(api_id: str, resource_id: str, method: str, auth: dict) -> dict:
    # REF: https://docs.aws.amazon.com/cli/latest/reference/apigateway/update-method.html
    args = {
        'restApiId': api_id,
        'resourceId': resource_id,
        'httpMethod': method,
        'patchOperations': [],
    }
    if auth and auth.get('type') == 'AWS_IAM':
        args['patchOperations'].append({'op': 'replace', 'path': '/authorizationType', 'value': 'AWS_IAM'})
    else:
        args['patchOperations'].append({'op': 'remove', 'path': '/authorizationType'})
    response = {}
    try:
        response = rest_client.update_method(**args)
        print(f'DONE: UPDATED AUTHORIZER [{auth}] FOR ROUTE [{resource_id}]')
        response.pop('ResponseMetadata', None)
    except Exception as e:
        logger.exception(e)
        print(f'FAILED TO UPDATE AUTHORIZER FOR [{auth}] FOR ROUTE [{resource_id}]')
    return response


def remove_api(api_id: str):
    response = rest_client.delete_rest_api(restApiId=api_id)
    print(f'DONE: REMOVED REST API: {api_id}')
    return response
