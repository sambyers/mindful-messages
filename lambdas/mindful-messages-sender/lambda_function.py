import os
import epsagon
import boto3
from boto3.dynamodb.conditions import Key
from webexteamssdk import WebexTeamsAPI
from models import MessageItem, UserItem
from datetime import datetime


table_name = os.environ['TABLE_NAME']
index_name = os.environ['INDEX_NAME']
epsagon_token = os.environ['EPSAGON_TOKEN']
app_name = os.environ['APP_NAME']

epsagon.init(
    token=epsagon_token,
    app_name=app_name,
    metadata_only=False,
)


def get_table(table_name=table_name):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    return table


def get_msgs_by_datetime(table, index_name, isoformat_string):
    resp = table.query(
        # Add the name of the index you want to use in your query.
        IndexName=index_name,
        KeyConditionExpression=Key('record_type').eq('message') &
        Key('sk').begins_with(isoformat_string)
    )
    return resp['Items']


@epsagon.lambda_wrapper
def lambda_handler(event, context):
    # 10 minute
    # datetime_search_string = datetime.utcnow().strftime(
    #   "%Y-%m-%dT%H:%M")[:-1]
    # 1 hour
    datetime_search_string = datetime.utcnow().strftime("%Y-%m-%dT%H:")
    msgs = get_msgs_by_datetime(
        get_table(), index_name, datetime_search_string)
    results = []
    for msg in msgs:
        user_id = msg.get('userid')
        message_id = msg.get('messageid')
        message_item = MessageItem(table=get_table(), msg_id=message_id)
        if message_item.is_valid and message_item.expired:
            user_item = UserItem(table=get_table(), user_id=user_id)
            wbxapi = WebexTeamsAPI(access_token=user_item.wbx_token)
            wbxapi.messages.create(
                toPersonEmail=message_item.person, text=message_item.msg)
            user_item.remove_message(message_item.id)
            message_item.delete()
            results.append(msg)
    return {'message count': len(results)}
