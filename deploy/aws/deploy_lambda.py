import os
import logging

from utils import iam_utils
from utils import common_utils
from utils import lambda_utils
from utils import lambdalayer_utils

import settings
logger = logging.getLogger(__name__)


class LambdaDeployHelper:
    def __init__(self):
        self.template = common_utils.get_template()
        self.repo_path = self.template['info']['repo_path']

    def deploy(self):
        self.deploy_functions()
        self.clear()
        print('[ OK ]')

    def deploy_functions(self):
        for specs in self.template['resources'].get('lambda') or []:
            specs = render_specs(specs)
            print('==>DEPLOYING LAMBDA {}'.format(specs['name']))
            if specs.get('no-deploy') is True:
                print('SKIP DEPLOYMENT FOR LAMBDA [{}]'.format(specs['name']))
                continue
            # DEPLOY IAM ROLE/POLICY
            iam_specs = {}
            __import__('pudb').set_trace()
            iam_utils.deploy_policy(specs['po-name'], specs['po-path'], **iam_specs)
            iam_utils.deploy_role(specs['ro-name'], specs['po-name'], 'lambda')
            print('DONE: DEPLOYED LAMBDA IAM ROLE/POLICY FOR [{}]'.format(specs['name']))
            # DEPLOY FUNCTION
            lambda_utils.compile_and_upload_python_code(self.repo_path, specs)
            # CREATE FUNCTION
            if not specs['remote']:
                assert 'python' in specs['runtime']  # TODO: SUPPORT MORE RUNTIMES
                specs['remote'] = lambda_utils.create_python_function(specs)
            else:
                # lambda_utils.update_python_function(specs, False)  # OPTIONAL: UPDATE $LATEST FOR GUI DEBUG
                specs['remote'] = lambda_utils.update_python_function(specs)
                if settings.ENABLE_LAMBDA_CONFIG_UPDATE:
                    # FIXME: THIS WILL CAUSE FUNCTION PENDING
                    specs['remote'] = lambda_utils.update_function_config(specs)
            # SET PROVISIONED CONCURRENCY
            if specs.get('preserve'):
                lambda_utils.set_function_preservation(specs)
            else:
                lambda_utils.remove_function_preservation(specs)
            # UPDATE ALIAS POINTING TO THE LATEST VERSION
            ver = specs.get('latest_version') or specs['remote'].get('Version') or '$LATEST'
            alias_version = specs['alias_info'].get('FunctionVersion')
            if not alias_version:
                specs['alias_info'] = lambda_utils.create_func_alias(specs['full_name'], settings.FUNC_ALIAS, ver)
            elif alias_version != ver:
                specs['alias_info'] = lambda_utils.update_func_alias(specs['full_name'], settings.FUNC_ALIAS, ver)
            specs['alias_arn'] = specs['alias_info']['AliasArn']
            specs['latest_version'] = specs['alias_info']['FunctionVersion']
            print('=' * 60)
        return

    def clear(self):
        if not settings.LOCAL_REPO_PATH:
            assert 0 == os.system(f'rm -rdf {self.repo_path} ||true')
        for specs in self.template['resources']['lambda']:
            print('REMOVING LAMBDA OLDER VERSIONS: {}'.format(specs['full_name']))
            lambda_utils.clean_func_old_versions(specs.get('versions') or [])


def render_specs(specs: dict) -> dict:
    specs['full_name'] = lambda_utils.get_func_full_name(specs['name'])
    specs['func_s3_key'] = lambda_utils.get_func_s3_key_by_name(specs['full_name'])
    specs['timeout'] = specs.get('timeout') or 60
    specs['arch'] = specs.get('arch') or 'x86_64'
    specs['mem'] = specs.get('mem') or 128
    specs['ro-name'] = iam_utils.get_role_full_name(specs['name'])
    specs['role-arn'] = iam_utils.get_role_arn_by_name(specs['ro-name'])
    specs['po-name'] = iam_utils.get_policy_full_name('lambda-general')
    specs['alias'] = settings.FUNC_ALIAS
    specs['preserve'] = int(specs.get('preserve') or 0)
    # Layers
    specs['layer_arn_list'] = []
    __import__('pudb').set_trace()
    for layer in specs.get('layers') or []:
        layer_name = lambdalayer_utils.get_layer_full_name(layer['name'])
        layer_info = lambdalayer_utils.get_latest_layer_by_name(layer_name)
        assert layer_info, f'Layer [{layer_name}] does not exist'
        layer_latest_arn = layer_info['LayerVersionArn']
        specs['layer_arn_list'].append(layer_latest_arn)
    [x['arn'] for x in specs.get('layers', [])]
    # VPC
    if settings.ENABLE_VPC and specs.get('vpc'):
        specs['subnet-ids'] = str(specs['vpc']['subnet-ids']).split(',')
        specs['sec-group-ids'] = str(specs['vpc']['sec-group-ids']).split(',')
        assert all([specs['subnet-ids'], specs['sec-group-ids']]), 'MISSING SUBNET & SECURITY-GROUP FOR VPC'
        specs['po-path'] = './iam/iam-policy-lambda-execute-vpc.json'
    else:
        specs['subnet-ids'] = []
        specs['sec-group-ids'] = []
        specs['vpc'] = {}
        specs['po-path'] = './iam/iam-policy-lambda-execute.json'
    # LIVE FETCH
    specs['remote'] = lambda_utils.get_func_info_by_name(specs['full_name'])
    latest = lambda_utils.get_func_latest_version(specs['full_name'])
    specs['latest_version'] = latest.get('Version') or specs['remote'].get('Version')
    specs['alias_info'] = lambda_utils.get_func_alias(specs['full_name'], specs['alias'])
    # SKIP DEPLOY
    if any([
        settings.DEPLOY_TYPE not in ['full', 'lambda'],
        settings.DEPLOY_TYPE == 'lambda' and settings.DEPLOY_TARGET != specs['name'],
    ]):
        print('SKIP DEPLOYMENT FOR LAMBDA [{}]'.format(specs['name']))
        specs['no-deploy'] = True
    return specs


def main():
    h = LambdaDeployHelper()
    h.deploy()


if __name__ == '__main__':
    main()
