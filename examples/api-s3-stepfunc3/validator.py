import json
import boto3


def lambda_handler(event, context):
    BUCKET_NAME = event["s3_uri"]
    OBJECT_NAME = event["s3_key"]
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=BUCKET_NAME, Key=OBJECT_NAME)
    content = response['Body'].read().decode('utf-8')
    input_json = json.loads(content)
    validator(input_json)
    return input_json


def validator(data):
    # TODO: Write validation logic
    if data:
        return True
    return False
