import os
import json
from google.cloud import storage
from google.cloud import functions_v1
from google.cloud import apigateway_v1
from google.oauth2 import service_account


def get_gcp_credential_obj():
    cred_json_path = os.path.expanduser(str(os.environ.get('GCP_CRED_JSON_PATH')))
    cred = json.loads(open(cred_json_path).read())
    cred_obj = service_account.Credentials.from_service_account_info(cred)
    # GCP_PROJECT_ID = cred_obj.project_id
    # GCP_SERVICE_ACCOUNT_EMAIL = cred_obj.service_account_email
    # GCP_REGION = 'us-east1'
    return cred_obj


def get_storage_client(cred_obj: object = None):
    cred_obj = cred_obj or get_gcp_credential_obj()
    return storage.Client(credentials=cred_obj)


def get_function_client(cred_obj: object = None):
    cred_obj = cred_obj or get_gcp_credential_obj()
    return functions_v1.CloudFunctionsServiceClient(credentials=cred_obj)


def get_gateway_client(cred_obj: object = None):
    cred_obj = cred_obj or get_gcp_credential_obj()
    return apigateway_v1.ApiGatewayServiceClient(credentials=cred_obj)


storage_client = get_storage_client()
function_client = get_function_client()
gw_client = get_gateway_client()
