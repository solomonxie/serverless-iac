import os
import logging

from utils import common_utils
from utils import rest_api_utils

import settings
logger = logging.getLogger(__name__)


class RestApiDeployHelper:
    def __init__(self):
        self.template = common_utils.get_template()
        if not self.template['resources'].get('rest-api'):
            return
        repo_path = self.template['info']['repo_path']
        swagger_path = os.path.realpath(os.path.join(
            os.path.expanduser(repo_path),
            self.template['resources']['rest-api']['swagger-path']
        ))
        self.specs = rest_api_utils.render_specs(self.template['resources']['rest-api'])
        self.swagger = rest_api_utils.render_swagger(swagger_path, self.specs)
        remote = rest_api_utils.get_api_by_name(self.specs['full-name'])
        self.api_id = remote.get('id')

    def deploy(self):
        if not self.template['resources'].get('rest-api'):
            print('SKIP DEPLOYMENT OF REST API FOR NOT FOUND DEFINITION')
            return
        if self.specs.get('no-deploy') is True:
            print('SKIP DEPLOYMENT FOR [REST-API]')
            return
        # DEPLOY API
        if not self.api_id:
            self.api_id = rest_api_utils.create_api(self.specs['full-name'], self.specs)
        rest_api_utils.import_routes(self.api_id, self.swagger)
        # DEPLOY STAGES
        dpl = rest_api_utils.get_api_latest_deployment(self.api_id)
        if not dpl:
            dpl = rest_api_utils.create_api_deployment(self.api_id)
        dpl_id = dpl['id']
        stages = rest_api_utils.get_api_stages(self.api_id)
        if settings.STAGE_NAME not in stages:
            rest_api_utils.create_api_stage(self.api_id, settings.STAGE_NAME, dpl_id)
        print('OK.')
        return True


def main():
    h = RestApiDeployHelper()
    h.deploy()


if __name__ == '__main__':
    main()
