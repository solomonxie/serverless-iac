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
        for specs in self.template['resources'].get('schedule') or []:
            if specs.get('no-deploy') is True:
                print('SKIP DEPLOYMENT FOR SCHEDULE [{}]'.format(specs['name']))
                continue
            specs = event_utils.render_specs(specs)
            event_utils.set_event_schedule(specs['name'], specs['cron'], role_arn=specs['ro-arn'])
            event_utils.set_target(specs['rule-name'], specs['target-arn'], role_arn=specs['ro-arn'])
        return


def render_specs(specs: dict) -> dict:
    specs['rule-name'] = event_utils.get_rule_full_name(specs['name'])
    if specs.get('cron'):
        specs['event-type'] = 'cron'
    elif specs.get('event-filter-path'):
        specs['event-type'] = 'event-filter'
        specs['filter'] = json.dumps(common_utils.render_json(specs['event-filter-path']))
    else:
        raise NotImplementedError('PLEASE SPECIFY EVENT TYPE')
    if specs['target-type'] == 'lambda':
        func_name = lambda_utils.get_func_full_name(specs['target-name'])
        specs['target-arn'] = lambda_utils.get_func_arn_by_name(func_name)
        specs['ro-arn'] = ''
    elif specs['target-type'] == 'stepfunc':
        sfn_name = stepfunc_utils.get_stepfunc_full_name(specs['target-name'])
        specs['target-arn'] = stepfunc_utils.get_stepfunc_arn_by_name(sfn_name)
        specs['ro-name'] = iam_utils.get_role_full_name('event-' + specs['name'])
        specs['ro-arn'] = iam_utils.get_role_arn_by_name(specs['ro-name'])
        specs['po-name'] = iam_utils.get_policy_full_name('event-' + specs['name'])
        specs['po-path'] = './iam/iam-policy-eventbridge-call-stepfunc.json'
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
