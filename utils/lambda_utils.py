"""
REF: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html
REF: https://stackoverflow.com/questions/33825815/how-to-calculate-the-codesha256-of-aws-lambda-deployment-package-before-uploadin
"""  # NOQA
import os
import json
import uuid
import logging

import settings
from utils.s3_utils import S3Bucket
from utils.common_utils import is_int
from utils.common_utils import get_app_env_dict

lambda_client = settings.lambda_client
s3_client = S3Bucket(settings.AWS_LAMBDA_BUCKET)
logger = logging.getLogger(__name__)


def get_func_full_name(short_name: str) -> str:
    full_name = f'lambda-{settings.APPLICATION_NAME}-{settings.STAGE_NAME}-{short_name}'
    return full_name


def get_func_arn_by_name(short_name: str) -> str:
    full_name = get_func_full_name(short_name)
    arn = 'arn:aws:lambda:{}:{}:function:{}:{}'.format(
        settings.AWS_REGION, settings.AWS_ACCOUNT_ID, full_name, settings.FUNC_ALIAS,
    )
    return arn


def get_func_s3_key_by_name(full_name: str) -> str:
    func_s3_key = 'lambda-function/{}/{}/{}-BUILD-{}.zip'.format(
        settings.APPLICATION_NAME, settings.STAGE_NAME, full_name, settings.BUILD_NO,
    )
    return func_s3_key


def list_all_functions_by_app() -> dict:
    functions = []
    paginator = lambda_client.get_paginator('list_functions')
    response_iterator = paginator.paginate()
    for resp in response_iterator:
        functions += resp['Functions']
    func_map = {
        f['FunctionName']: f for f in functions if str(f['FunctionName']).startswith(settings.APPLICATION_NAME)
    }
    return func_map


def get_lambda_invoke_caller_arn(api_id: str, route: str):
    caller_arn = 'arn:aws:execute-api:{}:{}:{}/{}/{}{}'.format(
        settings.AWS_REGION, settings.AWS_ACCOUNT_ID, api_id, '*', '*', route,
    )
    return caller_arn


def get_lambda_invoke_policy(func_arn, caller_arn):
    po = {}
    try:
        response = lambda_client.get_policy(FunctionName=func_arn)
        for stmt in json.loads(response['Policy'])['Statement']:
            if caller_arn == stmt.get('Condition', {}).get('ArnLike', {}).get('AWS:SourceArn', ''):
                po = stmt
                print('FOUND LAMBDA INVOKE POLICY: [{}]'.format(po['Sid']))
                break
    except Exception:
        pass
    return po


def create_lambda_invoke_policy(func_arn: str, caller_arn: str):
    args = {
        'FunctionName': func_arn,  # REQUIRED
        # 'SourceAccount': settings.AWS_ACCOUNT_ID,  # REQUIRED
        'StatementId': str(uuid.uuid4().hex),  # REQUIRED
        'Action': 'lambda:InvokeFunction',  # REQUIRED
        'Principal': 'apigateway.amazonaws.com',  # REQUIRED
        'SourceArn': caller_arn,  # REQUIRED
    }
    resp = lambda_client.add_permission(**args)
    resp.pop('ResponseMetadata', None)
    po = json.loads(resp['Statement'])
    print('DONE: ADDED INVOKE POLICY [{}] TO LAMBDA'.format(po['Sid']))
    return po


def remove_lambda_invoke_policy(func_arn, po_id):
    resp = lambda_client.remove_permission(FunctionName=func_arn, StatementId=po_id)
    resp.pop('ResponseMetadata', None)
    print('DONE: REMOEVD EXISTING LAMBDA POLICY, WILL ATTACH A NEW ONE')
    return resp


def get_func_info_by_short_name(short_name: str, alias: str = settings.FUNC_ALIAS) -> dict:
    full_name = get_func_full_name(f'{short_name}:{alias}')
    return get_func_info_by_name(full_name)


def get_func_info_by_name(func_name) -> dict:
    info = {}
    try:
        resp = lambda_client.get_function(FunctionName=func_name)
        resp.pop('ResponseMetadata', None)
        info = resp['Configuration']
    except Exception:
        pass
    return info


def get_func_latest_version(func_name: str):
    latest = {}
    try:
        fmap = {}
        paginator = lambda_client.get_paginator('list_versions_by_function')
        response_iterator = paginator.paginate(FunctionName=func_name)
        for resp in response_iterator:
            for func in resp['Versions']:
                fmap[func['Version']] = func
        default_latest = fmap.pop('$LATEST', {})
        latest = fmap[str(max([int(v) for v in fmap if is_int(v)]))] if len(fmap) else default_latest
    except Exception:
        print(f'NO LATEST VERSION FOUND FOR [{func_name}]')
    return latest


def get_all_func_versions(func_name: str) -> list:
    versions = []
    try:
        paginator = lambda_client.get_paginator('list_versions_by_function')
        response_iterator = paginator.paginate(FunctionName=func_name)
        for resp in response_iterator:
            versions += resp['Versions']
    except Exception:
        print(f'FAILED TO GET ALL VERSIONS FOR [{func_name}]')
    return versions


def filter_func_latest_version(func_versions: list) -> dict:
    fmap = {func['Version']: func for func in func_versions}
    default = fmap.pop('$LATEST', {})
    latest = fmap[max([v for v in fmap if is_int(v)])] if len(fmap) else default
    return latest


def compile_and_upload_python_code(repo_path: str, specs: dict) -> str:
    print('ZIPPING CODE ARCHIVE...')
    func_s3_key = specs['func_s3_key']
    tmp_path = '/tmp/code_{}.zip'.format(uuid.uuid4().hex)
    # # FYI: "git archive" WILL RESPECT [".gitignore", ".gitattributes"]
    # assert 0 == os.system(f'cd {repo_path} && git archive HEAD . -o {tmp_path}'), 'FAILED TO ARCHIVE'
    # for ignore in specs.get('upload-ignore') or []:
    #     assert 0 == os.system(f'zip --delete {tmp_path} "{ignore}" ||true')
    # assert 0 == os.system(f'zip -sf {tmp_path}'), f'FAILED TO READ ZIP FILE: {tmp_path}'
    patterns = ['.git/*', 'tests/*', '*/__pycache__/*', '.DS_Store']
    patterns += specs.get('upload-ignore') or []
    ignores = ' '.join([f'--exclude="{ptn}"' for ptn in patterns])
    cmd = f'cd {repo_path} && zip -r {ignores} {tmp_path} .'
    assert 0 == os.system(cmd), 'FAILED TO ARCHIVE'
    print('DONE: ZIP ARCHIVED')
    s3_client.upload_file(tmp_path, func_s3_key)
    assert s3_client.exists(func_s3_key), f'FAILED TO UPLOAD CODE: {func_s3_key}'
    print('DONE: UPLOADED CODE ZIP ARCHIVE')
    assert 0 == os.system(f'rm {tmp_path} ||true')
    print('DONE: REMOVED TMP FILES')
    return func_s3_key


def create_python_function(specs: dict) -> dict:
    full_name = specs['full_name']
    print(f'CREATING LAMBDA [{full_name}]')
    args = {
        'Publish': True,  # FYI: IMPORTANT
        'FunctionName': full_name,  # REQUIRED
        'Handler': specs['handler'],  # REQUIRED
        'Runtime': specs['runtime'],  # REQUIRED
        'Role': specs['role-arn'],  # REQUIRED
        'Architectures': [specs['arch']],
        'Timeout': specs['timeout'],
        'MemorySize': specs['mem'],
        'PackageType': 'Zip',
        'Code': {  # REQUIRED
            'S3Bucket': settings.AWS_LAMBDA_BUCKET,
            'S3Key': specs['func_s3_key'],
        },
        'Tags': {
            'app_name': settings.APPLICATION_NAME,
        },
        'Environment': {'Variables': get_app_env_dict()},
        'TracingConfig': {'Mode': 'Active' if settings.ENABLE_XRAY else 'PassThrough'},
        'Description': full_name,
    }
    if specs.get('layer_arn_list'):
        args.update({'Layers': specs['layer_arn_list']})
    if specs.get('tmp-size'):
        args.update({'EphemeralStorage': {'Size': int(specs['tmp-size'])}})
    if specs.get('vpc'):
        args.update({'VpcConfig': {
            'SubnetIds': specs['subnet-ids'],
            'SecurityGroupIds': specs['sec-group-ids'],
        }})
        print('\t==>NOTICE: WILL SET LAMBDA INSIDE OF VPC')
    resp = lambda_client.create_function(**args)
    resp.pop('ResponseMetadata', None)
    version = resp['Version']
    print(f'OK: CREATED LAMBDA FUNCTION {full_name} WITH VERSION [{version}]')
    return resp


def update_python_function(specs: dict, publish: bool = True) -> dict:
    # ==> PUBLISH CODE (NON-BLOCKING)
    print('PUBLISHING NEW VERSION OF LAMBDA FOR: {}'.format(specs['full_name']))
    args = {
        'Publish': publish,  # FYI: IMPORTANT
        'FunctionName': specs['full_name'],
        'S3Bucket': settings.AWS_LAMBDA_BUCKET,
        'S3Key': specs['func_s3_key'],
        'Architectures': [specs['arch']],
    }
    resp = lambda_client.update_function_code(**args)
    resp.pop('ResponseMetadata', None)
    waiter = lambda_client.get_waiter('function_updated')
    waiter.wait(FunctionName=specs['full_name'], WaiterConfig={'Delay': 2, 'MaxAttempts': 30})
    return resp


def update_function_config(specs: dict) -> dict:
    # ==> UPDATE CONFIG (BLOCKING)
    print('UPDATING LAMBDA CONFIG FOR: {}'.format(specs['full_name']))
    args = {
        'FunctionName': specs['full_name'],
        'Role': specs['role-arn'],
        'Handler': specs['handler'],
        'Runtime': specs['runtime'],  # REQUIRED
        'Timeout': specs['timeout'],
        'MemorySize': specs['mem'],
        'Environment': {'Variables': get_app_env_dict()},
        'TracingConfig': {'Mode': 'Active' if settings.ENABLE_XRAY else 'PassThrough'},
    }
    if specs.get('layer_arn_list'):
        args.update({'Layers': specs['layer_arn_list']})
    if specs.get('tmp-size'):
        args.update({'EphemeralStorage': {'Size': int(specs['tmp-size'])}})
    if specs.get('vpc'):
        args.update({'VpcConfig': {
            'SubnetIds': specs['subnet-ids'],
            'SecurityGroupIds': specs['sec-group-ids'],
        }})
        print('\t==>NOTICE: WILL SET LAMBDA INSIDE OF VPC')
    resp = lambda_client.update_function_configuration(**args)
    resp.pop('ResponseMetadata', None)
    print('DONE: UPDATED LAMBDA: {}'.format(specs['full_name']))
    return resp


def get_func_alias(func_name, alias) -> dict:
    response = {}
    try:
        response = lambda_client.get_alias(FunctionName=func_name, Name=alias)
        response.pop('ResponseMetadata', None)
    except Exception:
        pass
    return response


def create_func_alias(func_name, alias, version) -> dict:
    alias_version = None
    resp = lambda_client.create_alias(FunctionName=func_name, Name=alias, FunctionVersion=version)
    resp.pop('ResponseMetadata', None)
    alias_version = resp['FunctionVersion']
    print(f'DONE: REDIRECTED ALIAS {alias} TO VERSION: [{alias_version}]')
    return resp


def update_func_alias(func_name, alias, version) -> dict:
    resp = lambda_client.update_alias(FunctionName=func_name, Name=alias, FunctionVersion=version)
    resp.pop('ResponseMetadata', None)
    alias_version = resp['FunctionVersion']
    print(f'DONE: REDIRECTED ALIAS {alias} TO VERSION: [{alias_version}]')
    return resp


def get_function_concurrency(func_name: str, alias: str) -> int:
    count = 0
    args = {
        'FunctionName': func_name,
        'Qualifier': alias,
    }
    try:
        resp = lambda_client.get_provisioned_concurrency_config(**args)
        count = resp['AllocatedProvisionedConcurrentExecutions']
    except Exception:
        print(f'NO FUNCTION PROVISIONED CONCURRENCY FOUND FOR [{func_name}:{alias}]')
    return count


def set_function_preservation(specs: dict) -> dict:
    args = {
        'FunctionName': specs['full_name'],
        'Qualifier': specs['alias'],
        'ProvisionedConcurrentExecutions': specs['preserve'],
    }
    resp = lambda_client.put_provisioned_concurrency_config(**args)
    waiter = lambda_client.get_waiter('function_active')
    waiter.wait(FunctionName=specs['full_name'], WaiterConfig={'Delay': 2, 'MaxAttempts': 30})
    print('DONE: PUT PROVISIONED CONCURRENCY [{}] TO LAMBDA [{}]'.format(specs['preserve'], specs['name']))
    return resp


def remove_function_preservation(specs: dict) -> dict:
    args = {
        'FunctionName': specs['full_name'],
        'Qualifier': specs['alias'],
    }
    resp = lambda_client.delete_provisioned_concurrency_config(**args)
    waiter = lambda_client.get_waiter('function_active')
    waiter.wait(FunctionName=specs['full_name'], WaiterConfig={'Delay': 2, 'MaxAttempts': 30})
    print('DONE: REMOVED PROVISIONED CONCURRENCY FOR LAMBDA [{}]'.format(specs['name']))
    return resp


def get_func_triggers(func_name: str) -> list:
    resp = lambda_client.list_event_source_mappings(
        # EventSourceArn='string',
        FunctionName=func_name,
    )
    paginator = lambda_client.get_paginator('list_event_source_mappings')
    response_iterator = paginator.paginate(FunctionName=func_name)
    triggers = []
    for resp in response_iterator:
        triggers += resp['EventSourceMappings']
    # trigger = {'UUID': 'abc', 'EventSourceArn': 'abc', 'FunctionArn': 'abc'}
    return triggers


def add_func_trigger(source_specs: dict, lambda_specs: dict) -> dict:
    resp = lambda_client.create_event_source_mapping(
        EventSourceArn=source_specs['arn'],
        FunctionName=lambda_specs['full_name'],
        Enabled=True,
        # BatchSize=123,
        # MaximumBatchingWindowInSeconds=123,
        # ParallelizationFactor=123,
        # StartingPosition='TRIM_HORIZON'|'LATEST'|'AT_TIMESTAMP',
        # StartingPositionTimestamp=datetime(2015, 1, 1),
        # FilterCriteria={'Filters': [{'Pattern': 'string'}]},
        # MaximumRecordAgeInSeconds=123,
        # BisectBatchOnFunctionError=True|False,
        # MaximumRetryAttempts=3,
        # TumblingWindowInSeconds=123,
        # Topics=['string'],
        # Queues=['string'],
        # SelfManagedEventSource={'Endpoints': {'string': ['string']}},
        # FunctionResponseTypes=['ReportBatchItemFailures'],
        # DestinationConfig={'OnSuccess': {'Destination': 'string'}, 'OnFailure': {'Destination': 'string'}},
        # SourceAccessConfigurations=[{'Type': 'string', 'URI': 'string'}],
    )
    return resp


def deploy_func_trigger(source_specs: dict, lambda_specs: dict) -> bool:
    trigger_list = [t['EventSourceArn'] for t in get_func_triggers(lambda_specs['full_name'])]
    if source_specs['arn'] not in trigger_list:
        add_func_trigger(source_specs, lambda_specs)
    return True


def remove_function(func_name: str) -> dict:
    resp = lambda_client.delete_function(FunctionName=func_name)
    print(f'DONE: REMOVED FUNCTION: {func_name}')
    return resp


def clean_func_old_versions(func_versions: list) -> list:
    fmap = {x['Version']: x for x in func_versions if is_int(x.get('Version'))}
    remove_vers = sorted(fmap.keys())[:-settings.LAMBDA_MAX_VERSION]
    for version in remove_vers:
        item = fmap[version]
        func_name = item['FunctionName']
        try:
            lambda_client.delete_function(FunctionName=func_name, Qualifier=version)
            print(f'DONE: REMOVED FUNCTION VERSION: {version}')
        except Exception as e:
            logger.exception(e)
            print(f'FAILED TO REMOVE FUNCITON VERSION: [{func_name}:{version}], {e}')
    return remove_vers
