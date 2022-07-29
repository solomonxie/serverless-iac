import os
from boto3 import session

FUNC_ALIAS = 'latest_release'

STAGE_NAME = os.environ.get('STAGE_NAME')
STAGE_SUBNAME = os.environ.get('STAGE_SUBNAME')
BUILD_NO = os.environ.get('BUILD_NO')
APPLICATION_NAME = os.environ.get('APPLICATION_NAME') or ''
REPO_URL = os.environ.get('REPO_URL')
LOCAL_REPO_PATH = os.environ.get('LOCAL_REPO_PATH')

LAMBDA_MAX_VERSION = 5  # PREVENT FROM LAMBDA QUOTA CONSUMTION
DEPLOY_TYPE = os.environ.get('DEPLOY_TYPE') or 'full'  # full | lambda | layer | httpapi | restapi | stepfunc | schedule
DEPLOY_TARGET = os.environ.get('DEPLOY_TARGET')  # THE NAME OF TARGET RESOURCE
ENABLE_LAMBDA_CONFIG_UPDATE = True if str(os.environ.get('ENABLE_LAMBDA_CONFIG_UPDATE')).lower() == 'true' else False

# AWS
AWS_IAM_PROFILE_NAME = os.environ.get('AWS_IAM_PROFILE_NAME')
AWS_REGION = os.environ.get('AWS_REGION')
AWS_LAMBDA_BUCKET = os.environ.get('AWS_LAMBDA_BUCKET')

AWS_VPC_IDS = os.environ.get('AWS_VPC_IDS')
AWS_VPC_SUBNET_IDS = os.environ.get('AWS_VPC_SUBNET_IDS')
AWS_VPC_SEC_GROUP_IDS = os.environ.get('AWS_VPC_SEC_GROUP_IDS')

ENABLE_VPC = True if str(os.environ.get('ENABLE_VPC')).lower() == 'true' else False
DISABLE_API_AUTHORIZER = True if os.environ.get('DISABLE_API_AUTHORIZER') else False

ENABLE_XRAY = True if os.environ.get('ENABLE_XRAY') else False

ses = session.Session(profile_name=AWS_IAM_PROFILE_NAME)
gw_client = ses.client('apigatewayv2')
rest_client = ses.client('apigateway')
lambda_client = ses.client('lambda')
iam_client = ses.client('iam')
log_client = ses.client('logs')
sts_client = ses.client('sts')
event_client = ses.client('events')
sfn_client = ses.client('stepfunctions')
sqs_client = ses.client('sqs')
sns_client = ses.client('sns')
s3_client = ses.client('s3')
s3_resource = ses.resource('s3')
AWS_ACCOUNT_ID = sts_client.get_caller_identity().get('Account')


#############################################################
DESCRIPTION = (
    "SCOPE==> "
    f"STAGE: [{STAGE_NAME}]; "
    f"SUB: [{STAGE_SUBNAME}]; "
    f"BUILD: [{BUILD_NO}]; "
    f"APP: [{APPLICATION_NAME}]; "
    f"VPC: [{ENABLE_VPC}]; "
)
print(DESCRIPTION)
