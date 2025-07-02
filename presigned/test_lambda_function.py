import json
import os
import boto3
import pytest
from unittest.mock import patch
from lambda_function import lambda_handler

from moto import mock_aws

@mock_aws
def test_example():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="my-bucket")

    event = {
        'requestContext': {
            'authorizer': {
                'jwt': {
                    'claims': {
                        'sub': 'user-123'
                    }
                }
            }
        }
    }

    response = lambda_handler(event, None)
    body = json.loads(response['body'])

    assert response['statusCode'] == 200
    assert 'presigned_url' in body
    assert body['presigned_url'].startswith('https://')

@patch.dict(os.environ, {"BUCKET_NAME": "test-bucket"})
def test_lambda_handler_error():
    # Evento malformado (sem JWT)
    event = {
        'requestContext': {
            'authorizer': {
                'jwt': {
                    'claims': {}
                }
            }
        }
    }

    response = lambda_handler(event, None)
    body = json.loads(response['body'])

    assert response['statusCode'] == 500
    assert 'error' in body
