from datetime import datetime, timedelta
import uuid
import secrets
import pytz
from boto3.dynamodb.conditions import Key


# Session and token expiration constants
session_expiration_hours = 2
webex_token_expiration_days = 13

# Errors
auth_error = {'success': False, 'results': {'error': 'Authorization error.'}}
db_error = {'success': False, 'results': {'error': 'Database error.'}}


# DB Item Classes
class Item(object):
    def __init__(self, table):
        self.table = table

    def _create_item(self, item: dict) -> dict:
        try:
            resp = self.table.put_item(Item=item)
            return resp
        except Exception as e:
            print(e)
            return db_error

    def _get_item(self, key: dict) -> dict:
        try:
            resp = self.table.get_item(Key=key)
            return resp
        except Exception as e:
            print(e)
            return db_error

    def _query_item(self, key_cond_exp: Key) -> dict:
        try:
            resp = self.table.query(
                KeyConditionExpression=key_cond_exp
                )
            return resp
        except Exception as e:
            print(e)
            return db_error

    def _update_item(
            self,
            key: dict,
            update_exp: str,
            exp_attr_values: dict = None) -> dict:
        if exp_attr_values:
            try:
                resp = self.table.update_item(
                    Key=key,
                    UpdateExpression=update_exp,
                    ExpressionAttributeValues=exp_attr_values,
                    ReturnValues='ALL_NEW'
                    )
                return resp
            except Exception as e:
                print(e)
                return db_error
        else:
            try:
                resp = self.table.update_item(
                    Key=key,
                    UpdateExpression=update_exp,
                    ReturnValues='ALL_NEW'
                    )
                return resp
            except Exception as e:
                print(e)
                return db_error

    def _delete_item(self, key):
        try:
            # Delete user item
            self.table.delete_item(Key=key)
            return True
        except Exception as e:
            print(e)
            return False

    @staticmethod
    def is_datetime_expired(isoformat_string):
        # e.g. 2022-02-20T03:48:47.336062
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
    def get_session_expiration(hours):
        return datetime.utcnow() + timedelta(hours=hours)

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

    def create(self, delta=session_expiration_hours):
        # Create session token
        self.id = self.get_token()
        item = {
                'pk': f'sessionid#{self.id}',
                'sk': f'sessionid#{self.id}',
                'expires': self.get_session_expiration(delta).isoformat(),
                'user_id': self.user_id,
                'record_type': 'session',
                'id': self.id
        }
        self._create_item(item)
        return self.get()

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
        key = {
            'pk': f'sessionid#{self.id}',
            'sk': f'sessionid#{self.id}'
        }
        resp = self._delete_item(key)
        self.id = None
        self.expires = None
        self.user_id = None
        return resp


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

    @property
    def wbx_token_expired(self):
        if self.is_valid:
            return self.is_datetime_expired(self.wbx_token_expires)

    def create(self, days=webex_token_expiration_days):
        self.id = self.wbx_person.id
        item = {
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
        }
        self._create_item(item)
        return self.get()

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
        key = {
            'pk': f'userid#{self.id}',
            'sk': f'userid#{self.id}'
        }
        resp = self._delete_item(key)
        self.id = None,
        self.session_id = None
        self.displayname = None
        self.wbx_token = None
        self.wbx_token_expires = None
        self.messages = None
        self.is_valid = False
        return resp

    def update_wbx_token(self, wbx_token: str) -> dict:
        key = {'pk': f'userid#{self.id}', 'sk': f'userid#{self.id}'}
        update_exp = 'SET wbx_token = :i'
        exp_attr_values = {':i': wbx_token}
        self._update_item(key, update_exp, exp_attr_values)
        self._update_wbx_token_expiration(key)
        return self.get()

    def _update_wbx_token_expiration(
            self,
            key: dict,
            days: int = webex_token_expiration_days) -> None:
        wbx_token_expires = self.get_wbxtoken_expiration(days).isoformat()
        update_exp = 'SET wbx_token_expires = :i'
        exp_attr_values = {':i': wbx_token_expires}
        self._update_item(key, update_exp, exp_attr_values)

    def add_session(self, session_id):
        key = {'pk': f'userid#{self.id}', 'sk': f'userid#{self.id}'}
        update_exp = 'SET session_id = :i'
        exp_attr_values = {':i': session_id}
        self._update_item(key, update_exp, exp_attr_values)
        return self.get()

    def remove_session(self):
        key = {'pk': f'userid#{self.id}', 'sk': f'userid#{self.id}'}
        update_exp = 'REMOVE session_id'
        self._update_item(key, update_exp)
        self.session_id = None
        return self.get()

    def add_message(self, msg_id):
        key = {'pk': f'userid#{self.id}', 'sk': f'userid#{self.id}'}
        update_exp = 'SET messages = list_append(messages, :i)'
        exp_attr_values = {':i': [msg_id]}
        self._update_item(key, update_exp, exp_attr_values)
        return self.get()

    def remove_message(self, msg_id):
        # Remove given msg, update msg list on user item
        msgs = [m for m in self.messages if not m == msg_id]
        key = {'pk': f'userid#{self.id}', 'sk': f'userid#{self.id}'}
        update_exp = 'SET messages = :msgs'
        exp_attr_values = {':msgs': msgs}
        self._update_item(key, update_exp, exp_attr_values)
        return self.get()


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
        item = {
            'pk': f'message#{self.id}',
            'sk': self.time,
            'id': self.id,
            'msg': self.msg,
            'person': self.person,
            'user_id': self.user_id,
            'time': self.time,
            'record_type': 'message'
        }
        self._create_item(item)
        return self.get()

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
        key = {
            'pk': f'message#{self.id}',
            'sk': self.time
        }
        self._delete_item(key)
        self.id = None,
        self.user_id = None
        self.time = None
        self.msg = None
        self.person = None
        self.is_valid = False
        return True

    def to_dict(self):
        dict = {}
        dict['id'] = self.id
        dict['time'] = self.time
        dict['msg'] = self.msg
        dict['person'] = self.person
        return dict
