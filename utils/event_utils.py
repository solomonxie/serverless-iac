"""
REF:  https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/events.html
REF: https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html#RateExpressions
"""  # NOQA

import hashlib
import logging

import settings

event_client = settings.event_client
logger = logging.getLogger(__name__)


def get_rule_full_name(name: str) -> str:
    full_name = f'eventbridgerule-{settings.APPLICATION_NAME}-{settings.STAGE_NAME}-{name}'
    return full_name


def set_event_schedule(specs: dict) -> str:
    args = {
        'Name': specs['name'],
        'ScheduleExpression': specs['expression'],
        'State': 'ENABLED',
        'RoleArn': specs['role-arn'],
        'EventBusName': specs.get('bus') or 'default',
        'Description': specs['name'],
        'Tags': [{'Key': k, 'Value': v} for k, v in specs.get('tags', {}).items()],
    }
    resp = event_client.put_rule(**args)
    arn = resp['RuleArn']
    return arn


def set_event_rule(specs: dict) -> str:
    args = {
        'Name': specs['name'],
        'State': 'ENABLED',
        'EventBusName': specs.get('bus') or 'default',
        'Description': specs['name'],
        'Tags': [{'Key': k, 'Value': v} for k, v in specs.get('tags', {}).items()],
    }
    if specs.get('role-arn'):
        args['RoleArn'] = specs['role-arn']
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


def set_target(specs: dict) -> dict:
    # REF: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/events/client/put_targets.html
    target_arn = specs['target-arn']
    args = {
        'Rule': specs['rule-name'],
        'EventBusName': specs.get('bus') or 'default',
        'Targets': [{
            'Arn': target_arn,
            'Id': hashlib.md5(target_arn.encode('utf-8')).hexdigest(),
            'RoleArn': specs['role-arn'],
            'Input': specs.get('payload'),
        }]
    }
    tmap = get_targets(specs['rule-name'])
    resp = {}
    if target_arn in tmap:
        print(f'TARGET [{target_arn}] EXISTS, SKIP UPDATE.')
    else:
        resp = event_client.put_targets(**args)
        resp.pop('ResponseMetadata', None)
    return resp


def remove_rule(rule_name: str, bus: str = None):
    response = event_client.delete_rule(
        Name=rule_name,
        EventBusName=bus or 'default',
        Force=True,
    )
    print(f'DONE: REMOVED EVENTBRIDGE RULE [{rule_name}] FROM BUS [{bus}]')
    return response
