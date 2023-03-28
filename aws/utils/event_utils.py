"""
REF:  https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/events.html
REF: https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html#RateExpressions
"""  # NOQA

import json
import hashlib
import logging

import settings
from aws.utils import iam_utils
from aws.utils import lambda_utils
from aws.utils import common_utils
from aws.utils import stepfunc_utils

event_client = settings.event_client
logger = logging.getLogger(__name__)


def render_specs(specs: dict) -> dict:
    specs['rule-name'] = get_rule_full_name(specs['name'])
    if specs.get('cron'):
        specs['event-type'] = 'cron'
    elif specs.get('event-filter-path'):
        specs['event-type'] = 'event-filter'
        specs['filter'] = json.dumps(common_utils.render_json(specs['event-filter-path']))
    else:
        raise NotImplementedError('PLEASE SPECIFY EVENT TYPE')
    if specs['target-type'] == 'lambda':
        func_name = lambda_utils.get_func_full_name(specs['target-name'])
        specs['target-arn'] = lambda_utils.get_func_arn_by_name(func_name)
        specs['ro-arn'] = ''
    elif specs['target-type'] == 'stepfunc':
        sfn_name = stepfunc_utils.get_stepfunc_full_name(specs['target-name'])
        specs['target-arn'] = stepfunc_utils.get_stepfunc_arn_by_name(sfn_name)
        specs['ro-name'] = iam_utils.get_role_full_name('event-' + specs['name'])
        specs['ro-arn'] = iam_utils.get_role_arn_by_name(specs['ro-name'])
        specs['po-name'] = iam_utils.get_policy_full_name('event-' + specs['name'])
        specs['po-path'] = './aws/iam/iam-policy-eventbridge-call-stepfunc.json'
    else:
        raise NotImplementedError('TARGET TYPE [{}] SUPPORTED'.format(specs.get('target-type')))
    # SKIP DEPLOY
    if any([
        settings.DEPLOY_TYPE not in ['full', 'schedule'],
        settings.DEPLOY_TYPE == 'schedule' and settings.DEPLOY_TARGET != specs['name'],
    ]):
        specs['no-deploy'] = True
    return specs


def get_rule_full_name(short_name: str) -> str:
    prefix = f'rule-{settings.APPLICATION_NAME}-{settings.STAGE_NAME}'
    short_name = short_name.replace(prefix, '')
    full_name = f'{prefix}-{short_name}'
    return full_name


def set_cron(name: str, schedule: str, bus: str = None, role_arn: str = None) -> str:
    args = {
        'Name': name,
        'ScheduleExpression': schedule,
        'State': 'ENABLED',
        'EventBusName': bus or 'default',
        'Description': f'SCHEDULE:[{name}] FOR APP:[{settings.APPLICATION_NAME}]',
        'Tags': [
            {'Key': 'app_name', 'Value': settings.APPLICATION_NAME},
            {'Key': 'stage', 'Value': f'{settings.STAGE_NAME}'},
        ],
    }
    if role_arn:
        args['RoleArn'] = role_arn
    resp = event_client.put_rule(**args)
    arn = resp['RuleArn']
    return arn


def set_event_filter(name: str, event_pattern: str, bus: str = None, role_arn: str = None) -> str:
    args = {
        'Name': name,
        'State': 'ENABLED',
        'EventBusName': bus or 'default',
        'Description': f'EVENT FILTER:[{name}] FOR APP:[{settings.APPLICATION_NAME}]',
        'EventPattern': event_pattern,
        'Tags': [
            {'Key': 'app_name', 'Value': settings.APPLICATION_NAME},
            {'Key': 'stage', 'Value': f'{settings.STAGE_NAME}'},
        ],
    }
    if role_arn:
        args['RoleArn'] = role_arn
    resp = event_client.put_rule(**args)
    arn = resp['RuleArn']
    return arn


def get_rule(rule_name: str, bus: str = None):
    resp = {}
    try:
        resp = event_client.describe_rule(
            Name=rule_name,
            EventBusName=bus or 'default'
        )
        resp.pop('ResponseMetadata', None)
    except Exception:
        pass
    return resp


def get_targets(rule_name: str, bus: str = None) -> dict:
    targets = []
    paginator = event_client.get_paginator('list_targets_by_rule')
    response_iterator = paginator.paginate(Rule=rule_name, EventBusName=bus or 'default')
    for resp in response_iterator:
        targets += resp['Targets']
    tmap = {t.get('Arn'): t for t in targets}
    return tmap


def set_target(rule_name: str, func_arn: str, bus: str = None, role_arn: str = None) -> dict:
    args = {
        'Rule': rule_name,
        'EventBusName': bus or 'default',
        'Targets': [{'Arn': func_arn, 'Id': hashlib.md5(func_arn.encode('utf-8')).hexdigest()}]
    }
    if role_arn:
        args['Targets'][0]['RoleArn'] = role_arn
    tmap = get_targets(rule_name)
    resp = {}
    if func_arn in tmap:
        print(f'TARGET [{func_arn}] EXISTS, SKIP UPDATE.')
    else:
        resp = event_client.put_targets(**args)
        resp.pop('ResponseMetadata', None)
    return resp


def remove_targets(rule_name: str) -> dict:
    targets_map = get_targets(rule_name)
    if targets_map and len(targets_map):
        target_ids = list([x['Id'] for x in targets_map.values()])
        response = event_client.remove_targets(Rule=rule_name, Ids=target_ids, Force=True)
        print(f'DONE: REMOVED TARGETS {target_ids} FROM EVENTBRIDGE RULE [{rule_name}]')
        return response
    else:
        print(f'SKIP: NO TARGETS TO REMOVE OF EVENTBRIDGE RULE {rule_name}')
    return {}


def remove_rule(rule_name: str, bus: str = None):
    response = event_client.delete_rule(
        Name=rule_name,
        EventBusName=bus or 'default',
        Force=True,
    )
    print(f'DONE: REMOVED EVENTBRIDGE RULE [{rule_name}] FROM BUS [{bus}]')
    return response
