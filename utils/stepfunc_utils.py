"""
REF:  https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/stepfunctions.html
"""  # NOQA
import json
import re
import logging

import settings
from utils import iam_utils
from utils import lambda_utils
from utils import common_utils
from utils import cloudwatch_utils

sfn_client = settings.sfn_client
logger = logging.getLogger(__name__)


def render_specs(specs: dict) -> dict:
    specs['ro_name'] = iam_utils.get_role_full_name('ro-' + specs['name'])
    specs['role_arn'] = iam_utils.get_role_arn_by_name(specs['ro_name'])
    specs['po_name'] = iam_utils.get_policy_full_name('stepfunc-general')
    specs['po_path'] = specs.get('policy-path') or './iam/iam-policy-stepfunc-execution.json'
    specs['full_name'] = get_stepfunc_full_name(specs['name'])
    with open(specs['definition-path']) as f:
        raw = f.read()
    specs['definition'] = render_state_machine_expression(raw)
    specs['machine'] = get_state_machine_by_name(specs['full_name'])
    specs['arn'] = specs['machine'].get('stateMachineArn')
    specs['type'] = specs.get('type') or 'STANDARD'
    specs['log_group_name'] = cloudwatch_utils.get_stepfunc_log_group_name(specs['full_name'])
    specs['log_group_info'] = cloudwatch_utils.get_log_group(specs['log_group_name'])
    specs['log_group_arn'] = specs['log_group_info'].get('arn')
    return specs


def get_stepfunc_full_name(short_name: str) -> str:
    full_name = f'{settings.STAGE_NAME}-{settings.STAGE_SUBNAME}-{settings.APPLICATION_NAME}-stepfunc-{short_name}'
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
            short_name = info['name'].replace(common_utils.get_name_prefix('lambda'), '')
            full_name = lambda_utils.get_func_arn_by_name(short_name)
            expression = expression.replace(line, line.replace(name, full_name))
        else:
            full_name = lambda_utils.get_func_arn_by_name(name)
            expression = expression.replace(line, line.replace(name, full_name))
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
            short_name = info['name'].replace(common_utils.get_name_prefix('lambda'), '')
            full_name = lambda_utils.get_func_arn_by_name(short_name)
            specs['Parameters']['FunctionName'] = full_name
        else:
            full_name = lambda_utils.get_func_arn_by_name(name)
            specs['Parameters']['FunctionName'] = full_name
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
        'name': specs['full_name'],
        'definition': json.dumps(specs['definition']),
        'roleArn': specs['role_arn'],
        'type': specs['type'],  # STANDARD|EXPRESS
        'loggingConfiguration': {
            'level': 'ALL',  # 'ALL'|'ERROR'|'FATAL'|'OFF'
            'includeExecutionData': True,
            'destinations': [{
                'cloudWatchLogsLogGroup': {'logGroupArn': specs['log_group_arn']},
            }],
        },
        'tags': [
            {'key': 'app_name', 'value': settings.APPLICATION_NAME},
        ],
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
        'roleArn': specs['role_arn'],
        'loggingConfiguration': {
            'level': 'ALL',  # 'ALL'|'ERROR'|'FATAL'|'OFF'
            'includeExecutionData': True,
            'destinations': [{
                'cloudWatchLogsLogGroup': {'logGroupArn': specs['log_group_arn']},
            }],
        },
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
