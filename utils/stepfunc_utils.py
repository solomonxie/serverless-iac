"""
REF:  https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/stepfunctions.html
"""  # NOQA
import json
import re
import logging

import settings
from utils import lambda_utils
from utils import common_utils

sfn_client = settings.sfn_client
logger = logging.getLogger(__name__)


def get_stepfunc_full_name(short_name: str) -> str:
    full_name = f'stepfunc-{settings.APPLICATION_NAME}-{settings.STAGE_NAME}-{short_name}'
    return full_name


def get_stepfunc_arn_by_name(name: str) -> str:
    arn = f'arn:aws:states:{settings.AWS_REGION}:{settings.AWS_ACCOUNT_ID}:stateMachine:{name}'
    return arn


def get_state_machine_by_name(name: str) -> dict:
    arn = get_stepfunc_arn_by_name(name)
    step_func = {}
    try:
        resp = sfn_client.describe_state_machine(stateMachineArn=arn)
        resp.pop('ResponseMetadata', None)
        step_func = resp
    except Exception:
        print(f'404: STATE MACHINE NOT EXISTS: {arn}')
    return step_func


def render_state_machine_expression(expression: str) -> dict:
    ptn = re.compile(r'("FunctionName"\s?:\s?"([^"]+)")')
    funcs = ptn.findall(expression) or []
    for line, name in funcs:
        # UNIFY / CONVERT FUNCTION NAMES UNDER THE SAME SCOPE:
        if name.startswith('arn:aws:lambda'):
            info = common_utils.parse_arn(name)
            func_name = info['name'].replace(common_utils.get_name_prefix('lambda'), '')
            arn = lambda_utils.get_func_arn_by_name(func_name)
            expression = expression.replace(line, line.replace(name, arn))
        else:
            arn = lambda_utils.get_func_arn_by_name(name)
            expression = expression.replace(line, line.replace(name, arn))
    machine_expressions = json.loads(expression)
    return machine_expressions


def render_state_machine(path: str) -> dict:
    with open(path) as f:
        raw = f.read()
    machine = json.loads(raw)
    for name, specs in machine['States'].items():
        if not specs.get('Parameters', {}).get('FunctionName'):
            continue
        funcname = specs['Parameters']['FunctionName']
        if funcname.startswith('arn:aws:lambda'):
            info = common_utils.parse_arn(funcname)
            func_name = info['name'].replace(common_utils.get_name_prefix('lambda'), '')
            arn = lambda_utils.get_func_arn_by_name(func_name)
            specs['Parameters']['FunctionName'] = arn
        else:
            arn = lambda_utils.get_func_arn_by_name(name)
            specs['Parameters']['FunctionName'] = arn
    return machine


def get_state_machine_function_names(specs: dict) -> list:
    names = []
    for name, specs in specs['States'].items():
        if specs.get('Parameters', {}).get('FunctionName'):
            funcname = specs['Parameters']['FunctionName']
            info = common_utils.parse_arn(funcname)
            short_name = info['name'].replace(common_utils.get_name_prefix('lambda'), '')
            names.append(short_name)
    return names


def create_stepfunc(specs: dict) -> dict:
    args = {
        'name': specs['name'],
        'definition': json.dumps(specs['definition']),
        'roleArn': specs['role-arn'],
        'type': specs['type'],  # STANDARD|EXPRESS
        'tags': [{'key': k, 'value': v} for k, v in specs.get('tags', {}).items()],
        # 'loggingConfiguration': {
        #     'level': 'ALL',  # 'ALL'|'ERROR'|'FATAL'|'OFF'
        #     'includeExecutionData': True,
        #     'destinations': [{
        #         'cloudWatchLogsLogGroup': {'logGroupArn': specs['log_group_arn']},
        #     }],
        # },
    }
    if settings.ENABLE_XRAY:
        args['tracingConfiguration'] = {'enabled': True}
    resp = sfn_client.create_state_machine(**args)
    resp.pop('ResponseMetadata', None)
    print('DONE: CREATED STATE-MACHINE:', resp['stateMachineArn'])
    return resp


def update_stepfunc(arn: str, specs: dict) -> dict:
    args = {
        'stateMachineArn': arn,
        'definition': json.dumps(specs['definition']),
        'roleArn': specs['role-arn'],
        # 'loggingConfiguration': {
        #     'level': 'ALL',  # 'ALL'|'ERROR'|'FATAL'|'OFF'
        #     'includeExecutionData': True,
        #     'destinations': [{
        #         'cloudWatchLogsLogGroup': {'logGroupArn': specs['log_group_arn']},
        #     }],
        # },
    }
    if settings.ENABLE_XRAY:
        args['tracingConfiguration'] = {'enabled': True}
    sfn_client.update_state_machine(**args)
    print('DONE: UPDATED STATE-MACHINE:', arn)
    return


def get_stepfunc_invoke_caller_arn(api_id: str, route: str):
    caller_arn = 'arn:aws:execute-api:{}:{}:{}/{}/{}{}'.format(
        settings.AWS_REGION, settings.AWS_ACCOUNT_ID, api_id, '*', '*', route,
    )
    return caller_arn


def remove_state_machine(arn: str):
    response = sfn_client.delete_state_machine(stateMachineArn=arn)
    print(f'DONE: REMOVED STATE MACHINE: {arn}')
    return response
