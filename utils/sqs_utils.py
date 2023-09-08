"""
REF: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs.html
"""  # NOQA
import json
import logging

import settings
from utils import common_utils

sqs_client = settings.sqs_client
logger = logging.getLogger(__name__)


def render_specs(specs: dict) -> dict:
    specs['type'] = specs.get('type') or 'standard'
    assert specs['type'] in ['standard', 'fifo']
    specs['full_name'] = get_queue_full_name(specs['name'], specs['type'])
    specs['delay'] = specs.get('delay') or 0
    specs['msg-bytes'] = int(specs.get('msg-bytes') or 1024 * 256)  # bytes
    assert 1024 <= specs['msg-bytes'] <= 1024 * 256
    specs['retention'] = specs.get('retention') or 60 * 60 * 24 * 7  # seconds
    specs['receive-wait'] = specs.get('receive-wait') or 0  # seconds
    assert specs['receive-wait'] in range(21)
    specs['policy-path'] = './iam/iam-policy-sqs-resource.json'
    po = common_utils.render_json(specs['policy-path'])
    specs['policy'] = json.dumps(po)  # TODO
    specs['redrive-policy'] = {
        'deadLetterTargetArn': '',
        'maxReceiveCount': 100,
    }  # TODO
    return specs


def get_queue_full_name(name: str, qtype: str = 'standard') -> str:
    full_name = f'sqs-{settings.APPLICATION_NAME}-{settings.STAGE_NAME}-{name}'
    full_name += '.fifo' if qtype == 'fifo' else ''
    return full_name


def create_queue(specs: dict) -> dict:
    args = {
        'QueueName': specs['full_name'],
        'Attributes': {
            'DelaySeconds': str(specs['delay']),
            'MaximumMessageSize': str(specs['msg-bytes']),
            'MessageRetentionPeriod': str(specs['retention']),
            'ReceiveMessageWaitTimeSeconds': str(specs['receive-wait']),
            'Policy': specs['policy'],
            # 'RedrivePolicy': specs['redrive-policy'],
            # 'FifoQueue': 'true' if specs['type'] == 'fifo' else 'false',  # FIXME
        },
        'tags': {
            'app_name': settings.APPLICATION_NAME,
        }
    }
    resp = sqs_client.create_queue(**args)
    resp.pop('ResponseMetadata', None)
    specs['queue-url'] = resp['QueueUrl']
    print('DONE: CREATED SQS QUEUE: {}'.format(specs['full_name']))
    return resp
