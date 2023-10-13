import os

from settings import s3_client
from settings import s3_resource

import logging
logger = logging.getLogger(__name__)


def get_s3_file_arn(bucket_name: str, s3_key: str) -> str:
    arn = f'arn:aws:s3:::{bucket_name}/{s3_key}'
    return arn


class S3Bucket:
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name

    def exists(self, key_name):
        is_existed = False
        try:
            result = self.list_files(key_name)
            is_existed = bool(result)
        except Exception as ex:  # pylint: disable=broad-except
            logger.info('check_if_key_exist_in_s3 false. key = %s, msg = %s', key_name, ex)
        return is_existed

    def upload_file(self, localpath, s3_key=None):
        if not os.path.exists(localpath):
            return False
        s3_key = s3_key or os.path.basename(localpath)
        s3_client.upload_file(localpath, self.bucket_name, s3_key)
        return True

    def upload_file_blob(self, file_blob, s3_key):
        s3_client.put_object(Bucket=self.bucket_name, Key=s3_key, Body=file_blob)
        return True

    def download_file_blob(self, s3_key):
        obj = s3_resource.Object(self.bucket_name, s3_key)
        body = obj.get()
        blob = body['Body'].read()
        return blob

    def get_signed_url(self, s3_key, expiredin=86400, httpmethod=None):
        try:
            url = s3_client.generate_presigned_url(
                ClientMethod='get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key,
                },
                ExpiresIn=expiredin,
                HttpMethod=httpmethod,
            )
        except Exception as e:
            logger.exception(e)
            raise RuntimeError('FAILED TO GET SIGNED S3 LINK, PLEASE TRY AGAIN')
        return url

    def get_file_meta_info(self, key_name, meta_info_name):
        try:
            meta_info = s3_client.head_object(Bucket=self.bucket_name, Key=key_name)
            return meta_info.get(meta_info_name)
        except Exception as ex:
            raise RuntimeError(ex)

    def create_bucket(self):
        existing = [b['Name'] for b in s3_client.list_buckets()['Buckets']]
        if self.bucket_name not in existing:
            s3_resource.create_bucket(Bucket=self.bucket_name)
            print('Created bucket:', str(self.bucket_name))
        else:
            print('Bucket existed, skip creation.')
        return s3_resource.Bucket(self.bucket_name).creation_date

    def delete_bucket(self):
        existing = [b['Name'] for b in s3_client.list_buckets()['Buckets']]
        if self.bucket_name in existing:
            bucket = s3_resource.Bucket(self.bucket_name)
            _ = [key.delete() for key in bucket.objects.all()]
            bucket.delete()

    def list_files(self, path_prefix=None):
        if path_prefix:
            keys = [obj.key for obj in s3_resource.Bucket(self.bucket_name).objects.filter(Prefix=path_prefix)]
        else:
            keys = [obj.key for obj in s3_resource.Bucket(self.bucket_name).objects.all()]
        return keys
