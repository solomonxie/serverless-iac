import json
from unittest import TestCase
from oauth2client import service_account
from unittest.mock import patch, MagicMock

from utils.gcp_utils.storage_utils import GcpStorage


class TestGcpBucket(TestCase):
    def setUp(self):
        self.patches = [
            patch(
                'oauth2client.service_account.ServiceAccountCredentials.from_json_keyfile_dict',
                return_value=MagicMock()
            ),
        ]
        _ = [p.start() for p in self.patches]

    def tearDown(self):
        _ = [p.stop() for p in self.patches]

    def test_list_files__ok(self):
        mock_data = {'items': [{'name': '123.json'}, {'name': '234.json'}]}
        mock_storage = MagicMock()
        mock_storage.objects().list().execute.return_value = mock_data
        with patch('googleapiclient.discovery.build', return_value=mock_storage):
            storage = GcpStorage(bucket='fakebucket', credential_dict={'pkey': 123})
            file_paths = storage.list_files()
        self.assertEqual([x['name'] for x in mock_data['items']], file_paths)

    def test_download_blob__ok(self):
        mock_data = {'a': 1, 'b': 2}
        mock_storage = MagicMock()
        mock_storage.objects().get_media().execute.return_value = mock_data
        with patch('googleapiclient.discovery.build', return_value=mock_storage):
            storage = GcpStorage(bucket='fakebucket', credential_dict={'pkey': 123})
            data = storage.download_blob('/a/b/c.csv')
        self.assertEqual(mock_data, data)

    def test_download_header__ok(self):
        mock_data = {'etag': '123', 'Content-Type': 'application/json'}
        mock_storage = MagicMock()
        mock_storage.objects().get().execute.return_value = mock_data
        with patch('googleapiclient.discovery.build', return_value=mock_storage):
            storage = GcpStorage(bucket='fakebucket', credential_dict={'pkey': 123})
            headers = storage.download_headers('/a/b/c.csv')
        self.assertEqual(mock_data, headers)

    def test_verify_access__ok(self):
        mock_data = {'items': [{'name': '123.json'}, {'name': '234.json'}]}
        mock_storage = MagicMock()
        mock_storage.objects().list().execute.return_value = mock_data
        with patch('googleapiclient.discovery.build', return_value=mock_storage):
            storage = GcpStorage(bucket='fakebucket', credential_dict={'pkey': 123})
            result = storage.verify_bucket_access()
        self.assertEqual(True, result)


class TestGoogleAPIs(TestCase):
    def setUp(self):
        self.patches = [
        ]
        _ = [p.start() for p in self.patches]

    def tearDown(self):
        _ = [p.stop() for p in self.patches]

    def test_parsing_service_account__ok(self):
        with open('tests/mock_data/gp-iam-project-demo01-312408a22210.json') as f:
            cred_dict = json.loads(f.read())
        scopes = ['https://www.googleapis.com/auth/devstorage.read_only']
        cred = service_account.ServiceAccountCredentials.from_json_keyfile_dict(cred_dict, scopes=scopes)
        self.assertIsNotNone(cred)
        self.assertEqual(cred.client_id, cred_dict['client_id'])
        self.assertEqual(cred.invalid, False)

    def test_parsing_service_account__invalid(self):
        cred_dict = {'abc': 'abc'}
        scopes = ['https://www.googleapis.com/auth/devstorage.read_only']
        with self.assertRaises(ValueError):
            service_account.ServiceAccountCredentials.from_json_keyfile_dict(cred_dict, scopes=scopes)

        with open('tests/mock_data/gp-iam-project-demo01-312408a22210.json') as f:
            valid_cred_dict = json.loads(f.read())

        valid_cred_dict.pop('private_key')
        with self.assertRaises(ValueError):
            service_account.ServiceAccountCredentials.from_json_keyfile_dict(cred_dict, scopes=scopes)
