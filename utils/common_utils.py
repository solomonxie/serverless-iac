import os
import re
import uuid
import json
import yaml
import hashlib
import logging
from copy import deepcopy
from collections import OrderedDict

import settings
logger = logging.getLogger(__name__)


def get_template() -> dict:
    repo_path = settings.LOCAL_REPO_PATH or download_application_code()
    repo_path = os.path.realpath(os.path.expanduser(repo_path))
    path = os.path.join(repo_path, 'definitions/', settings.TEMPLATE_NAME)
    assert os.path.exists(path), f'SWAWGGER FILE NOT EXISTS: {path}'
    template = render_yaml(path)
    template['info']['repo_path'] = repo_path
    # MERGE LAMBDA DEFAULT
    lambda_default = template['services'].get('lambda') or {}
    for specs in template['resources'].get('lambda') or []:
        specs.update({k: v for k, v in lambda_default.items() if k not in specs})
        specs['env'] = {**lambda_default.get('env', {}), **specs.get('env', {})}
    for specs in template['resources'].get('stepfunc') or []:
        specs['definition-path'] = os.path.realpath(os.path.join(repo_path, specs['definition-path']))
    for specs in template['resources'].get('schedule') or []:
        if specs.get('event-filter-path'):
            specs['event-filter-path'] = os.path.realpath(os.path.join(repo_path, specs['event-filter-path']))
    return template


def get_name_prefix(resource: str = '') -> str:
    prefix = f'{settings.STAGE_NAME}-{settings.APPLICATION_NAME}-'
    if resource:
        prefix += str(resource) + '-'
    return prefix


def download_application_code():
    tmp_path = f'/tmp/code-{uuid.uuid4().hex}'
    assert 0 == os.system(f'git clone -b {settings.BUILD_NO} {settings.REPO_URL} {tmp_path}')
    assert 0 == os.system(f'tree {tmp_path}')
    return tmp_path


def get_swagger_definition(template: dict):
    swagger = {}
    for k, v in template.items():
        if k.startswith('swagger-'):
            swagger[k.replace('swagger-', '')] = v
    return swagger


def parse_swagger_route_map(definitions: dict):
    definitions = deepcopy(definitions)
    route_map = {}
    for route, methods in definitions.items():
        for method, info in methods.items():
            route_key = ' '.join([method.upper(), route])
            info.update({
                'method': method.upper(), 'route': route, 'route_key': route_key,
                'auth': info.get('x-api-authorizer') or {},
            })
            route_map[route_key] = info
            print('SWAGGER DEFINED API ROUTE: [{}]'.format(info['route_key']))
    return route_map


def render_text_file(path: str, **kwargs) -> str:
    path = os.path.realpath(os.path.expanduser(path))
    if not path:
        return {}
    with open(path, 'r') as f:
        raw = f.read()
    ptn = re.compile(r'\$\{([^}]+)\}')
    env_names = sorted(set(ptn.findall(raw)))
    for k in env_names:
        v = kwargs.get(k) or getattr(settings, k, None) or os.environ.get(k)
        if v:
            raw = raw.replace('${' + k + '}', v)
    return raw


def parse_arn(arn: str) -> dict:
    """
    Lambda: arn:aws:lambda:us-east-1:12345:function:my-poc-abc
    LambdaAlias: arn:aws:lambda:us-east-1:12345:function:my-poc-abc:myalias
    Layer: arn:aws:lambda:us-east-1:12345:layer:search-task-lambdalayer:1
    StepFunc: arn:aws:states:us-east-1:12345:stateMachine:stepfunc-company-task
    S3: arn:aws:s3:::my-poc-bucket
    EventBridge: arn:aws:events:us-east-1:123123123:rule/weekly-company-search
    Role: arn:aws:iam::12345:role/search-task-role-ro-company-task
    Policy: arn:aws:iam::12345:policy/search-task-policy-lambda-general
    SQS: arn:aws:sqs:us-east-1:123123123:hello-standard-queue
    SNS: arn:aws:sns:us-east-1:123123123:hello-sns-topic
    API Gateway: arn:aws:apigateway:us-east-1:s3:path/my-poc/upload
    API Gateway: arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:123123123:function:prod-green-my-bulk-delivery-lambda-launch_task/invocations
    """  # NOQA
    info = {}
    parts = str(arn).split(':')
    if arn.startswith('arn:aws:iam'):
        resource, name = parts[5].split('/')
        info = OrderedDict({
            'service': parts[2],
            'region': parts[3],
            'account': parts[4],
            'resource': resource,
            'name': name,
            'extra': parts[6:] if len(parts) >= 5 else [],
        })
    elif arn.startswith('arn:aws:sns') or arn.startswith('arn:aws:sqs'):
        info = OrderedDict({
            'service': parts[2],
            'region': parts[3],
            'account': parts[4],
            'resource': parts[2],
            'name': parts[5],
            'extra': parts[6:] if len(parts) >= 6 else [],
        })
    elif arn.startswith('arn:aws:apigateway'):
        info = OrderedDict({
            'service': parts[2],
            'region': parts[3],
            'target': parts[4],
        })
    else:
        info = OrderedDict({
            'service': parts[2],
            'region': parts[3],
            'account': parts[4],
            'resource': parts[5],
            'name': parts[6],
            'extra': parts[7:] if len(parts) >= 7 else [],
        })
    return info


def render_yaml(path: str, **kwargs) -> dict:
    content = render_text_file(path, **kwargs)
    result = yaml.safe_load(content)
    return result


def render_json(path: str, **kwargs) -> dict:
    content = render_text_file(path, **kwargs)
    result = json.loads(content)
    return result


def get_role_arn_by_name(role_name: str) -> str:
    arn = f'arn:aws:iam::{settings.AWS_ACCOUNT_ID}:role/{role_name}'
    return arn


def file_to_sha(path: str) -> str:
    path = os.path.realpath(os.path.expanduser(path))
    with open(path, 'rb') as f:
        raw = f.read()
    sha = hashlib.md5(raw).hexdigest()
    return sha


def is_int(s: str) -> bool:
    result = False
    try:
        int(s)
        result = True
    except Exception as e:
        logger.exception(e)
    return result
