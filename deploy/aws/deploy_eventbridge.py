import logging

from utils import iam_utils
from utils import event_utils
from utils import common_utils

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
            # DEPLOY IAM ROLE/POLICY
            if specs['target-type'] == 'stepfunc':
                iam_utils.deploy_policy(specs['po-name'], specs['po-path'])
                iam_utils.deploy_role(specs['ro-name'], specs['po-name'], 'eventbridge')
            # SET RULE
            if specs['event-type'] == 'cron':
                event_utils.set_cron(specs['rule-name'], specs['cron'], role_arn=specs['ro-arn'])
            elif specs['event-type'] == 'event-filter':
                event_utils.set_event_filter(specs['rule-name'], specs['filter'], role_arn=specs['ro-arn'])
            # SET TARGET
            event_utils.set_target(specs['rule-name'], specs['target-arn'], role_arn=specs['ro-arn'])
        return


def main():
    h = ScheduleDeployHelper()
    h.deploy()
    print('[ OK ]')


if __name__ == '__main__':
    main()
