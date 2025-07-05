import json
import boto3
import os
import logging
import time

BUCKET_NAME = os.environ.get('BUCKET_NAME', 'presigned-url-fiap-test')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info(f'Evento recebido: {json.dumps(event)}')
    s3_client = boto3.client('s3')

    try:
        user_id = event['requestContext']['authorizer']['jwt']['claims']['sub']
        timestamp_ms = int(time.time() * 1000)
        s3_key = f"{user_id}_{timestamp_ms}.mp4"
        email = event['requestContext']['authorizer']['jwt']['claims'].get('email', 'fiap.grupo.2024@gmail.com')
        
        logger.info(f'Gerando presigned URL para a key: {s3_key}')

        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': s3_key,
                'ContentType': 'application/octet-stream',
                'Metadata': {
                    'user-email': email
                }
            },
            ExpiresIn=3600
        )

        return {
            'statusCode': 200,
            'body': json.dumps({'presigned_url': presigned_url})
        }

    except Exception as e:
        logger.error(f'Erro ao gerar presigned URL: {str(e)}', exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Erro interno ao gerar presigned URL.'})
        }
