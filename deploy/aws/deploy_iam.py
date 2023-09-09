import os
import logging

from utils import iam_utils
from utils import common_utils
logger = logging.getLogger(__name__)


class IAMDeployHelper:
    def __init__(self):
        self.template = common_utils.get_template()
        self.repo_path = self.template['info']['repo_path']

    def deploy(self):
        self.deploy_policies()
        self.deploy_roles()
        self.clear()
        print('[ OK ]')

    def deploy_policies(self):
        for specs in self.template['resources'].get('iam', {}).get('policy') or []:
            specs = render_policy_specs(specs)
            print('==>DEPLOYING POLICY {}'.format(specs['name']))
            path = os.path.join(self.repo_path, specs['path'])
            iam_utils.deploy_policy(specs['name'], path, specs.get('tags'))

    def deploy_roles(self):
        for specs in self.template['resources'].get('iam', {}).get('role') or []:
            specs = render_role_specs(specs)
            print('==>DEPLOYING ROLE {}'.format(specs['name']))
            iam_utils.deploy_role(specs['name'], specs['trust-entity'], specs.get('tags'))
            for po_name in specs.get('policies') or []:
                iam_utils.attach_policy_to_role(specs['name'], po_name)

    def clear(self):
        pass


def render_role_specs(specs: dict) -> dict:
    return specs


def render_policy_specs(specs: dict) -> dict:
    return specs


def main():
    h = IAMDeployHelper()
    h.deploy()


if __name__ == '__main__':
    main()
