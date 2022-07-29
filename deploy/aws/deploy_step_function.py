import logging

import settings
from utils import iam_utils
from utils import common_utils
from utils import stepfunc_utils
from utils import cloudwatch_utils

logger = logging.getLogger(__name__)


class StepFuncDeployHelper:
    def __init__(self):
        self.template = common_utils.get_template()
        self.repo_path = self.template['info']['repo_path']

    def deploy(self):
        for specs in self.template['resources'].get('stepfunc') or []:
            if any([
                settings.DEPLOY_TYPE not in ['full', 'stepfunc'],
                settings.DEPLOY_TYPE == 'stepfunc' and settings.DEPLOY_TARGET != specs['name'],
            ]):
                print('SKIP DEPLOYMENT FOR STATE MACHINE [{}]'.format(specs['name']))
                continue
            specs = stepfunc_utils.render_specs(specs)
            # DEPLOY LOG GROUP
            if not specs['log_group_info']:
                cloudwatch_utils.create_log_group(specs['log_group_name'])
                specs['log_group_info'] = cloudwatch_utils.get_log_group(specs['log_group_name'])
                specs['log_group_arn'] = specs['log_group_info'].get('arn')
            # DEPLOY IAM/POLICY
            iam_specs = {}
            iam_utils.deploy_policy(specs['po_name'], specs['po_path'], **iam_specs)
            iam_utils.deploy_role(specs['ro_name'], specs['po_name'], 'stepfunc')
            print('DONE: DEPLOYED STEPFUNC IAM ROLE/POLICY FOR [{}]'.format(specs['name']))
            # DEPLOY STATE MACHINE
            machine = specs.get('machine')
            if not machine:
                specs['machine'] = stepfunc_utils.create_stepfunc(specs)
            else:
                specs['machine'] = stepfunc_utils.update_stepfunc(machine['stateMachineArn'], specs)
        return


def main():
    h = StepFuncDeployHelper()
    h.deploy()
    print('[ OK ]')


if __name__ == '__main__':
    main()
