"""
REF: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/iam.html
"""
import os
import json
import logging
import time

import settings
from utils import common_utils
from settings import iam_client

logger = logging.getLogger(__name__)


def get_role_full_name(short_name: str) -> str:
    full_name = f'{settings.STAGE_NAME}-{settings.STAGE_SUBNAME}-{settings.APPLICATION_NAME}-role-{short_name}'
    assert len(full_name) <= 64, f'ROLE NAME SHOULD BE LESS THAN 64: {full_name}'
    return full_name


def get_policy_full_name(short_name: str) -> str:
    full_name = f'{settings.STAGE_NAME}-{settings.STAGE_SUBNAME}-{settings.APPLICATION_NAME}-policy-{short_name}'
    assert len(full_name) <= 64, f'POLICY NAME SHOULD BE LESS THAN 64: {full_name}'
    return full_name


def get_role_arn_by_name(ro_name: str) -> str:
    arn = 'arn:aws:iam::{}:role/{}'.format(settings.AWS_ACCOUNT_ID, ro_name)
    return arn


def get_policy_arn_by_name(po_name: str) -> str:
    arn = 'arn:aws:iam::{}:policy/{}'.format(settings.AWS_ACCOUNT_ID, po_name)
    return arn


def get_iam_role(ro_name: str) -> dict:
    ro = {}
    try:
        response = iam_client.get_role(RoleName=ro_name)
        ro = response['Role']
        print('DONE: FOUND IAM ROLE [{}]'.format(ro_name))
    except Exception:
        print('ROLE NOT EXISTS:', ro_name)
    return ro


def list_roles_by_prefix(prefix: str = ''):
    ro_list = []
    paginator = iam_client.get_paginator('list_roles')
    response_iterator = paginator.paginate()
    for resp in response_iterator:
        ro_list += resp['Roles']
    name_list = [x['RoleName'] for x in ro_list if x['RoleName'].startswith(prefix)]
    print(f'FOUND [{len(name_list)}] ROLES BY PREFIX [{prefix}]')
    return name_list


def list_role_policies(ro_name):
    po_list = []
    paginator = iam_client.get_paginator('list_attached_role_policies')
    response_iterator = paginator.paginate(RoleName=ro_name)
    for resp in response_iterator:
        po_list += resp['AttachedPolicies']
    arn_list = [x['PolicyArn'] for x in po_list]
    return arn_list


def list_policies_by_prefix(prefix: str = ''):
    po_list = []
    args = {'Scope': 'All'}
    paginator = iam_client.get_paginator('list_policies')
    response_iterator = paginator.paginate(**args)
    for resp in response_iterator:
        po_list += [x for x in resp['Policies'] if x['PolicyName'].startswith(prefix)]
    arn_list = [x['Arn'] for x in po_list]
    print(f'FOUND [{len(arn_list)}] POLICIES BY PREFIX [{prefix}]')
    return arn_list


def list_policy_versions(arn: str) -> list:
    paginator = iam_client.get_paginator('list_policy_versions')
    response_iterator = paginator.paginate(PolicyArn=arn)
    versions = []
    for resp in response_iterator:
        versions += [x['VersionId'] for x in resp['Versions']]
    return versions


def create_iam_role(ro_name: str, service: str = 'lambda') -> dict:
    service_host = {
        'lambda': 'lambda.amazonaws.com',
        # 'stepfunc': 'states.amazonaws.com',
        'stepfunc': ['states.amazonaws.com', 'apigateway.amazonaws.com'],
        'eventbridge': 'events.amazonaws.com',
    }[service]
    response = iam_client.create_role(
        RoleName=ro_name,  # REQUIRED
        AssumeRolePolicyDocument=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": service_host},
                "Action": "sts:AssumeRole",
            }]
        }),  # REQUIRED
        Description=ro_name + ': ' + service,
        MaxSessionDuration=3600,
    )
    ro = response['Role']
    print('DONE: CREATED IAM ROLE [{}]'.format(ro_name))
    return ro


def update_iam_role():
    pass


def attach_policy(ro_name, policy_arn):
    response = iam_client.attach_role_policy(
        RoleName=ro_name,
        PolicyArn=policy_arn,
    )
    response.pop('ResponseMetadata', None)
    print('DONE: ATTACHED IAM POLICY [{}] TO ROLE: [{}]'.format(policy_arn, ro_name))
    return response


def get_iam_policy(arn):
    response = {}
    try:
        response = iam_client.get_policy(PolicyArn=arn)
        response.pop('ResponseMetadata', None)
        print('DONE: FOUND IAM POLICY [{}]'.format(arn))
    except Exception:
        print('POLICY NOT EXISTS:', arn)
    return response


def create_iam_policy(po_name: str, doc_content: str) -> dict:
    response = iam_client.create_policy(
        PolicyName=po_name,  # REQUIRED
        PolicyDocument=doc_content,  # REQUIRED
        Description='this is my policy',
    )
    po = response['Policy']
    print('DONE: CREATED IAM POLICY [{}]'.format(po_name))
    return po


def update_iam_policy(arn, doc_content):
    response = iam_client.create_policy_version(
        PolicyArn=arn,
        PolicyDocument=doc_content,
        SetAsDefault=True,  # ACT AS "UPDATE"
    )
    po = response['PolicyVersion']
    print('DONE: UPDATED IAM POLICY [{}]'.format(arn))
    return po


def deploy_policy(po_name: str, path: str, **iam_specs) -> dict:
    assert len(po_name) <= 64, f'POLICY NAME SHOULD BE LESS THAN 64: {po_name}'
    po_path = os.path.realpath(os.path.expanduser(path))
    po_arn = get_policy_arn_by_name(po_name)
    po_content = json.dumps(common_utils.render_json(po_path, **iam_specs))
    po = get_iam_policy(po_arn) or {}
    if not po:
        po = create_iam_policy(po_name, po_content)
    else:
        # po = update_iam_policy(po_arn, po_content)
        pass
    waiter = iam_client.get_waiter('policy_exists')
    waiter.wait(PolicyArn=po_arn, WaiterConfig={'Delay': 2, 'MaxAttempts': 30})
    return po


def deploy_role(ro_name: str, po_name: str, event_source: str) -> dict:
    assert len(ro_name) <= 64, f'ROLE NAME SHOULD BE LESS THAN 64: {ro_name}'
    ro = get_iam_role(ro_name)
    if not ro:
        ro = create_iam_role(ro_name, event_source)
        waiter = iam_client.get_waiter('role_exists')
        waiter.wait(RoleName=ro_name, WaiterConfig={'Delay': 2, 'MaxAttempts': 30})
    else:
        # iam_utils.update_iam_role()
        pass
    po_arn = get_policy_arn_by_name(po_name)
    existing_po_arns = list_role_policies(ro_name)
    if po_arn not in existing_po_arns:
        attach_policy(ro_name, po_arn)
        # FIXME: NEWLY ATTACHED POLICY CANNOT BE IMMEDIATELY ASSUMED BY LAMBDA
        time.sleep(10)
    return ro


def remove_roles(name_list: list):
    removed = []
    for name in name_list:
        try:
            iam_client.delete_role(RoleName=name)
            removed.append(name)
            print(f'DONE: REMOVED ROLE: {name}')
        except Exception as e:
            logger.exception(e)
    return removed


def remove_policies(arn_list: list):
    removed = []
    for arn in arn_list:
        try:
            versions = list_policy_versions(arn)
            for vid in versions:
                try:
                    iam_client.delete_policy_version(PolicyArn=arn, VersionId=vid)
                except Exception:
                    pass
            iam_client.delete_policy(PolicyArn=arn)
            print(f'DONE: REMOVED POLICY: {arn}')
            removed.append(arn)
        except Exception as e:
            logger.exception(e)
    return removed


def remove_policy_by_prefix(prefix: str):
    arn_list = list_policies_by_prefix(prefix)
    removed = remove_policies(arn_list)
    return removed
