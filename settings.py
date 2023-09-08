import os
import boto3
from botocore.client import Config

FUNC_ALIAS = 'latest_release'

TEAM_NAME = os.environ.get('TEAM_NAME')
STAGE_NAME = os.environ.get('STAGE_NAME')
BUILD_NO = os.environ.get('BUILD_NO')
APPLICATION_NAME = os.environ.get('APPLICATION_NAME') or ''
REPO_URL = os.environ.get('REPO_URL')
LOCAL_REPO_PATH = os.environ.get('LOCAL_REPO_PATH')
TEMPLATE_NAME = os.getenv('TEMPLATE_NAME')

LAMBDA_MAX_VERSION = 5  # PREVENT FROM LAMBDA QUOTA CONSUMTION
DEPLOY_TYPE = os.environ.get('DEPLOY_TYPE') or 'full'  # full | lambda | layer | httpapi | restapi | stepfunc | schedule
DEPLOY_TARGET = os.environ.get('DEPLOY_TARGET')  # THE NAME OF TARGET RESOURCE
ENABLE_LAMBDA_CONFIG_UPDATE = True if str(os.environ.get('ENABLE_LAMBDA_CONFIG_UPDATE')).lower() == 'true' else False

# AWS
AWS_ACCOUNT_ID = os.getenv('AWS_ASSUME_ACCOUNT_ID') or os.getenv('AWS_AUTH_ACCOUNT_ID') or os.getenv('AWS_ACCOUNT_ID')
AWS_REGION = os.environ.get('DEFAULT_REGION') or os.environ.get('AWS_REGION')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID') or os.getenv('AWS_AUTH_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY') or os.getenv('AWS_AUTH_SECRET_ACCESS_KEY')
AWS_SESSION_TOKEN = None

AWS_VPC_IDS = os.environ.get('AWS_VPC_IDS')
AWS_VPC_SUBNET_IDS = os.environ.get('AWS_VPC_SUBNET_IDS')
AWS_VPC_SEC_GROUP_IDS = os.environ.get('AWS_VPC_SEC_GROUP_IDS')

IAC_BUCKET = os.environ.get('IAC_BUCKET')

ENABLE_VPC = True if str(os.environ.get('ENABLE_VPC')).lower() == 'true' else False
DISABLE_API_AUTHORIZER = True if os.environ.get('DISABLE_API_AUTHORIZER') else False

ENABLE_XRAY = True if os.environ.get('ENABLE_XRAY') else False

if os.getenv('AWS_ASSUME_ROLE'):
    client = boto3.client(
        'sts', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )
    role = client.assume_role(RoleArn=os.getenv('AWS_ASSUME_ROLE'), RoleSessionName=APPLICATION_NAME)
    AWS_ACCESS_KEY_ID = role['Credentials']['AccessKeyId']
    AWS_SECRET_ACCESS_KEY = role['Credentials']['SecretAccessKey']
    AWS_SESSION_TOKEN = role['Credentials']['SessionToken']
aws_creds = {
    'aws_access_key_id': AWS_ACCESS_KEY_ID,
    'aws_secret_access_key': AWS_SECRET_ACCESS_KEY,
}
if AWS_SESSION_TOKEN:
    aws_creds['aws_session_token'] = AWS_SESSION_TOKEN
ses = boto3.session.Session(region_name=AWS_REGION, **aws_creds)
BOTO_CONFIG = Config(connect_timeout=5, retries={'max_attempts': 3})
gw_client = ses.client('apigatewayv2', config=BOTO_CONFIG)
rest_client = ses.client('apigateway', config=BOTO_CONFIG)
lambda_client = ses.client('lambda', config=BOTO_CONFIG)
iam_client = ses.client('iam', config=BOTO_CONFIG)
log_client = ses.client('logs', config=BOTO_CONFIG)
sts_client = ses.client('sts', config=BOTO_CONFIG)
event_client = ses.client('events', config=BOTO_CONFIG)
sfn_client = ses.client('stepfunctions', config=BOTO_CONFIG)
sqs_client = ses.client('sqs', config=BOTO_CONFIG)
sns_client = ses.client('sns', config=BOTO_CONFIG)
s3_client = ses.client('s3', config=BOTO_CONFIG)
s3_resource = ses.resource('s3', config=BOTO_CONFIG)


#############################################################
DESCRIPTION = (
    "SCOPE==> "
    f"STAGE: [{STAGE_NAME}]; "
    f"BUILD: [{BUILD_NO}]; "
    f"APP: [{APPLICATION_NAME}]; "
    f"VPC: [{ENABLE_VPC}]; "
)
print(DESCRIPTION)
