"""
REF: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/apigatewayv2.html
"""
import json
import logging

import settings

gw_client = settings.gw_client
logger = logging.getLogger(__name__)


def get_api_by_name(name: str):
    api = {}
    paginator = gw_client.get_paginator('get_apis')
    response_iterator = paginator.paginate()
    for resp in response_iterator:
        for item in resp.get("Items", []):
            if str(item.get('Name')).startswith(str(name)):
                api = item
                print('FOUND API [{}]: {}'.format(name, item['ApiId']))
                break
    api.pop('ResponseMetadata', None)
    return api


def get_api_by_id(api_id: str) -> dict:
    if not api_id:
        return {}
    response = {}
    try:
        response = gw_client.get_api(apiId=api_id)
    except Exception as e:
        raise e
    return response


def get_api_route_map(api_id: str) -> dict:
    if not api_id:
        return {}
    paginator = gw_client.get_paginator('get_routes')
    response_iterator = paginator.paginate(ApiId=api_id)
    route_map = {}
    for resp in response_iterator:
        for item in resp['Items']:
            route_map[item['RouteKey']] = item
            print('FOUND API ROUTE: {}'.format(item['RouteKey']))
    return route_map


def get_api_route(api_id: str, route_id: str) -> dict:
    if not api_id or not route_id:
        return {}
    response = {}
    try:
        response = gw_client.get_route(ApiId=api_id, RouteId=route_id)
    except Exception as e:
        print('FAILED TO GET ROUTE: {}'.format(route_id), e)
    return response


def get_api_stages(api_id: str) -> list:
    if not api_id:
        return {}
    response = gw_client.get_stages(ApiId=api_id)
    stg_map = {x['StageName']: x for x in response['Items']}
    print('FOUND API STAGES: {}'.format(list(stg_map.keys())))
    return stg_map


def get_api_integrations(api_id: str) -> dict:
    if not api_id:
        return {}
    itg_map = {}
    paginator = gw_client.get_paginator('get_integrations')
    response_iterator = paginator.paginate(ApiId=api_id)
    for resp in response_iterator:
        for item in resp.get("Items", []):
            itg_id = 'integrations/{}'.format(item['IntegrationId'])
            itg_map.update({itg_id: item})
    return itg_map


def get_api_full_name(name: str):
    full_name = f'{settings.STAGE_NAME}-{settings.STAGE_SUBNAME}-{settings.APPLICATION_NAME}-httpapi-{name}'
    return full_name


def create_api(api_name) -> dict:
    args = {
        'ProtocolType': 'HTTP',  # REQUIRED
        'Name': api_name,  # REQUIRED
        'Description': api_name,
        'DisableExecuteApiEndpoint': False,
    }
    print('CREATING API...')
    response = gw_client.create_api(**args)
    response.pop('ResponseMetadata', None)
    print('DONE: CREATED API.')
    return response


def update_api(name, **kwargs):
    pass


def create_api_integration(api_id: str, func_arn: str) -> str:
    print('CREATING INTEGRATION FOR LAMBDA: {}'.format(func_arn))
    itg_id = None
    args = {
        'ApiId': api_id,  # REQUIRED
        'IntegrationType': 'AWS_PROXY',  # REQUIRED
        'IntegrationMethod': 'POST',  # REQUIRED
        'IntegrationUri': func_arn,  # REQUIRED
        'PayloadFormatVersion': '2.0',  # REQUIRED
    }
    try:
        response = gw_client.create_integration(**args)
        itg_id = 'integrations/{}'.format(response['IntegrationId'])
        print('DONE: CREATED INTEGRATION [{}] FOR LAMBDA'.format(itg_id))
    except Exception as e:
        print('FAILED TO CREATE INTEGRATION')
        raise e
    return itg_id


def create_api_route(api_id: str, method: str, route: str, integration_id: str, auth: dict) -> dict:
    route_key = '{} {}'.format(method, route)
    print('CREATING ROUTE: {}'.format(route_key))
    args = {
        'ApiId': api_id,  # REQUIRED
        'RouteKey': route_key,  # REQUIRED
        'Target': integration_id,
    }
    if not settings.DISABLE_API_AUTHORIZER and auth and auth.get('type') == 'AWS_IAM':
        args['AuthorizationType'] = 'AWS_IAM'
    else:
        args['AuthorizationType'] = 'NONE'
    response = gw_client.create_route(**args)
    print('DONE: CREATED ROUTE: {}'.format(route_key))
    return response


def update_api_route(api_id: str, route_id: str, integration_id: str, auth: dict) -> dict:
    print('UPDATING ROUTE: {}'.format(route_id))
    args = {
        'ApiId': api_id,  # REQUIRED
        'RouteId': route_id,  # REQUIRED
        'Target': integration_id,
    }
    if not settings.DISABLE_API_AUTHORIZER and auth and auth.get('type') == 'AWS_IAM':
        args['AuthorizationType'] = 'AWS_IAM'
    else:
        args['AuthorizationType'] = 'NONE'
    response = gw_client.update_route(**args)
    print('DONE: UPDATED ROUTE: {}'.format(route_id))
    return response


def create_api_stage(api_id: str, stage_name: str, log_group_arn: str, throttling: dict = {}) -> dict:
    print('CREATING STAGE [{}] FOR API'.format(stage_name))
    args = {
        'ApiId': api_id,  # REQUIRED
        'StageName': stage_name,  # REQUIRED
        'AutoDeploy': True,
        'StageVariables': {
            'stage_name': stage_name,
        },
        'DefaultRouteSettings': {
            'ThrottlingBurstLimit': throttling.get('burst-limit') or 20,
            'ThrottlingRateLimit': throttling.get('rate-limit') or 10,
        },
        'AccessLogSettings': {
            'DestinationArn': log_group_arn,
            'Format': json.dumps({
                "requestId": "$context.requestId",
                "ip": "$context.identity.sourceIp",
                "requestTime": "$context.requestTime",
                "httpMethod": "$context.httpMethod",
                "routeKey": "$context.routeKey",
                "status": "$context.status",
                "protocol": "$context.protocol",
                "stage_name": stage_name,
                "responseLength": "$context.responseLength",
            }),
        },
    }
    response = gw_client.create_stage(**args)
    print('DONE: CREATED STAGE [{}]'.format(stage_name))
    return response


def get_route_throttling_by_route_map(route_map: dict) -> dict:
    t = {}
    for route_key, info in route_map.items():
        throttling = info.get('x-throttling') or {}
        rate = min(9000, throttling.get('rate-limit') or 20)
        burst = min(4000, throttling.get('burst-limit') or 10)
        t[route_key] = {
            'ThrottlingBurstLimit': rate,
            'ThrottlingRateLimit': burst,
        }
        print(f'ADDING THROTTLING [B:{burst} / R:{rate}] FOR ROUTE [{route_key}]')
    return t


def update_route_throttling(api_id: str, stage_name: str, throttling: dict = {}) -> dict:
    print('UPDATING STAGE [{}] FOR API'.format(stage_name))
    args = {
        'ApiId': api_id,  # REQUIRED
        'StageName': stage_name,  # REQUIRED
        'AutoDeploy': True,
        'StageVariables': {
            'stage_name': stage_name,
        },
    }
    if throttling:
        args['RouteSettings'] = throttling
    response = gw_client.update_stage(**args)
    print(f'DONE: UPDATED ROUTE THROTTLING FOR STAGE [{stage_name}]')
    return response


def remove_api(api_id: str):
    response = gw_client.delete_api(ApiId=api_id)
    print(f'DONE: REMOVED API: {api_id}')
    return response
