from datetime import datetime, timedelta
import uuid
import secrets
import pytz
from boto3.dynamodb.conditions import Key


# Session and token expiration constants
session_expiration_days = 1
webex_token_expiration_days = 13

# Errors
auth_error = {'success': False, 'results': {'error': 'Authorization error.'}}
db_error = {'success': False, 'results': {'error': 'Database error.'}}


# DB Item Classes
class Item(object):
    def __init__(self, table):
        self.table = table

    def create():
        pass

    def _get_item(self, key_dict):
        try:
            resp = self.table.get_item(
                Key=key_dict
            )
            return resp
        except Exception as e:
            print(e)
            return db_error

    def _query_item(self, key_cond_exp):
        try:
            resp = self.table.query(
                KeyConditionExpression=key_cond_exp
                )
            return resp
        except Exception as e:
            print(e)
            return db_error

    def update():
        pass

    def delete():
        pass

    @staticmethod
    def is_datetime_expired(isoformat_string):
        dtobj = datetime.fromisoformat(isoformat_string)
        nowobj = datetime.fromisoformat(
            datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"))
        if dtobj > nowobj:
            return False
        else:
            return True

    @staticmethod
    def to_utc(dt, tz):
        dt = datetime.fromisoformat(dt)
        tz = pytz.timezone(tz)
        # Return timezone naive datetime string, ex. '2021-12-09T16:04:42'
        return tz.normalize(
            tz.localize(dt)).astimezone(
                pytz.utc).strftime("%Y-%m-%dT%H:%M:%S")

    @staticmethod
    def from_utc(dt, tz):
        dt = datetime.fromisoformat(dt)
        tz = pytz.timezone(tz)
        # Return timezone naive datetime string, ex. '2021-12-09T16:04:42'
        return tz.fromutc(dt).strftime("%Y-%m-%dT%H:%M:%S")

    @staticmethod
    def get_uuid():
        return uuid.uuid4().hex

    @staticmethod
    def get_token():
        return secrets.token_urlsafe()

    @staticmethod
    def get_wbxtoken_expiration(days):
        return datetime.utcnow() + timedelta(days=days)

    @staticmethod
    def get_session_expiration(days):
        return datetime.utcnow() + timedelta(days=days)

    def _reflect_item_attrs(self, d):
        if not isinstance(d, dict):
            return False
        for key in d.keys():
            setattr(self, key, d[key])
        return True


class SessionItem(Item):
    def __init__(self, table=None, session_id=None, user_id=None):
        super().__init__(table)
        self.id = session_id
        self.user_id = user_id
        self.is_valid = False
        if user_id:
            self.create()
        elif session_id:
            self.get()

    def redirect_resp(self, url):
        headers = {'Location': f'{url}?session={self.id}'}
        # Redirect to message page with session id in query param
        resp = {'body': '', 'status_code': 301, 'headers': headers}
        return resp

    @property
    def expired(self):
        return self.is_datetime_expired(self.expires)

    def create(self, days=session_expiration_days):
        # Create session token
        self.id = self.get_token()
        try:
            # Create the session item
            self.table.put_item(Item={
                'pk': f'sessionid#{self.id}',
                'sk': f'sessionid#{self.id}',
                'expires': self.get_session_expiration(days).isoformat(),
                'user_id': self.user_id,
                'record_type': 'session',
                'id': self.id
                })
            return self.get()
        except Exception as e:
            print(e)
            return db_error

    def get(self):
        key_dict = {
            'pk': f'sessionid#{self.id}',
            'sk': f'sessionid#{self.id}'
        }
        resp = self._get_item(key_dict)
        resp_item = resp.get('Item')
        if resp_item:
            self.is_valid = self._reflect_item_attrs(resp_item)
            return resp_item
        else:
            self.id = None
            self.expires = None
            self.user_id = None
            self.is_valid = False
            return resp

    def delete(self):
        try:
            # Delete session item
            self.table.delete_item(
                Key={
                    'pk': f'sessionid#{self.id}',
                    'sk': f'sessionid#{self.id}'
                }
            )
            self.id = None
            self.expires = None
            self.user_id = None
            return True
        except Exception as e:
            print(e)
            return False


class UserItem(Item):
    def __init__(
            self, table=None, user_id=None, wbx_person=None, wbx_token=None):
        super().__init__(table)
        self.id = user_id
        self.wbx_person = wbx_person
        self.wbx_token = wbx_token
        self.is_valid = False
        if user_id:
            self.get()
        elif wbx_person and wbx_token:
            self.create()

    def create(self, days=webex_token_expiration_days):
        try:
            # Create new user item
            self.id = self.wbx_person.id
            self.table.put_item(Item={
                'pk': f'userid#{self.id}',
                'sk': f'userid#{self.id}',
                'session_id': '',
                'displayname': self.wbx_person.nickName,
                'wbx_token': self.wbx_token,
                'wbx_token_expires':
                    self.get_wbxtoken_expiration(days).isoformat(),
                'messages': list(),
                'record_type': 'user',
                'id': self.id
            })
            return self.get()
        except Exception as e:
            print(e)
            return db_error

    def get(self):
        key_dict = {'pk': f'userid#{self.id}', 'sk': f'userid#{self.id}'}
        resp = self._get_item(key_dict)
        resp_item = resp.get('Item')
        if resp_item:
            self.is_valid = self._reflect_item_attrs(resp_item)
            return resp_item
        else:
            return resp

    def delete(self):
        try:
            # Delete user item
            self.table.delete_item(Key={
                'pk': f'userid#{self.id}',
                'sk': f'userid#{self.id}'
                }
            )
            self.id = None,
            self.session_id = None
            self.displayname = None
            self.wbx_token = None
            self.wbx_token_expires = None
            self.messages = None
            self.is_valid = False
            return True
        except Exception as e:
            print(e)
            return False

    def add_session(self, session_id):
        try:
            self.table.update_item(
                Key={'pk': f'userid#{self.id}', 'sk': f'userid#{self.id}'},
                UpdateExpression="SET session_id = :i",
                ExpressionAttributeValues={
                    ':i': session_id
                    },
                ReturnValues='ALL_NEW'
                )['Attributes']
            self.session_id = session_id
            return self.get()
        except Exception as e:
            print(e)
            return db_error

    def remove_session(self):
        try:
            # Update user to remove pointer to session_id item
            self.table.update_item(
                Key={'pk': f'userid#{self.id}', 'sk': f'userid#{self.id}'},
                UpdateExpression="REMOVE session_id",
                ReturnValues='ALL_NEW'
                )['Attributes']
            self.session_id = None
            return self.get()
        except Exception as e:
            print(e)
            return db_error

    def add_message(self, msg_id):
        try:
            # Update the user item with a pointer to the message item
            self.table.update_item(
                Key={'pk': f'userid#{self.id}', 'sk': f'userid#{self.id}'},
                UpdateExpression="SET messages = list_append(messages, :i)",
                ExpressionAttributeValues={
                    ':i': [msg_id]
                },
                ReturnValues='ALL_NEW'
                )['Attributes']
            return self.get()
        except Exception as e:
            print(e)
            return db_error

    # Needs testing
    def remove_message(self, msg_id):
        msgs = [m for m in self.messages if not m == msg_id]
        try:
            # Update message list without a given message
            self.table.update_item(
                Key={'pk': f'userid#{self.id}', 'sk': f'userid#{self.id}'},
                UpdateExpression="SET messages = :msgs",
                ExpressionAttributeValues={
                    ':msgs': msgs
                },
                ReturnValues='ALL_NEW'
                )['Attributes']
            return self.get()
        except Exception as e:
            print(e)
            return db_error


class MessageItem(Item):
    def __init__(
            self,
            table=None,
            msg_id=None,
            user_id=None,
            time=None,
            msg=None,
            person=None,
            index_name=None):
        super().__init__(table)
        self.id = msg_id
        self.user_id = user_id
        self.time = time
        self.msg = msg
        self.person = person
        self.is_valid = False
        self.index_name = index_name
        if user_id and time and msg and person:
            self.create()
        elif msg_id:
            self.get()

    @property
    def expired(self):
        return self.is_datetime_expired(self.time)

    def create(self):
        self.id = self.get_uuid()
        try:
            self.table.put_item(Item={
                'pk': f'message#{self.id}',
                'sk': self.time,
                'id': self.id,
                'msg': self.msg,
                'person': self.person,
                'user_id': self.user_id,
                'time': self.time,
                'record_type': 'message'
                })
            return self.get()
        except Exception as e:
            print(e)
            return db_error

    def get(self):
        key_exp = Key('pk').eq(f'message#{self.id}')
        resp = self._query_item(key_exp)
        resp_items = resp.get('Items')
        if resp_items:
            resp_item = resp_items[0]
            self.is_valid = self._reflect_item_attrs(resp_item)
            return resp_item
        else:
            return resp_items

    def delete(self):
        try:
            # Delete message item
            self.table.delete_item(Key={
                'pk': f'message#{self.id}',
                'sk': self.time
                }
            )
            self.id = None,
            self.user_id = None
            self.time = None
            self.msg = None
            self.person = None
            self.is_valid = False
            return True
        except Exception as e:
            print(e)
            return False

    def to_dict(self):
        dict = {}
        dict['id'] = self.id
        dict['time'] = self.time
        dict['msg'] = self.msg
        dict['person'] = self.person
        return dict
