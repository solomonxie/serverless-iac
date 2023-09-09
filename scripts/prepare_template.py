import os
import logging
from copy import deepcopy

import settings
from utils import s3_utils
from utils import iam_utils
from utils import common_utils
from utils import event_utils
from utils import lambda_utils
from utils import stepfunc_utils
from utils import http_api_utils
from utils import rest_api_utils
from utils import cloudwatch_utils

logger = logging.getLogger(__name__)
s3_client = s3_utils.S3Bucket(settings.IAC_BUCKET)

TEMPLATE = common_utils.get_template()
REPO_PATH = TEMPLATE['info']['repo_path']
LAMBDA_PO_PATH = os.path.realpath(os.path.expanduser(
    './iam/iam-policy-lambda-execute.json'
))
STEPFUNC_PO_PATH = os.path.realpath(os.path.expanduser(
    './iam/iam-policy-stepfunc-execution.json'
))
PO_NAME = 'lambda-general'
# ACTIONS = {'services': [], 'resources': []}


def prepare_template() -> dict:
    template = deepcopy(TEMPLATE)
    for service, specs in (template.get('default') or {}).items():
        if service == 'http-api':
            specs = prepare_http_api(specs)
        elif service == 'rest-api':
            specs = prepare_rest_api(specs)
        elif service == 'eventbridge':
            pass  # TODO
    for k, items in (template.get('resources') or {}).items():
        if k == 'lambda':
            _ = [prepare_lambda(x) for x in items]
        elif k == 'schedule':
            _ = [prepare_schedule(x) for x in items]
        elif k == 'stepfunc':
            _ = [prepare_stepfunc(x) for x in items]
    return template


def prepare_http_api(specs: dict) -> dict:
    specs['swagger-path'] = os.path.realpath(os.path.join(
        os.path.expanduser(REPO_PATH), specs['swagger-path']
    ))
    specs['swagger'] = common_utils.render_yaml(specs['swagger-path'])
    specs['swagger']['info']['title'] = specs['name']
    specs['name'] = http_api_utils.get_api_full_name(specs['name'])
    specs['log_group_arn'] = cloudwatch_utils.get_log_group_arn(specs['name'])
    specs['log_group'] = cloudwatch_utils.get_log_group(specs['name'])
    specs['meta'] = http_api_utils.get_api_by_name(specs['name'])
    specs['api_id'] = specs['meta'].get('ApiId')
    specs['stage_map'] = http_api_utils.get_api_stages(specs['api_id'])
    specs['route_map'] = http_api_utils.get_api_route_map(specs['api_id'])
    return specs


def prepare_rest_api(specs: dict) -> dict:
    specs['swagger-path'] = os.path.realpath(os.path.join(
        os.path.expanduser(REPO_PATH), specs['swagger-path']
    ))
    specs['swagger'] = common_utils.render_yaml(specs['swagger-path'])
    specs['swagger']['info']['title'] = specs['name']
    specs['name'] = rest_api_utils.get_api_full_name(specs['name'])
    specs['meta'] = rest_api_utils.get_api_by_name(specs['name'])
    specs['api_id'] = specs['meta'].get('id')
    specs['route_map'] = rest_api_utils.get_api_route_map(specs['api_id'])
    specs['stages'] = rest_api_utils.get_api_stages(specs['api_id'])
    specs['deployment'] = rest_api_utils.get_api_latest_deployment(specs['api_id'])
    return specs


def prepare_lambda(specs: dict) -> dict:
    specs['name'] = lambda_utils.get_func_full_name(specs['name'])
    specs['s3_key'] = lambda_utils.get_func_s3_key_by_name(specs['name'])
    specs['meta'] = lambda_utils.get_func_info_by_name(specs['name'])
    specs['versions'] = lambda_utils.get_all_func_versions(specs['name'])
    specs['alias'] = lambda_utils.get_func_alias(specs['name'], settings.FUNC_ALIAS)
    # IAM
    specs['po_path'] = LAMBDA_PO_PATH
    specs['po_name'] = iam_utils.get_policy_full_name('lambda-general')
    specs['po_arn'] = iam_utils.get_policy_arn_by_name(specs['po_name'])
    specs['policy'] = iam_utils.get_iam_policy(specs['po_arn'])
    specs['ro_name'] = iam_utils.get_role_full_name('ro-' + specs['name'])
    specs['role-arn'] = iam_utils.get_role_arn_by_name(specs['ro_name'])
    specs['role'] = iam_utils.get_iam_role(specs['ro_name'])
    # LAYER
    for layer in specs.get('layers') or []:
        if layer['type'] == 'python-requirements':
            path = os.path.join(REPO_PATH, layer['manifest'])
            layer['sha'] = lambda_utils.file_to_sha(os.path.realpath(os.path.expanduser(path)))
            layer['meta'] = lambda_utils.get_latest_layer_by_name(layer['sha'])
            layer['s3_key'] = lambda_utils.get_layer_s3_key_by_sha(layer['sha'], 'python')
            layer['arn'] = lambda_utils.get_layer_arn(layer['sha'])
            layer['exists'] = s3_client.exists(layer['s3_key'])
    specs['layer_arn_list'] = [x['arn'] for x in specs.get('layers', [])]
    return specs


def prepare_schedule(specs: dict) -> dict:
    specs['name'] = event_utils.get_rule_full_name(specs['name'])
    if specs['target-type'] == 'lambda':
        specs['target-arn'] = lambda_utils.get_func_arn_by_name(specs['target-name'])
    elif specs['target-type'] == 'stepfunc':
        specs['ro_name'] = iam_utils.get_role_full_name('ro-' + specs['name'])
        specs['role_arn'] = iam_utils.get_role_arn_by_name(specs['ro_name'])
        specs['role'] = iam_utils.get_iam_role(specs['ro_name'])
        specs['target-arn'] = stepfunc_utils.get_stepfunc_arn_by_name(specs['target-name'])
    else:
        specs['target-arn'] = None
    return specs


def prepare_stepfunc(specs: dict) -> dict:
    specs['name'] = stepfunc_utils.get_stepfunc_full_name(specs['name'])
    specs['meta'] = stepfunc_utils.get_stepfunc_by_name(specs['name'])
    specs['arn'] = stepfunc_utils.get_stepfunc_arn_by_name(specs['name'])
    specs['path'] = os.path.realpath(os.path.join(REPO_PATH, specs['definition-path']))
    with open(specs['path']) as f:
        raw = f.read()
        specs['expression'] = stepfunc_utils.render_state_machine_expression(raw)
    # IAM
    specs['po_path'] = LAMBDA_PO_PATH
    specs['po_name'] = iam_utils.get_policy_full_name('lambda-general')
    specs['po_arn'] = iam_utils.get_policy_arn_by_name(specs['po_name'])
    specs['policy'] = iam_utils.get_iam_policy(specs['po_arn'])
    specs['ro_name'] = iam_utils.get_role_full_name('ro-' + specs['name'])
    specs['role-arn'] = iam_utils.get_role_arn_by_name(specs['ro_name'])
    specs['role'] = iam_utils.get_iam_role(specs['ro_name'])
    return specs


def main():
    prepare_template()


if __name__ == '__main__':
    main()
