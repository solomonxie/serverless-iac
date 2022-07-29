"""
REF: https://cloud.google.com/python/docs/reference/storage/latest/google.cloud.storage.client.Client
"""  # NOQA
from google.cloud.storage.blob import Blob
from utils.gcp_utils.gcp_clients import storage_client

import logging
logger = logging.getLogger(__name__)


class GcpBucket:
    """ Google Cloud Storage operations through [ Service Account ] as authentication """

    def __init__(self, bucket_name: str, **kwargs):
        self.bucket_name = bucket_name
        self.bucket = storage_client.get_bucket(self.bucket_name)
        logger.info('[ GCP STORAGE ] SUCCESSFULLY INITIALIZED...')

    def verify_bucket_access(self):
        is_valid = False
        try:
            next(self.bucket.list_blobs())
            is_valid = True
        except Exception as e:
            logger.warning('[ VALIDATE BUCKET ] INVALID CREDENTAIL, VALIDATION FAILED: {}'.format(e))
        return is_valid

    def list_files(self, prefix=''):
        blob_list = [x for x in self.bucket.list_blobs(prefix=prefix)]
        path_list = [x['name'] for x in blob_list]
        logger.info('[ GET LIST ] DETECTED {} FILES IN BUCKET'.format(len(path_list)))
        return path_list

    def download_headers(self, cloud_path: str) -> dict:
        blob = self.bucket.get_blob(cloud_path)
        headers = {
            'Content-Type': blob.content_type,
            'Content-Encoding': blob.content_encoding,
            'Content-Language': blob.content_language,
            'Cache-Control': blob.cache_control,
            'Time-Created': blob.time_created,
        } if blob else {}
        headers.update(blob.metadata or {})
        return headers

    def download_blob(self, cloud_path: str) -> dict:
        blob = self.bucket.get_blob(cloud_path)
        return blob

    def upload_from_string(self, cloud_path: str, body: str) -> bool:
        blob = Blob(cloud_path, self.bucket)
        blob.upload_from_string(body)
        return True

    def upload_from_file(self, cloud_path: str, local_path: str) -> bool:
        blob = Blob(cloud_path, self.bucket)
        blob.upload_from_filename(local_path)
        return True


def test_storage_client():
    __import__('pudb').set_trace()
    bucket = storage_client.get_bucket('my-poc-bucket')
    blob = Blob('README.md', bucket)
    blob = bucket.get_blob('README.md')
    blob.upload_from_filename('./README.md')
    print(blob.download_as_string())
    blob.upload_from_string('New contents!')
    return


if __name__ == '__main__':
    test_storage_client()
