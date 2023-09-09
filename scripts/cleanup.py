import os
import logging

from utils import common_utils
from utils import lambda_utils
from utils import http_api_utils
from utils import rest_api_utils
from utils import stepfunc_utils

import settings
logger = logging.getLogger(__name__)


class CleanUp:
    def __init__(self):
        self.template = common_utils.get_template()
        self.repo_path = self.template['info']['repo_path']

    def clean(self):
        print('OK.')

    def delete_layers(self):
        pass

    def delete_lambdas(self):
        for specs in self.template['resources']['lambda']:
            if any([
                settings.DEPLOY_TYPE not in ['full', 'lambda'],
                settings.DEPLOY_TYPE == 'lambda' and settings.DEPLOY_TARGET != specs['name'],
            ]):
                print('SKIP DEPLOYMENT FOR LAMBDA [{}]'.format(specs['name']))
                continue
            full_name = lambda_utils.get_func_full_name(specs['name'])
            try:
                lambda_utils.remove_function(full_name)
            except Exception as e:
                logger.exception(e)
        return

    def delete_http_api(self):
        full_name = http_api_utils.get_api_full_name(self.template['resources']['http-api']['name'])
        api = http_api_utils.get_api_by_name(full_name)
        if api:
            api_id = api['ApiId']
            try:
                http_api_utils.remove_api(api_id)
            except Exception as e:
                logger.exception(e)
        return

    def delete_rest_api(self):
        full_name = rest_api_utils.get_api_full_name(self.template['resources']['rest-api']['name'])
        api = rest_api_utils.get_api_by_name(full_name)
        if api:
            api_id = api['ApiId']
            try:
                rest_api_utils.remove_api(api_id)
            except Exception as e:
                logger.exception(e)
        return

    def delete_state_machines(self):
        for specs in self.template['resources']['stepfunc']:
            arn = stepfunc_utils.get_stepfunc_arn_by_name(specs['name'])
            try:
                stepfunc_utils.remove_state_machine(arn)
            except Exception as e:
                logger.exception(e)

    def delete_schedules(self):
        pass

    def delete_policies(self):
        pass

    def delete_roles(self):
        pass


def main():
    c = CleanUp()
    c.clean()


if __name__ == '__main__':
    main()

