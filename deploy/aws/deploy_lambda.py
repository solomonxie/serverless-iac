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
        self.upload_code()
        self.deploy_functions()
        self.clear()
        print('[ OK ]')

    def upload_code(self):
        ignores = self.template['services']['lambda'].get('upload-ignore') or []
        lambda_utils.upload_code_to_s3(self.repo_path, ignores)

    def deploy_functions(self):
        __import__('pudb').set_trace()
        for specs in self.template['resources'].get('lambda') or []:
            specs = render_specs(specs)
            print('==>DEPLOYING LAMBDA {}'.format(specs['name']))
            if specs.get('no-deploy') is True:
                print('SKIP DEPLOYMENT FOR LAMBDA [{}]'.format(specs['name']))
                continue
            # CREATE FUNCTION
            if not specs['remote']:
                assert 'python' in specs['runtime']  # TODO: SUPPORT MORE RUNTIMES
                specs['remote'] = lambda_utils.create_lambda_function(specs)
            else:
                # lambda_utils.update_python_function(specs, False)  # OPTIONAL: UPDATE $LATEST FOR GUI DEBUG
                specs['remote'] = lambda_utils.update_lambda_function(specs)
                specs['remote'] = lambda_utils.update_function_config(specs)
            # UPDATE ALIAS POINTING TO THE LATEST VERSION
            ver = specs.get('latest_version') or specs['remote'].get('Version') or '$LATEST'
            alias_version = specs['alias_info'].get('FunctionVersion')
            if not alias_version:
                specs['alias_info'] = lambda_utils.create_func_alias(specs['name'], settings.FUNC_ALIAS, ver)
            elif alias_version != ver:
                specs['alias_info'] = lambda_utils.update_func_alias(specs['name'], settings.FUNC_ALIAS, ver)
            specs['alias_arn'] = specs['alias_info']['AliasArn']
            specs['latest_version'] = specs['alias_info']['FunctionVersion']
            # SET Unreserved CONCURRENCY
            lambda_utils.set_lambda_concurrency(specs['name'], specs.get('concurrency'))
            # SET PROVISIONED CONCURRENCY (requires func-alias)
            if specs.get('preserve'):
                lambda_utils.set_function_preservation(specs)
            else:
                lambda_utils.remove_function_preservation(specs)
            print('=' * 60)
        return

    def clear(self):
        if not settings.LOCAL_REPO_PATH:
            assert 0 == os.system(f'rm -rdf {self.repo_path} ||true')
        for specs in self.template['resources']['lambda']:
            print('REMOVING LAMBDA OLDER VERSIONS: {}'.format(specs['name']))
            lambda_utils.clean_func_old_versions(specs.get('versions') or [])


def render_specs(specs: dict) -> dict:
    specs['code_s3_key'] = lambda_utils.get_code_s3_key()
    specs['timeout'] = specs.get('timeout') or 60
    specs['arch'] = specs.get('arch') or 'x86_64'
    specs['mem'] = specs.get('mem') or 128
    specs['role-arn'] = iam_utils.get_role_arn_by_name(specs['role'])
    specs['alias'] = settings.FUNC_ALIAS
    specs['preserve'] = int(specs.get('preserve') or 0)
    # Layers
    specs['layer_arn_list'] = []
    for layer in specs.get('layers') or []:
        layer_info = lambdalayer_utils.get_latest_layer_by_name(layer['name'])
        assert layer_info, 'Layer [{}] does not exist'.format(layer['name'])
        layer_latest_arn = layer_info['LayerVersionArn']
        specs['layer_arn_list'].append(layer_latest_arn)
    # Environments
    specs['env'] = {k: str(v) for k, v in specs.get('env', {}).items()}
    specs['tags'] = {k: str(v) for k, v in specs.get('tags', {}).items()}
    # LIVE FETCH
    specs['remote'] = lambda_utils.get_func_info_by_name(specs['name'])
    latest = lambda_utils.get_func_latest_version(specs['name'])
    specs['latest_version'] = latest.get('Version') or specs['remote'].get('Version')
    specs['alias_info'] = lambda_utils.get_func_alias(specs['name'], specs['alias'])
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
