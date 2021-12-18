import boto3
from unittest import TestCase
from unittest.mock import Mock
from datetime import datetime, timedelta
from moto import mock_dynamodb2
from chalicelib import UserItem, SessionItem, MessageItem, session_expiration_days


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
        self.table.meta.client.get_waiter('table_exists').wait(TableName='test-table')
        assert self.table.table_status == 'ACTIVE'

    def tearDown(self):
        self.table.delete()
        self.dynamodb = None

    def test_user_create(self):        
        user_item = UserItem(table=self.table, wbx_person=self.wbx_person, wbx_token=self.wbx_token)
        self.assertEqual(self.wbx_person.id,  user_item.id)

    def test_user_get(self):
        user_item = UserItem(table=self.table, wbx_person=self.wbx_person, wbx_token=self.wbx_token)
        user_item = UserItem(table=self.table, user_id=self.wbx_person.id)
        self.assertEqual(user_item.wbx_token, self.wbx_token)
        self.assertEqual(user_item.id, self.wbx_person.id)
        self.assertEqual(user_item.displayname, self.wbx_person.nickName)

    def test_user_delete(self):        
        user_item = UserItem(table=self.table, wbx_person=self.wbx_person, wbx_token=self.wbx_token)
        self.assertTrue(user_item.delete())

    def test_user_add_session(self):
        user_item = UserItem(table=self.table, wbx_person=self.wbx_person, wbx_token=self.wbx_token)
        user_item.add_session(self.session_id)
        self.assertEqual(user_item.session_id, self.session_id)

    def test_user_remove_session(self):
        user_item = UserItem(table=self.table, wbx_person=self.wbx_person, wbx_token=self.wbx_token)
        user_item.add_session(self.session_id)
        user_item.remove_session()
        self.assertEqual(user_item.session_id, None)

    def test_user_add_message(self):
        user_item = UserItem(table=self.table, wbx_person=self.wbx_person, wbx_token=self.wbx_token)
        user_item.add_message(self.message_id)
        self.assertIn(self.message_id, user_item.messages)

    def test_user_remove_message(self):
        user_item = UserItem(table=self.table, wbx_person=self.wbx_person, wbx_token=self.wbx_token)
        user_item.add_message(self.message_id)
        user_item.remove_message(self.message_id)
        self.assertNotIn(self.message_id, user_item.messages)


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
        self.table.meta.client.get_waiter('table_exists').wait(TableName='test-table')
        assert self.table.table_status == 'ACTIVE'

    def tearDown(self):
        self.table.delete()
        self.dynamodb = None

    def test_session_create(self):
        session_item = SessionItem(table=self.table, user_id=self.user_id)
        self.assertEqual(session_item.user_id, self.user_id)
    
    def test_session_get(self):
        new_session_item = SessionItem(table=self.table, user_id=self.user_id)
        session_item = SessionItem(table=self.table, session_id=new_session_item.id)
        self.assertEqual(session_item.user_id, self.user_id)
    
    def test_session_delete(self):
        new_session_item = SessionItem(table=self.table, user_id=self.user_id)
        self.assertTrue(new_session_item.delete())

    def test_session_redirect_resp(self):
        new_session_item = SessionItem(table=self.table, user_id=self.user_id)
        redirect_resp = new_session_item.redirect_resp(self.test_url)
        redirect_loc = redirect_resp['headers']['Location']
        self.assertIn(f'{self.test_url}?session={new_session_item.id}', redirect_loc)

    def test_session_expired_false(self):
        new_session_item = SessionItem(table=self.table, user_id=self.user_id)
        self.assertFalse(new_session_item.expired)
    
    def test_session_expired_true(self):
        new_session_item = SessionItem(table=self.table, user_id=self.user_id)
        # Expire the session by subtracting a day from the expiration
        past_datetime = datetime.utcnow() - timedelta(days=session_expiration_days)
        new_session_item.expires = past_datetime.isoformat()
        self.assertTrue(new_session_item.expired)


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
        self.table.meta.client.get_waiter('table_exists').wait(TableName='test-table')
        assert self.table.table_status == 'ACTIVE'

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
        message_item = MessageItem(
            table=self.table,
            user_id=self.user_id,
            time=self.time,
            msg=self.msg,
            person=self.person
            )
        message_item_get = MessageItem(table=self.table, msg_id=message_item.id)
        self.assertEqual(message_item_get.time, self.time)
        self.assertEqual(len(message_item_get.id), 32)
    
    def test_message_delete(self):
        message_item = MessageItem(
            table=self.table,
            user_id=self.user_id,
            time=self.time,
            msg=self.msg,
            person=self.person
            )
        message_item_delete = MessageItem(table=self.table, msg_id=message_item.id)
        deleted = message_item_delete.delete()
        message_item_get = MessageItem(table=self.table, msg_id=message_item.id)
        self.assertTrue(deleted)
        self.assertEqual(message_item_get.user_id, None)
    
    def test_message_to_dict(self):
        message_item = MessageItem(
            table=self.table,
            user_id=self.user_id,
            time=self.time,
            msg=self.msg,
            person=self.person
            )
        dict = message_item.to_dict()
        self.assertEqual(dict['id'], message_item.id)
        self.assertEqual(dict['time'], message_item.time)
        self.assertEqual(dict['msg'], message_item.msg)
        self.assertEqual(dict['person'], message_item.person)