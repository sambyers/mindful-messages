import boto3
import os
import epsagon
import bleach
from webexteamssdk import WebexTeamsAPI
from chalice import Chalice, Response, CORSConfig
from chalicelib import UserItem, SessionItem, MessageItem


# Environmental variables of the lambda function
client_id = os.environ['OAUTH_CLIENT_ID']
client_secret = os.environ['OAUTH_CLIENT_SECRET']
redirect_uri = os.environ['OAUTH_REDIRECT_URI']
table_name = os.environ['TABLE_NAME']
cors_allow_origin = os.environ['CORS_ALLOW_ORIGIN']
redirect_resp_url = cors_allow_origin + '/index.html'
epsagon_token = os.environ['EPSAGON_TOKEN']
app_name = os.environ['APP_NAME']
allowed_domains = os.environ['ALLOWED_DOMAINS']
allowed_domains = allowed_domains.split(',')

epsagon.init(
  token=epsagon_token,
  app_name=app_name,
  metadata_only=False
  )

app = Chalice(app_name=app_name)

cors_config = CORSConfig(
    allow_origin=cors_allow_origin
)

# Errors
auth_error = {'success': False, 'results': {'error': 'Authorization error.'}}
db_error = {'success': False, 'results': {'error': 'Database error.'}}


# Helper functions
def error_response(results=None):
    return {'success': False, 'results': results}


def success_response(results=None):
    return {'success': True, 'results': results}


def authorize(code):
    wbxapi = WebexTeamsAPI(client_id=client_id,
                           client_secret=client_secret,
                           oauth_code=code,
                           redirect_uri=redirect_uri
                           )
    return wbxapi


def get_table(table_name=table_name):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    return table


def is_domain_allowed(domains, emails):
    # Poor speed here but lists are expected to be short
    for email in emails:
        for domain in domains:
            if domain in email:
                return True
    return False


def delete_state(table, state):
    try:
        # Delete ephemeral OAuth2 state
        resp = table.delete_item(Key={'pk': state, 'sk': state})
        return resp
    except Exception as e:
        print(e)
        return auth_error


# App routes
# Form and respond with the Webex authorizer link, store ephemeral OAuth2 state
@app.route('/wbxauth', methods=['GET'], cors=cors_config)
def wbxauth():
    oauth_state = UserItem.get_token()
    try:
        get_table().put_item(Item={'pk': f'state#{oauth_state}',
                                   'sk': f'state#{oauth_state}'})
        authorizer_url = (f'https://webexapis.com/v1/authorize'
                          f'?client_id={client_id}'
                          f'&response_type=code&redirect_uri={redirect_uri}'
                          f'&scope=spark%3Akms%20spark%3Apeople_read%20'
                          f'spark%3Amessages_write'
                          f'&state={oauth_state}')
        return {'success': True, 'results': {'location': authorizer_url}}
    except Exception as e:
        print(e)
        return db_error


# Authorizer for Webex accounts.
# State is verified, a session is created, and a Webex token is created.
@app.route('/auth', methods=['GET'])
def auth():
    # Get request dict
    request = app.current_request
    # Get ephemeral state to verify correct OAuth flow
    state = bleach.clean(request.query_params.get('state'))
    try:
        # Get the ephemeral state from the db
        oauth_state = get_table().get_item(Key={
            'pk': f'state#{state}', 'sk': f'state#{state}'})['Item']['pk']
    except Exception as e:
        print(e)
        return db_error
    # Verify state is the same between request and db
    if 'code' in request.query_params and f'state#{state}' == oauth_state:
        # Get OAuth granted code from query params
        code = request.query_params.get('code')
        wbxapi = None
        wbxapi = authorize(code)
    if wbxapi:
        person = wbxapi.people.me()
        table = get_table()
        if not is_domain_allowed(allowed_domains, person.emails):
            delete_state(table, oauth_state)
            return {'success': False, 'results': {'error': 'Not allowed.'}}
        delete_state(table, oauth_state)
        user_item = UserItem(table=table, user_id=person.id)
        # User and Session exists
        if user_item.is_valid and user_item.session_id:
            session_item = SessionItem(
                table=table, session_id=user_item.session_id
                )
            if session_item.is_valid:
                # If the session is expired, delete it user and table
                if session_item.expired:
                    session_item.delete()
                    new_session_item = SessionItem(table=table,
                                                   user_id=user_item.id)
                    user_item.add_session(new_session_item.id)
                    return Response(
                        **new_session_item.redirect_resp(redirect_resp_url))
                else:
                    return Response(
                        **session_item.redirect_resp(redirect_resp_url))
            else:
                new_session_item = SessionItem(
                    table=table, user_id=user_item.id)
                user_item.add_session(new_session_item.id)
                return Response(
                    **new_session_item.redirect_resp(redirect_resp_url))
        # User exists but no session, create session and add to user
        elif user_item.is_valid:
            session_item = SessionItem(table=table, user_id=user_item.id)
            user_item.add_session(session_item.id)
            return Response(**session_item.redirect_resp(redirect_resp_url))
        # No user or session exists, create both
        else:
            new_user_item = UserItem(
                table=table, wbx_person=person,
                wbx_token=wbxapi.access_token)
            session_item = SessionItem(
                table=table, user_id=new_user_item.id)
            new_user_item.add_session(session_item.id)
            return Response(**session_item.redirect_resp(redirect_resp_url))
    else:
        # Failure due to Webex API object not existing
        return {
            'success': False,
            'results': {'error': 'Webex authorization failed.'}}


# Get the username given a session ID in the query params
@app.route('/user', methods=['GET'], cors=cors_config)
def get_user():
    request = app.current_request
    session_id = bleach.clean(request.query_params.get('session'))
    try:
        session_item = SessionItem(table=get_table(), session_id=session_id)
        if session_item.expired:
            session_item.delete()
            return {'success': False, 'results': 'Session Expired.'}
        else:
            user_item = UserItem(
                table=get_table(), user_id=session_item.user_id)
            return {
                'success': True,
                'results': {'username': user_item.displayname}}
    except Exception as e:
        print(e)
        return {'success': False, 'results': {'error': 'Database error.'}}


# Delete the user given a session ID in the query params
@app.route('/user', methods=['DELETE'], cors=cors_config)
def delete_user():
    request = app.current_request
    session_id = bleach.clean(request.query_params.get('session'))
    try:
        session_item = SessionItem(table=get_table(), session_id=session_id)
        if session_item.expired:
            session_item.delete()
            return {'success': False, 'results': 'Session Expired.'}
        else:
            user_item = UserItem(
                table=get_table(), user_id=session_item.user_id)
            if user_item.is_valid:
                if hasattr(user_item, 'messages'):
                    # For each msg ID in the user item, get item and delete it
                    for message_id in user_item.messages:
                        message_item = MessageItem(
                            table=get_table(), msg_id=message_id)
                        if message_item.is_valid:
                            message_item.delete()
                if user_item.delete():
                    return {'success': True, 'results': 'User deleted.'}
                else:
                    return {'success': False, 'results': 'User not deleted.'}
    except Exception as e:
        print(e)
        return db_error


# Logout the user session given a session ID in the query params
@app.route('/logout', methods=['GET'], cors=cors_config)
def logout():
    request = app.current_request
    # Get sessionid query parameter from the request
    session_id = bleach.clean(request.query_params.get('session'))
    session_item = SessionItem(table=get_table(), session_id=session_id)
    if session_item.delete():
        return {'success': True}


# Schedule a message to send at a later date and time given a session id
@app.route('/schedule', methods=['POST'], cors=cors_config)
def schedule():
    request = app.current_request
    # Get the session id from query parameters
    session_id = request.query_params.get('session')
    # Get the json body and the message details
    req_data = request.json_body
    message_txt = bleach.clean(req_data.get('msg'))
    message_datetime = bleach.clean(req_data.get('time'))
    message_recipient = bleach.clean(req_data.get('person'))
    message_timezone = bleach.clean(req_data.get('timezone'))
    message_datetime_utc = MessageItem.to_utc(
        message_datetime, message_timezone)
    session_item = SessionItem(table=get_table(), session_id=session_id)

    if session_item.expired:
        session_item.delete()
        return {'success': False, 'results': 'Session Expired.'}
    else:
        user_item = UserItem(table=get_table(), user_id=session_item.user_id)
        msg_item = MessageItem(
            table=get_table(),
            user_id=user_item.id,
            time=message_datetime_utc,
            msg=message_txt,
            person=message_recipient)
        user_item.add_message(msg_item.id)
        return {'success': True}


# Return list of messages given a sessionid
@app.route('/messages', methods=['GET'], cors=cors_config)
def messages():
    request = app.current_request
    # Get the session id from query parameters
    session_id = bleach.clean(request.query_params.get('session'))
    # timezone = request.query_params.get('timezone')
    session_item = SessionItem(table=get_table(), session_id=session_id)
    if session_item.expired:
        session_item.delete()
        return {'success': False, 'results': 'Session Expired.'}
    else:
        user_item = UserItem(table=get_table(), user_id=session_item.user_id)
        results = []
        if hasattr(user_item, 'messages'):
            # For each msg ID in user item, get msg item and append to list
            for message_id in user_item.messages:
                message_item = MessageItem(
                    table=get_table(), msg_id=message_id)
                if message_item.is_valid:
                    if not message_item.is_datetime_expired(message_item.time):
                        msg_dict = message_item.to_dict()
                        # time = msg_dict['time']
                        # time = message_item.from_utc(time, timezone)
                        # msg_dict['time'] = time
                        results.append(msg_dict)
        return {'success': True, 'results': results}


# Delete message given a message ID and session ID
@app.route('/message', methods=['DELETE'], cors=cors_config)
def message():
    request = app.current_request
    # Get the session id and message id from query parameters
    session_id = bleach.clean(request.query_params.get('session'))
    message_id = bleach.clean(request.query_params.get('message'))
    session_item = SessionItem(table=get_table(), session_id=session_id)
    if session_item.expired:
        session_item.delete()
        return {'success': False, 'results': 'Session Expired.'}
    else:
        message_item = MessageItem(table=get_table(), msg_id=message_id)
        if message_item.is_valid:
            if message_item.delete():
                user_item = UserItem(table=get_table(),
                                     user_id=session_item.user_id)
                user_item.remove_message(message_id)
                return {'success': True, 'results': 'Message deleted.'}
            else:
                return {'success': False, 'results': 'Message not deleted.'}
        else:
            return {'success': True, 'results': 'Message does not exist.'}


@app.route('/people', methods=['GET'], cors=cors_config)
def people():
    request = app.current_request
    # Get the session id and person query from query parameters
    session_id = bleach.clean(request.query_params.get('session'))
    query = request.query_params.get('q')
    query = bleach.clean(str(query))
    session_item = SessionItem(table=get_table(), session_id=session_id)
    if session_item.expired:
        session_item.delete()
        return {'success': False, 'results': 'Session Expired.'}
    user_item = None
    wbxapi = None
    results = []
    if all(chr.isalpha() or chr.isspace() for chr in query):
        user_item = UserItem(table=get_table(), user_id=session_item.user_id)
    if user_item:
        if user_item.is_valid and not user_item.is_datetime_expired(
                user_item.wbx_token_expires):
            wbxapi = WebexTeamsAPI(access_token=user_item.wbx_token)
    if wbxapi:
        people = wbxapi.people.list(displayName=query)
        for person in people:
            result = {}
            result['displayname'] = person.displayName
            result['email'] = person.emails[0]
            results.append(result)
    if len(results) > 0:
        return {'success': True, 'results': results}
    else:
        return {'success': False, 'results': 'No results.'}


# Epsagon monitoring
app = epsagon.chalice_wrapper(app)
