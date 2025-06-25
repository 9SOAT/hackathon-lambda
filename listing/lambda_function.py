import boto3
import os
from boto3.dynamodb.conditions import Key
import json

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')

    table_name = os.getenv("DDB_TABLE")
    table = dynamodb.Table(table_name)

    try:
        response = table.scan()

        items = response.get('Items', [])

        if not items:
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No items found in table'})
            }

        processed_items = []
        for item in items:
            processed_items.append(item)

        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response.get('Items', []))

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Items recovered successfully',
                'items': processed_items,
                'total': len(items)
            })
        }

    except Exception as e:
        print(f'Error accessing DynamoDB: {str(e)}')
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error listing items: {str(e)}')
        }
