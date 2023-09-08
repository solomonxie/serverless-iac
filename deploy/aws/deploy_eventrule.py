import logging

from utils import event_utils
from utils import common_utils

logger = logging.getLogger(__name__)


class EventRuleDeployHelper:
    def __init__(self):
        self.template = common_utils.get_template()

    def deploy(self):
        for specs in self.template['resources'].get('eventrule') or []:
            if specs.get('no-deploy') is True:
                print('SKIP DEPLOYMENT FOR SCHEDULE [{}]'.format(specs['name']))
                continue
            specs = render_specs(specs)
            event_utils.set_event_rule(specs['rule-name'], specs['filter'], role_arn=specs['ro-arn'])
            event_utils.set_target(specs['rule-name'], specs['target-arn'], role_arn=specs['ro-arn'])
        return


def render_specs(specs: dict) -> dict:
    return specs


def main():
    h = EventRuleDeployHelper()
    h.deploy()
    print('[ OK ]')


if __name__ == '__main__':
    main()
