import boto3
import os
import logging
from boto3.dynamodb.conditions import Key
import json

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    table_name = os.getenv("DDB_TABLE")
    table = dynamodb.Table(table_name)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    try:
        user_id = event['requestContext']['authorizer']['jwt']['claims']['sub']

        response = table.scan(
            FilterExpression=Key('user_uuid').eq(user_id),
        )
        items = response.get('Items', [])
        processed_items = []

        while True:
            processed_items.extend(items)
            if 'LastEvaluatedKey' not in response:
                break
            response = table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey'],
                FilterExpression=Key('user_uuid').eq(user_id),
            )
            items = response.get('Items', [])

        if not processed_items:
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No items found for this user'})
            }

        status_archive = [{
            'status': item.get('status'),
            'timestamp': item.get('timestamp'),
            'input_key': item.get('input_key'),
            'output_key': item.get('output_key')
        } for item in processed_items]

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Items retrieved successfully',
                'statusArchive': status_archive,
                'total': len(status_archive)
            })
        }

    except Exception as e:
        logger.error(f'Error accessing DynamoDB: {str(e)}')
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Error listing items: {str(e)}'})
        }