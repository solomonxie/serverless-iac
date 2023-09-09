import os
import logging

import settings
from utils import common_utils
from utils import lambda_utils
from utils import http_api_utils
from utils import cloudwatch_utils

logger = logging.getLogger(__name__)


class DeployHelper:
    def __init__(self):
        self.template = common_utils.get_template()
        repo_path = self.template['info']['repo_path']
        swagger_path = os.path.realpath(os.path.join(
            os.path.expanduser(repo_path),
            self.template['resources']['http-api']['swagger-path']
        ))
        self.swagger = common_utils.render_yaml(swagger_path)
        self.route_map = common_utils.parse_swagger_route_map(self.swagger['paths'])
        self.api_id = None
        self.api_name = self.template['resources']['http-api']['name']
        self.api_full_name = http_api_utils.get_api_full_name(self.api_name)

    def deploy(self):
        if any([
            settings.DEPLOY_TYPE not in ['full', 'httpapi'],
            settings.DEPLOY_TYPE == 'httpapi' and settings.DEPLOY_TARGET != self.api_name,
        ]):
            print('SKIP DEPLOYMENT FOR [HTTP-API]')
            return
        self.deploy_api()
        self.deploy_routes()
        self.deploy_throttling()
        # self.delete_app()
        print('OK')

    def deploy_api(self):
        if not self.template['resources'].get('http-api'):
            print('SKIP DEPLOYMENT OF HTTP API FOR NOT FOUND DEFINITION')
            return
        specs = self.template['resources']['http-api']
        api = http_api_utils.get_api_by_name(self.api_full_name)
        if not api:
            api = http_api_utils.create_api(self.api_full_name)
        self.api_id = api['ApiId']
        stages = http_api_utils.get_api_stages(self.api_id)
        log_group_arn = cloudwatch_utils.create_or_get_api_log_group_arn(self.api_full_name)
        throttling = specs.get('throttling') or {}
        if settings.STAGE_NAME not in stages:
            http_api_utils.create_api_stage(self.api_id, settings.STAGE_NAME, log_group_arn, throttling)
        return

    def deploy_routes(self):
        rmap = http_api_utils.get_api_route_map(self.api_id)
        for route_key, specs in self.route_map.items():
            method, route = specs['method'], specs['route']
            itg_id = rmap.get(route_key, {}).get('Target')
            func_arn = lambda_utils.get_func_arn_by_name(specs['x-lambda-name'])
            caller_arn = 'arn:aws:execute-api:{}:{}:{}/{}/*{}'.format(
                settings.AWS_REGION, settings.AWS_ACCOUNT_ID, self.api_id, settings.STAGE_NAME, route,
            )
            if not itg_id:
                itg_id = http_api_utils.create_api_integration(self.api_id, func_arn)
            if route_key not in rmap:
                http_api_utils.create_api_route(self.api_id, method, route, itg_id, specs['auth'])
            else:
                http_api_utils.update_api_route(self.api_id, rmap[route_key]['RouteId'], itg_id, specs['auth'])
            # UPDATE INVOKE POLICY (ONLY ALLOW ONE ROUTE PER LAMBDA, EXCLUSIVELY)
            po = lambda_utils.get_lambda_invoke_policy(func_arn, caller_arn)
            if not po:
                po = lambda_utils.create_lambda_invoke_policy(func_arn, caller_arn)
            else:
                # lambda_utils.remove_lambda_invoke_policy(po['Resource'], po['Sid'])
                pass
        return

    def deploy_throttling(self):
        # UPDATE THROTTLING FOR ALL ROUTES (MANDATORY)
        throttling = http_api_utils.get_route_throttling_by_route_map(self.route_map)
        http_api_utils.update_route_throttling(self.api_id, settings.STAGE_NAME, throttling)

    def delete_app(self):
        api = http_api_utils.get_api_by_name(self.api_full_name)
        # DELETE API
        if api:
            http_api_utils.remove_api(self.api_id)


def main():
    h = DeployHelper()
    h.deploy()


if __name__ == '__main__':
    main()
