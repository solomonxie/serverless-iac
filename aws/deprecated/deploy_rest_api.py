import os
import logging

from utils import common_utils
from utils import lambda_utils
from utils import rest_api_utils
from utils import stepfunc_utils

import settings
logger = logging.getLogger(__name__)


class RestApiDeployHelper:
    def __init__(self):
        self.template = common_utils.get_template()
        if not self.template['services'].get('rest-api'):
            return
        repo_path = self.template['info']['repo_path']
        swagger_path = os.path.realpath(os.path.join(
            os.path.expanduser(repo_path),
            self.template['services']['rest-api']['swagger-path']
        ))
        self.swagger = common_utils.render_yaml(swagger_path)
        self.route_map = common_utils.parse_swagger_route_map(self.swagger['paths'])
        self.api_id = None

    def deploy(self):
        if not self.template['services'].get('rest-api'):
            print('SKIP DEPLOYMENT OF REST API FOR NOT FOUND DEFINITION')
            return
        api_name = self.template['services']['rest-api']['name']
        if any([
            settings.DEPLOY_TYPE not in ['full', 'restapi'],
            settings.DEPLOY_TYPE == 'restapi' and settings.DEPLOY_TARGET != api_name,
        ]):
            print('SKIP DEPLOYMENT FOR [REST-API]')
            return
        self.deploy_api()
        self.deploy_integrations()
        self.deploy_stages()
        print('OK.')

    def deploy_api(self):
        specs = self.template['services']['rest-api']
        full_name = rest_api_utils.get_api_full_name(specs['name'])
        api = rest_api_utils.get_api_by_name(full_name)
        if not api:
            api = rest_api_utils.create_api(full_name, specs)
        self.api_id = api['id']
        self.swagger['info']['title'] = full_name  # REQUIRED: title REPRESENTS "API-NAME"
        rest_api_utils.import_routes(self.api_id, self.swagger)
        return

    def deploy_integrations(self):
        if not self.api_id:
            raise RuntimeError('MUST PROVIDE [api_id] FOR DEPLOYING INTEGRATION.')
        route_map = rest_api_utils.get_api_route_map(self.api_id)
        for (method, route), specs in route_map.items():
            route_key = ' '.join([method.upper(), route])
            route_info = self.route_map[route_key]
            route_id = specs['id']
            if route_info.get('x-lambda-name'):
                self._integrate_lambda(specs['id'], method, route, route_info['x-lambda-name'])
            elif route_info.get('x-stepfunc-name'):
                self._integrate_stepfunc(specs['id'], method, route, route_info['x-stepfunc-name'])
            elif route_info.get('x-s3-target'):
                __import__('pudb').set_trace()
                self._integrate_s3(specs['id'], method, route, route_info['x-s3-target'])
            # UPDATE ROUTE AUTH
            rest_api_utils.update_route_authorizor(self.api_id, route_id, method, route_info.get('auth'))
        return

    def _integrate_lambda(self, route_id: str, method: str, route: str, name: str):
        target_arn = lambda_utils.get_func_arn_by_name(name)
        itg = rest_api_utils.get_api_integration(self.api_id, route_id, method)
        # rest_api_utils.delete_api_integration(self.api_id, specs['id'], method)
        if not itg:
            itg = rest_api_utils.integrate_api_with_lambda(self.api_id, route_id, target_arn, method)
        # UPDATE INVOKE POLICY (ONLY ALLOW ONE ROUTE PER LAMBDA, EXCLUSIVELY)
        caller_arn = lambda_utils.get_lambda_invoke_caller_arn(self.api_id, route)
        po = lambda_utils.get_lambda_invoke_policy(target_arn, caller_arn)
        if not po:
            po = lambda_utils.create_lambda_invoke_policy(target_arn, caller_arn)
        return itg

    def _integrate_stepfunc(self, route_id: str, method: str, route: str, name: str):
        # FIXME: NOT YET WORKING
        target_arn = stepfunc_utils.get_stepfunc_arn_by_name(name)
        itg = rest_api_utils.get_api_integration(self.api_id, route_id, method)
        if not itg:
            itg = rest_api_utils.integrate_api_with_stepfunc(self.api_id, route_id, target_arn, method)
        # DEPLOY IAM ROLE/POLICY
        # iam_utils.deploy_policy(specs['po-name'], specs['po-path'])
        # iam_utils.deploy_role(specs['ro-name'], specs['po-name'], 'lambda')
        # print('DONE: DEPLOYED LAMBDA IAM ROLE/POLICY FOR [{}]'.format(specs['name']))
        return itg

    def _integrate_s3(self, route_id: str, method: str, route: str, s3_key: str) -> dict:
        itg = rest_api_utils.get_api_integration(self.api_id, route_id, method)
        if not itg:
            target_arn = f's3://{s3_key}'
            itg = rest_api_utils.integrate_api_with_s3(self.api_id, route_id, method, target_arn)
        return

    def deploy_stages(self):
        if not self.api_id:
            raise RuntimeError('MUST PROVIDE [api_id] FOR DEPLOYING STAGES.')
        stages = rest_api_utils.get_api_stages(self.api_id)
        dpl = rest_api_utils.get_api_latest_deployment(self.api_id)
        if not dpl:
            dpl = rest_api_utils.create_api_deployment(self.api_id)
        dpl_id = dpl['id']
        if settings.STAGE_NAME not in stages:
            rest_api_utils.create_api_stage(self.api_id, settings.STAGE_NAME, dpl_id)
        return


def main():
    h = RestApiDeployHelper()
    h.deploy()


if __name__ == '__main__':
    main()
