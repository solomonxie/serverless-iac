"""
REF: https://cloud.google.com/python/docs/reference/cloudfunctions/latest/google.cloud.functions_v1.services.cloud_functions_service.CloudFunctionsServiceClient
"""  # NOQA
from google.cloud.functions_v1 import GetFunctionRequest
from google.cloud.functions_v1 import ListFunctionsRequest

from utils.gcp_utils.gcp_clients import function_client
from utils.gcp_utils.gcp_clients import GCP_PROJECT_ID, GCP_REGION

import logging
logger = logging.getLogger(__name__)


def get_func_frn(name: str) -> str:
    frn = f'projects/{GCP_PROJECT_ID}/locations/{GCP_REGION}/functions/{name}'
    return frn


def get_func_parent() -> str:
    prefix = f'projects/{GCP_PROJECT_ID}/locations/{GCP_REGION}'
    return prefix


def test_function_client():
    __import__('pudb').set_trace()
    prefix = get_func_parent()
    req = ListFunctionsRequest(parent=prefix)
    pager = function_client.list_functions(request=req)
    func_list = [x for x in pager]
    print(func_list)
    frn = get_func_frn('function-1')
    req = GetFunctionRequest(name=frn)
    func = function_client.get_function(request=req)
    print(func)


if __name__ == '__main__':
    test_function_client()
