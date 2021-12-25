import boto3
from unittest import TestCase
from unittest.mock import Mock
from datetime import datetime, timedelta
from moto import mock_dynamodb2
from chalicelib import (
    UserItem,
    SessionItem,
    MessageItem,
    session_expiration_days
)


@mock_dynamodb2
class TestUserItem(TestCase):
    def setUp(self):
        self.wbx_person = Mock()
        self.wbx_person.id = '123'
        self.wbx_person.nickName = 'Test'
        self.wbx_token = '123'
        self.session_id = '123'
        self.message_id = '123'
        boto3.setup_default_session()
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.create_table(
            TableName='test-table',
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
        self.table.meta.client.get_waiter(
            'table_exists').wait(TableName='test-table')
        assert self.table.table_status == 'ACTIVE'
        self.user_item = UserItem(
            table=self.table,
            wbx_person=self.wbx_person,
            wbx_token=self.wbx_token
        )

    def tearDown(self):
        self.table.delete()
        self.dynamodb = None

    def test_user_create(self):
        user_item = UserItem(
            table=self.table,
            wbx_person=self.wbx_person,
            wbx_token=self.wbx_token
        )
        self.assertEqual(self.wbx_person.id,  user_item.id)

    def test_user_get(self):
        self.user_item = UserItem(table=self.table, user_id=self.wbx_person.id)
        self.assertEqual(self.user_item.wbx_token, self.wbx_token)
        self.assertEqual(self.user_item.id, self.wbx_person.id)
        self.assertEqual(self.user_item.displayname, self.wbx_person.nickName)

    def test_user_add_session(self):
        self.user_item.add_session(self.session_id)
        self.assertEqual(self.user_item.session_id, self.session_id)

    def test_user_remove_session(self):
        self.user_item.add_session(self.session_id)
        self.user_item.remove_session()
        self.assertEqual(self.user_item.session_id, None)

    def test_user_add_message(self):
        self.user_item.add_message(self.message_id)
        self.assertIn(self.message_id, self.user_item.messages)

    def test_user_remove_message(self):
        self.user_item.add_message(self.message_id)
        self.user_item.remove_message(self.message_id)
        self.assertNotIn(self.message_id, self.user_item.messages)

    def test_user_delete(self):
        self.assertTrue(self.user_item.delete())


@mock_dynamodb2
class TestSessionItem(TestCase):
    def setUp(self):
        self.user_id = '123'
        self.test_url = 'https://test.com/index.html'
        boto3.setup_default_session()
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.create_table(
            TableName='test-table',
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
        self.session_item = SessionItem(
            table=self.table,
            user_id=self.user_id
        )

    def tearDown(self):
        self.table.delete()
        self.dynamodb = None

    def test_session_create(self):
        session_item = SessionItem(table=self.table, user_id=self.user_id)
        self.assertEqual(session_item.user_id, self.user_id)

    def test_session_get(self):
        session_item = SessionItem(
            table=self.table,
            session_id=self.session_item.id
        )
        self.assertEqual(session_item.user_id, self.user_id)

    def test_session_delete(self):
        self.assertTrue(self.session_item.delete())

    def test_session_redirect_resp(self):
        redirect_resp = self.session_item.redirect_resp(self.test_url)
        redirect_loc = redirect_resp['headers']['Location']
        self.assertIn(
            f'{self.test_url}?session={self.session_item.id}', redirect_loc
        )

    def test_session_expired_false(self):
        self.assertFalse(self.session_item.expired)

    def test_session_expired_true(self):
        # Expire the session by subtracting a day from the expiration
        past_datetime = (
            datetime.utcnow() - timedelta(days=session_expiration_days))
        self.session_item.expires = past_datetime.isoformat()
        self.assertTrue(self.session_item.expired)


@mock_dynamodb2
class TestMessageItem(TestCase):
    def setUp(self):
        self.user_id = '123'
        self.time = datetime.utcnow().isoformat()
        self.msg = 'Test'
        self.person = 'person@domain.com'
        boto3.setup_default_session()
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.create_table(
            TableName='test-table',
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
        self.message_item = MessageItem(
            table=self.table,
            user_id=self.user_id,
            time=self.time,
            msg=self.msg,
            person=self.person
        )

    def tearDown(self):
        self.table.delete()
        self.dynamodb = None

    def test_message_create(self):
        message_item = MessageItem(
            table=self.table,
            user_id=self.user_id,
            time=self.time,
            msg=self.msg,
            person=self.person
        )
        # Check if UUID of message is 32 in length
        self.assertEqual(len(message_item.id), 32)

    def test_message_get(self):
        message_item_get = MessageItem(
            table=self.table, msg_id=self.message_item.id)
        self.assertEqual(message_item_get.time, self.time)
        self.assertEqual(len(message_item_get.id), 32)

    def test_message_delete(self):
        message_item_delete = MessageItem(
            table=self.table, msg_id=self.message_item.id)
        deleted = message_item_delete.delete()
        message_item_get = MessageItem(
            table=self.table, msg_id=self.message_item.id)
        self.assertTrue(deleted)
        self.assertEqual(message_item_get.user_id, None)

    def test_message_to_dict(self):
        dict = self.message_item.to_dict()
        self.assertEqual(dict['id'], self.message_item.id)
        self.assertEqual(dict['time'], self.message_item.time)
        self.assertEqual(dict['msg'], self.message_item.msg)
        self.assertEqual(dict['person'], self.message_item.person)
