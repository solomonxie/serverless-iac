import os
import logging

from aws.utils import common_utils
from aws.utils import rest_api_utils
from aws.utils import lambda_utils
from aws.utils import stepfunc_utils

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
        self.specs = rest_api_utils.render_specs(self.template['services']['rest-api'])
        self.swagger = rest_api_utils.render_swagger(swagger_path, self.specs)
        remote = rest_api_utils.get_api_by_name(self.specs['full-name'])
        self.api_id = remote.get('id')

    def deploy(self):
        if not self.template['services'].get('rest-api'):
            print('SKIP DEPLOYMENT OF REST API FOR NOT FOUND DEFINITION')
            return
        if self.specs.get('no-deploy') is True:
            print('SKIP DEPLOYMENT FOR [REST-API]')
            return
        self.deploy_api()
        self.deploy_integrations()
        self.deploy_stages()
        print('OK.')
        return True

    def deploy_api(self):
        if not self.api_id:
            info = rest_api_utils.create_api(self.specs['full-name'], self.specs)
            self.api_id = info['id']
        rest_api_utils.import_routes(self.api_id, self.swagger)
        return True

    def deploy_integrations(self):
        if not self.api_id:
            raise RuntimeError('MUST PROVIDE [api_id] FOR DEPLOYING INTEGRATION.')
        remote_route_map = rest_api_utils.get_api_route_map(self.api_id)
        local_route_map = common_utils.parse_swagger_route_map(self.swagger['paths'])
        for (method, route), specs in remote_route_map.items():
            route_info = local_route_map[(method.upper(), route)]
            route_id = specs['id']
            if route_info.get('x-lambda-name'):
                self._integrate_lambda(specs['id'], method, route, route_info['x-lambda-name'])
            elif route_info.get('x-stepfunc-name'):
                # FIXME-->
                self._integrate_stepfunc(specs['id'], method, route, route_info['x-stepfunc-name'])
            elif route_info.get('x-s3-target'):
                # FIXME-->
                self._integrate_s3(specs['id'], method, route, route_info['x-s3-target'])
            else:
                print(f'NO INTEGRATION FOUND FOR [{method} {route}]')
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
        # FIXME: NOT YET WORKING
        itg = rest_api_utils.get_api_integration(self.api_id, route_id, method)
        if not itg:
            target_arn = f's3://{s3_key}'
            itg = rest_api_utils.integrate_api_with_s3(self.api_id, route_id, method, target_arn)
        return

    def deploy_stages(self):
        dpl = rest_api_utils.get_api_latest_deployment(self.api_id)
        if not dpl:
            dpl = rest_api_utils.create_api_deployment(self.api_id)
        dpl_id = dpl['id']
        stages = rest_api_utils.get_api_stages(self.api_id)
        if settings.STAGE_NAME not in stages:
            rest_api_utils.create_api_stage(self.api_id, settings.STAGE_NAME, dpl_id)
        return True


def main():
    h = RestApiDeployHelper()
    h.deploy()


if __name__ == '__main__':
    main()
