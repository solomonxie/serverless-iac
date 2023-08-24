import os
import logging

from utils import common_utils
from utils import lambdalayer_utils
from utils.common_utils import file_to_sha

logger = logging.getLogger(__name__)


class LambdaLayerDeployHelper:
    def __init__(self):
        self.template = common_utils.get_template()
        self.repo_path = self.template['info']['repo_path']

    def deploy(self):
        self.deploy_layers()
        self.clear()
        print('[ OK ]')

    def deploy_layers(self):
        for specs in self.template['services'].get('lambdalayer') or []:
            specs = render_specs(specs, self.repo_path)
            print('==>DEPLOYING LAMBDA LAYER {}'.format(specs['name']))
            if specs['type'] == 'nodejs_packages':
                # TODO: SUPPORT MORE LANGUAGES
                pass
            elif specs['type'] == 'py_requirements':
                lambdalayer_utils.build_layer_py_requirements(specs)
                lambdalayer_utils.deploy_python_package_layer(specs)
        return

    def clear(self):
        pass


def render_specs(specs: dict, repo_path: str) -> dict:
    assert specs['runtime'] in ['python3.7', 'python3.8', 'python3.9']
    specs['runtime'] = specs['runtime']
    assert specs['arch'] in ['x86_64', 'arm64']
    specs['arn'] = lambdalayer_utils.get_layer_arn(specs['name'])
    specs['path'] = os.path.join(repo_path, specs['manifest'])
    specs['sha'] = file_to_sha(os.path.realpath(os.path.expanduser(specs['path'])))
    specs['layer_s3_key'] = lambdalayer_utils.get_layer_s3_key(specs['name'])
    specs['sha_s3_key'] = specs['layer_s3_key'] + '.sha'
    return specs


def main():
    h = LambdaLayerDeployHelper()
    h.deploy()


if __name__ == '__main__':
    main()
