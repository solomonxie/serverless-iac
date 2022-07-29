"""
REF: https://cloud.google.com/python/docs/reference/apigateway/latest/google.cloud.apigateway_v1.services.api_gateway_service.ApiGatewayServiceClient
"""  # NOQA

from google.cloud.apigateway_v1 import GetApiRequest
from google.cloud.apigateway_v1 import GetGatewayRequest
from google.cloud.apigateway_v1 import GetApiConfigRequest

from utils.gcp_utils.gcp_clients import gw_client
from utils.gcp_utils.gcp_clients import GCP_PROJECT_ID, GCP_REGION

import logging
logger = logging.getLogger(__name__)


def get_api_frn(api_name: str) -> str:
    frn = f'projects/{GCP_PROJECT_ID}/locations/global/apis/{api_name}'
    return frn


def get_api_config_frn(api_name: str, config_name: str) -> str:
    frn = f'projects/{GCP_PROJECT_ID}/locations/global/apis/{api_name}/configs/{config_name}'
    return frn


def get_gateway_frn(api_name: str, gateway_name: str) -> str:
    frn = f'projects/{GCP_PROJECT_ID}/locations/{GCP_REGION}/gateways/{gateway_name}'
    return frn


def test_gw_client():
    frn = get_api_frn('hello-api-123')
    response = gw_client.get_api(request=GetApiRequest(name=frn))
    print(response)
    frn = get_api_config_frn('hello-api-123', 'hello-api-config')
    response = gw_client.get_api_config(request=GetApiConfigRequest(name=frn))
    print(response)
    __import__('pudb').set_trace()
    frn = get_gateway_frn('hello-api-123', 'hello-gateway')
    response = gw_client.get_gateway(request=GetGatewayRequest(name=frn))
    print(response)


if __name__ == '__main__':
    test_gw_client()
