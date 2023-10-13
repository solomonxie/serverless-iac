import json

import boto3

from aws_xray_sdk.core import patch_all

# apply the XRay handler to all clients.
patch_all()


def lambda_handler(event, context):
    client = boto3.client('events')
    upload_event_entry = {
        'Source': "dab.tracer",
        'EventBusName': 'default',
        'DetailType': 'Object Created',
        'Detail': json.dumps({
            "bucket": event['Records'][0]['s3']['bucket'],
            "object": {'key': event['Records'][0]['s3']['object']['key']},
        }
        ),
    }
    response = client.put_events(Entries=[upload_event_entry])
    return response
