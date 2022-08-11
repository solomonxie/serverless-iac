import os
import logging

from aws.utils import iam_utils
from aws.utils import common_utils
from aws.utils import lambda_utils

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
            specs = lambda_utils.render_specs(specs)
            print('==>DEPLOYING LAMBDA {}'.format(specs['name']))
            full_name = specs['full_name']
            if specs.get('no-deploy') is True:
                print('SKIP DEPLOYMENT FOR LAMBDA [{}]'.format(specs['name']))
                continue
            # DEPLOY LAYERS
            for layer in specs.get('layers') or []:
                if layer['type'] == 'python-requirements':
                    path = os.path.join(self.repo_path, layer['manifest'])
                    sha = lambda_utils.build_python_package_layer(path)
                    layer['arn'] = lambda_utils.deploy_python_package_layer(sha, specs['runtime'], specs['arch'])
                elif layer['type'] == 'nodejs-package':
                    pass  # TODO: SUPPORT MORE LANGUAGES
            specs['layer_arn_list'] = [x['arn'] for x in specs.get('layers', [])]
            # DEPLOY IAM ROLE/POLICY
            iam_specs = {}
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
            # UPDATE ALIAS POINTING TO THE LATEST VERSION
            ver = specs.get('latest_version') or specs['remote'].get('Version') or '$LATEST'
            alias_version = specs['alias_info'].get('FunctionVersion')
            if not alias_version:
                specs['alias_info'] = lambda_utils.create_func_alias(full_name, settings.FUNC_ALIAS, ver)
            elif alias_version != ver:
                specs['alias_info'] = lambda_utils.update_func_alias(full_name, settings.FUNC_ALIAS, ver)
            specs['alias_arn'] = specs['alias_info']['AliasArn']
            specs['latest_version'] = specs['alias_info']['FunctionVersion']
            # SET PROVISIONED CONCURRENCY
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
            print('REMOVING LAMBDA OLDER VERSIONS: {}'.format(specs['full_name']))
            lambda_utils.clean_func_old_versions(specs.get('versions') or [])


def main():
    h = LambdaDeployHelper()
    h.deploy()


if __name__ == '__main__':
    main()
