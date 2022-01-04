import os
import boto3
# from webexteamssdk import WebexTeamsAPI
from unittest import TestCase, mock
from urllib.parse import urlparse
from json import dumps
from moto import mock_dynamodb2
from chalice.test import Client
from chalicelib import SessionItem, UserItem, MessageItem


@mock_dynamodb2
class TestApp(TestCase):
    def setUp(self):
        # Mock environmental variables setup
        self.table_name = 'test-table'
        self.env_vars = {
            'OAUTH_CLIENT_ID': '123',
            'OAUTH_CLIENT_SECRET': '123',
            'OAUTH_REDIRECT_URI': 'https://redirect.uri.com/auth',
            'TABLE_NAME': self.table_name,
            'CORS_ALLOW_ORIGIN': 'https://test.domain.com',
            'APP_NAME': 'test_app',
            'ALLOWED_DOMAINS': 'domain.com',
            'EPSAGON_TOKEN': '123'
        }
        self.env_patch = mock.patch.dict(os.environ, self.env_vars)
        self.env_patch.start()
        from app import app, db_error
        self.db_error = db_error
        self.client = Client(app)
        # Mock DynamoDB table setup
        boto3.setup_default_session()
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.create_table(
            TableName=self.table_name,
            KeySchema=[
                {
                    'AttributeName': 'pk',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'sk',
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'pk',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'sk',
                    'AttributeType': 'S'
                },

            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 1,
                'WriteCapacityUnits': 1
            }
        )
        self.table.meta.client.get_waiter('table_exists').wait(
            TableName='test-table')
        assert self.table.table_status == 'ACTIVE'
        # Mock webexteamssdk object setup
        self.user_id = '123'
        self.wbx_person = mock.Mock()
        self.wbx_person.id = '123'
        self.wbx_person.nickName = 'Test'
        self.wbx_token = '123'
        # Mock DB items setup
        self.user_item = UserItem(
            table=self.table,
            wbx_person=self.wbx_person,
            wbx_token=self.wbx_token
        )
        self.session_item = SessionItem(
            table=self.table, user_id=self.user_item.id)
        self.user_item.add_session(self.session_item.id)
        self.message_item = MessageItem(
            table=self.table,
            user_id=self.user_item.id,
            time='2030-12-25T12:00:00',
            msg='Test msg',
            person='test@domain.com'
        )
        self.user_item.add_message(self.message_item.id)
        self.code = '123'

    def tearDown(self):
        self.client = None
        self.env_patch.stop()
        self.table.delete()
        self.dynamodb = None

    def test_wbxauth_get(self):
        with self.client as client:
            response = client.http.get(
                '/wbxauth',
                headers={'Content-Type': 'application/json'}
            )
            parsed = urlparse(response.json_body['results']['location'])
            self.assertIn(self.env_vars['OAUTH_CLIENT_ID'], parsed.query)
            self.assertIn(self.env_vars['OAUTH_REDIRECT_URI'], parsed.query)
            self.assertTrue(response.json_body['success'])

    def test_user_get(self):
        with self.client as client:
            response = client.http.get(
                f'/user?session={self.session_item.id}',
                headers={'Content-Type': 'application/json'}
            )
            self.assertEqual(
                response.json_body['results']['username'],
                self.wbx_person.nickName
            )

    def test_user_delete(self):
        with self.client as client:
            response = client.http.delete(
                f'/user?session={self.session_item.id}',
                headers={'Content-Type': 'application/json'}
            )
            self.assertTrue(response.json_body['success'])

    def test_logout_get(self):
        with self.client as client:
            response = client.http.get(
                f'/logout?session={self.session_item.id}',
                headers={'Content-Type': 'application/json'}
            )
            self.assertTrue(response.json_body['success'])

    def test_schedule_post(self):
        body = self.message_item.to_dict()
        body['timezone'] = 'US/Alaska'
        with self.client as client:
            response = client.http.post(
                f'/schedule?session={self.session_item.id}',
                headers={'Content-Type': 'application/json'},
                body=dumps(body)
            )
            self.assertTrue(response.json_body['success'])

    def test_messages_get(self):
        with self.client as client:
            response = client.http.get(
                f'/messages?session={self.session_item.id}',
                headers={'Content-Type': 'application/json'}
            )
            self.assertTrue(response.json_body['success'])
            self.assertIn(
                self.message_item.to_dict(), response.json_body['results'])

    def test_message_delete(self):
        with self.client as client:
            response = client.http.delete(
                (f'/message?session={self.session_item.id}'
                 f'&message={self.message_item.id}'),
                headers={'Content-Type': 'application/json'}
            )
            self.assertTrue(response.json_body['success'])


''' TODO: Tests that require webexteamssdk mocked
    def test_people_get(self):
        with self.client as client:
            response = client.http.get(
                f'/people?session={self.session_item.id}&q={self.person_name}',
                headers={'Content-Type':'application/json'}
            )
            self.assertTrue(response.json_body['success'])

    def test_auth_webex_fail(self):
        with self.client as client:
            auth_url_response = client.http.get(
                '/wbxauth',
                headers={'Content-Type':'application/json'}
            )
        auth_url = auth_url_response.json_body['results']['location']
        parsed_auth_url = urlparse(auth_url)
        parsed_auth_param_list = parsed_auth_url.query.split('&')
        for param in parsed_auth_param_list:
            if 'state' in param:
                self.state = param.split('=')[1]
        with mock.patch('WebexTeamsAPI') as WebexTeamsAPI:

            with self.client as client:
                auth_response = client.http.get(
                    f'/auth?code={self.code}&state={self.state}',
                    headers={'Content-Type':'application/json'}
                )
            print(auth_response.json_body)
            self.assertFalse(auth_response.json_body['success'])
'''
