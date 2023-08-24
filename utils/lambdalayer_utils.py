"""
REF: https://aws.amazon.com/premiumsupport/knowledge-center/lambda-layer-simulated-docker/
"""  # NOQA
import os
import logging

import settings
from utils.s3_utils import S3Bucket
from utils.common_utils import file_to_sha

lambda_client = settings.lambda_client
s3_client = S3Bucket(settings.IAC_BUCKET)
logger = logging.getLogger(__name__)


def get_layer_full_name(short_name: str) -> str:
    full_name = f'lambdalayer-{settings.APPLICATION_NAME}-{settings.STAGE_NAME}-{short_name}'
    return full_name


def get_layer_arn(layer_name: str) -> str:
    arn = f'arn:aws:lambda:{settings.AWS_REGION}:{settings.AWS_ACCOUNT_ID}:layer:{layer_name}'
    return arn


def get_layers_by_app_name(app_name: str):
    layers = []
    paginator = lambda_client.get_paginator('list_layers')
    response_iterator = paginator.paginate()
    for resp in response_iterator:
        layers += resp['Layers']
    layer_map = {
        x['LayerName']: x for x in layers if str(x.get('LayerName')).startswith(str(app_name))
    }
    return layer_map


def get_layer_s3_key(name: str) -> str:
    layer_s3_key = f'lambdalayer/{settings.APPLICATION_NAME}/{name}.zip'
    return layer_s3_key


def build_layer_py_requirements(specs: dict) -> str:
    layer_s3_key = specs['layer_s3_key']
    sha_s3_key = specs['sha_s3_key']
    sha = specs['sha']
    runtime = specs['runtime']
    if s3_client.exists(sha_s3_key) and s3_client.download_file_blob(sha_s3_key).decode() == sha:
        print('SKIP UPLOAD: LAYER ALREADY EXISTS ON S3')
        return layer_s3_key
    print('BUILDING PACKAGES...')
    tmp_path = f'/tmp/layer_{sha}.zip'
    assert 0 == os.system(f'rm -rdf {tmp_path} python ||true')
    workdir, filename = os.path.dirname(specs['path']), os.path.basename(specs['path'])
    cmd = f"""
        docker run --rm -v '{workdir}:/var/task' "public.ecr.aws/sam/build-{runtime}" \\
        /bin/sh -c "pip install -r {filename} -t python/lib/{runtime}/site-packages/; exit"
    """.strip()
    # cmd = f'pip install -r {path} -t python/lib/{runtime}/site-packages/'
    assert 0 == os.system(cmd)
    print('OK: BUILD LAYER')
    assert 0 == os.system(f'zip -r {tmp_path} {workdir}/python')
    assert 0 == os.system(f'zip -sf {tmp_path}; du -sh {tmp_path}')
    assert 0 == os.system(f'rm -rdf {workdir}/python ||true')
    print('OK: ZIPPED LAYER')
    s3_client.upload_file(tmp_path, layer_s3_key)
    s3_client.upload_file_blob(sha, sha_s3_key)
    print('OK: UPLOADED LAYER')
    return layer_s3_key


def create_python_package_layer(specs: dict):
    layer_name = specs['full_name']
    layer_s3_key = specs['layer_s3_key']
    print(f'CREATING LAYER: [{layer_name}]')
    args = {
        'LayerName': layer_name,  # REQUIRED
        'Content': {  # REQUIRED
            'S3Bucket': settings.IAC_BUCKET,
            'S3Key': layer_s3_key,
        },
        'CompatibleRuntimes': [specs['runtime']],
        'CompatibleArchitectures': [specs['arch']],
    }
    resp = lambda_client.publish_layer_version(**args)
    arn = resp['LayerVersionArn']
    print('OK: CREATED LAYER [{}] OF VERSION [V:{}]'.format(layer_name, resp['Version']))
    return arn


def get_latest_layer_by_name(layer_name: str):
    arn = get_layer_arn(layer_name)
    resp = lambda_client.list_layer_versions(LayerName=layer_name)
    versions = sorted(x['Version'] for x in resp['LayerVersions'])
    ver = versions[-1] if bool(versions) else None
    layer = lambda_client.get_layer_version_by_arn(Arn=f'{arn}:{ver}') if ver else {}
    return layer


def deploy_python_package_layer(specs: dict):
    layer = get_latest_layer_by_name(specs['full_name'])
    if layer.get('LayerVersionArn'):
        version_arn = layer['LayerVersionArn']
        print(f'SKIP CREATE LAYER: ALREADY EXISTS: {version_arn}')
    else:
        version_arn = create_python_package_layer(specs)
    return version_arn


def clean_layer_old_versions(sha: list) -> bool:
    return True
