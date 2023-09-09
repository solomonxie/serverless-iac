import json
import logging

from utils import iam_utils
from utils import event_utils
from utils import common_utils
from utils import lambda_utils
from utils import stepfunc_utils

import settings

logger = logging.getLogger(__name__)


class ScheduleDeployHelper:
    def __init__(self):
        self.template = common_utils.get_template()

    def deploy(self):
        __import__('pudb').set_trace()
        for specs in self.template['resources'].get('schedule') or []:
            if specs.get('no-deploy') is True:
                print('SKIP DEPLOYMENT FOR SCHEDULE [{}]'.format(specs['name']))
                continue
            specs = render_specs(specs)
            event_utils.set_event_schedule(specs)
            event_utils.set_target(specs)
        return


def render_specs(specs: dict) -> dict:
    specs['rule-name'] = event_utils.get_rule_full_name(specs['name'])
    specs['role-arn'] = iam_utils.get_role_arn_by_name(specs['role'])
    if specs['target-type'] == 'lambda':
        specs['target-arn'] = lambda_utils.get_func_arn_by_name(specs['target-name'])
    elif specs['target-type'] == 'stepfunc':
        specs['target-arn'] = stepfunc_utils.get_stepfunc_arn_by_name(specs['target-name'])
    else:
        raise NotImplementedError('TARGET TYPE [{}] SUPPORTED'.format(specs.get('target-type')))
    # SKIP DEPLOY
    if any([
        settings.DEPLOY_TYPE not in ['full', 'schedule'],
        settings.DEPLOY_TYPE == 'schedule' and settings.DEPLOY_TARGET != specs['name'],
    ]):
        specs['no-deploy'] = True
    return specs


def main():
    h = ScheduleDeployHelper()
    h.deploy()
    print('[ OK ]')


if __name__ == '__main__':
    main()
