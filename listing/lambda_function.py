import boto3
import os
from boto3.dynamodb.conditions import Key
import json

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    table_name = os.getenv("DDB_TABLE")
    table = dynamodb.Table(table_name)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    try:
        # Scan with an optional limit
        response = table.scan(Limit=100)
        items = response.get('Items', [])
        processed_items = []

        while True:
            processed_items.extend(items)
            if 'LastEvaluatedKey' not in response:
                break
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'], Limit=100)
            items = response.get('Items', [])

        if not processed_items:
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No items found in table'})
            }

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Items recovered successfully',
                'items': processed_items,
                'total': len(processed_items)
            })
        }

    except Exception as e:
        logger.error(f'Error accessing DynamoDB: {str(e)}')
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Error listing items: {str(e)}'})
        }
