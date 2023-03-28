import logging

from aws.utils import iam_utils
from aws.utils import event_utils
from aws.utils import common_utils
from aws.utils import lambda_utils
from aws.utils import stepfunc_utils
from aws.utils import rest_api_utils

logger = logging.getLogger(__name__)


class DestroyHelper:
    def __init__(self):
        self.template = common_utils.get_template()
        self.repo_path = self.template['info']['repo_path']

    def remove(self):
        # self.remove_lambda()
        # self.remove_iam()
        # self.remove_stepfunc()
        # self.remove_rest_api()
        self.remove_schedule()
        print('[ OK ]')

    def remove_lambda(self):
        for specs in self.template['resources'].get('lambda') or []:
            specs = lambda_utils.render_specs(specs)
            try:
                lambda_utils.clean_func_old_versions(specs.get('versions') or [])
                lambda_utils.remove_function(specs['full_name'])
            except Exception as e:
                logger.warning(e)
        return True

    def remove_iam(self):
        # TODO: REMOVE ATTACHED POLICIES OF EACH ROLE
        prefix = common_utils.get_name_prefix()
        po_list = iam_utils.list_policies_by_prefix(prefix)
        removed = iam_utils.remove_policies(po_list)
        print(f'REMOVED {len(removed)} POLICIES')
        ro_list = iam_utils.list_roles_by_prefix(prefix)
        removed = iam_utils.remove_roles(ro_list)
        print(f'REMOVED {len(removed)} ROLES')
        return True

    def remove_stepfunc(self):
        for specs in self.template['resources'].get('stepfunc') or []:
            specs = stepfunc_utils.render_specs(specs)
            if specs['arn']:
                stepfunc_utils.remove_state_machine(specs['arn'])
        return True

    def remove_rest_api(self):
        if self.template['services'].get('rest-api'):
            specs = rest_api_utils.render_specs(self.template['services']['rest-api'])
            api = rest_api_utils.get_api_by_name(specs['full-name'])
            if api:
                rest_api_utils.remove_api(api['id'])
        return True

    def remove_schedule(self):
        for specs in self.template['resources'].get('schedule') or []:
            rule_name = event_utils.get_rule_full_name(specs['name'])
            event_utils.remove_targets(rule_name)
            rule = event_utils.get_rule(rule_name)
            if rule:
                event_utils.remove_rule(rule_name)


def main():
    h = DestroyHelper()
    h.remove()


if __name__ == '__main__':
    main()
