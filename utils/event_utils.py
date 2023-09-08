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
    full_name = f'{settings.STAGE_NAME}-{settings.STAGE_SUBNAME}-{settings.APPLICATION_NAME}-schedule-{name}'
    return full_name


def set_event_schedule(name: str, schedule: str, bus: str = None, role_arn: str = None) -> str:
    args = {
        'Name': name,
        'ScheduleExpression': schedule,
        'State': 'ENABLED',
        'EventBusName': bus or 'default',
        'Description': f'SCHEDULE:[{name}] FOR APP:[{settings.APPLICATION_NAME}]',
        'Tags': [
            {'Key': 'app_name', 'Value': settings.APPLICATION_NAME},
        ],
    }
    if role_arn:
        args['RoleArn'] = role_arn
    resp = event_client.put_rule(**args)
    arn = resp['RuleArn']
    return arn


def set_event_rule(name: str, event_pattern: str, bus: str = None, role_arn: str = None) -> str:
    args = {
        'Name': name,
        'State': 'ENABLED',
        'EventBusName': bus or 'default',
        'Description': f'EVENT FILTER:[{name}] FOR APP:[{settings.APPLICATION_NAME}]',
        'EventPattern': event_pattern,
        'Tags': [
            {'Key': 'app_name', 'Value': settings.APPLICATION_NAME},
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


def remove_rule(rule_name: str, bus: str = None):
    response = event_client.delete_rule(
        Name=rule_name,
        EventBusName=bus or 'default',
        Force=True,
    )
    print(f'DONE: REMOVED EVENTBRIDGE RULE [{rule_name}] FROM BUS [{bus}]')
    return response
