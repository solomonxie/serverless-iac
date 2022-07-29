import os
import json
from google.cloud import storage
from google.cloud import functions_v1
from google.cloud import apigateway_v1
from google.oauth2 import service_account

cred_path = os.path.expanduser(str(os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')))
cred = json.loads(open(cred_path).read())
cred_obj = service_account.Credentials.from_service_account_info(cred)
GCP_PROJECT_ID = cred_obj.project_id
GCP_SERVICE_ACCOUNT_EMAIL = cred_obj.service_account_email
GCP_REGION = 'us-east1'

storage_client = storage.Client(credentials=cred_obj)
function_client = functions_v1.CloudFunctionsServiceClient(credentials=cred_obj)
gw_client = apigateway_v1.ApiGatewayServiceClient(credentials=cred_obj)
