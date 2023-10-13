"""
REF: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/logs.html
"""
import logging

import settings
log_client = settings.log_client

logger = logging.getLogger(__name__)


def get_api_log_group_name(name: str) -> str:
    return '/aws/gateway/{}'.format(name)


def get_stepfunc_log_group_name(name: str) -> str:
    return f'/aws/vendedlogs/states/{name}'


def get_log_group_arn(name: str) -> str:
    arn = f'arn:aws:logs:{settings.AWS_REGION}:{settings.AWS_ACCOUNT_ID}:log-group:{name}'
    return arn


def create_or_get_api_log_group_arn(name: str) -> str:
    lg_name = get_api_log_group_name(name)
    lg = get_log_group(lg_name)
    if not lg:
        create_log_group(lg_name)
    arn = f'arn:aws:logs:{settings.AWS_REGION}:{settings.AWS_ACCOUNT_ID}:log-group:{lg_name}'
    return arn


def create_or_get_stepfunc_log_group_arn(name: str) -> str:
    lg_name = get_stepfunc_log_group_name(name)
    lg = get_log_group(lg_name)
    if not lg:
        create_log_group(lg_name)
    arn = f'arn:aws:logs:{settings.AWS_REGION}:{settings.AWS_ACCOUNT_ID}:log-group:{lg_name}'
    return arn


def get_log_group(lg_name: str) -> dict:
    print('SEARCHING CLOUDWATCH LOG GROUP [{}]'.format(lg_name))
    group = {}
    try:
        response = log_client.describe_log_groups(logGroupNamePrefix=lg_name, limit=1)
        print('FETCHED [{}] CLOUDWATCH LOG GROUP'.format(len(response['logGroups'])))
        for item in response['logGroups']:
            if item['logGroupName'] == lg_name:
                group = item
                break
        response.pop('ResponseMetadata', None)
    except Exception:
        print('FAILED TO FETCH CLOUDWATCH GROUPS')
    return group


def create_log_group(lg_name: str, **kwargs) -> dict:
    print('CREATING CLOUDWATCH LOG GROUP [{}]'.format(lg_name))
    log_client.create_log_group(logGroupName=lg_name)
    print('OK: CREATED LOG GROUP: [{}]'.format(lg_name))
    print('ADDING EXPIRE/RETENTION TO LOG GROUP')
    args = {'logGroupName': lg_name, 'retentionInDays': kwargs.get('expire_days') or 7}
    log_client.put_retention_policy(**args)
    print('OK: SET LOGS IN GROUP [{}] EXPIRED IN [{}] DAYS'.format(lg_name, args.get('retentionInDays')))
    return
