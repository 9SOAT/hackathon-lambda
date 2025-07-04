import unittest
from unittest.mock import patch, MagicMock
import json
import os

from lambda_function import lambda_handler

class TestLambdaHandler(unittest.TestCase):

    @patch('boto3.resource')
    @patch('os.getenv')
    def test_lambda_handler_no_items(self, mock_getenv, mock_boto3_resource):
        mock_getenv.return_value = 'test_table'

        mock_table = MagicMock()
        mock_boto3_resource.return_value.Table.return_value = mock_table

        event = {
            'requestContext': {
                'authorizer': {
                    'jwt': {
                        'claims': {
                            'sub': 'test_user_id'
                        }
                    }
                }
            }
        }

        mock_table.scan.return_value = {
            'Items': [],
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(json.loads(response['body']), {'message': 'No items found for this user'})

    @patch('boto3.resource')
    @patch('os.getenv')
    def test_lambda_handler_with_items(self, mock_getenv, mock_boto3_resource):
        mock_getenv.return_value = 'test_table'

        mock_table = MagicMock()
        mock_boto3_resource.return_value.Table.return_value = mock_table

        event = {
            'requestContext': {
                'authorizer': {
                    'jwt': {
                        'claims': {
                            'sub': 'test_user_id'
                        }
                    }
                }
            }
        }

        mock_table.scan.side_effect = [
            {
                'Items': [{'status': 'active'}, {'status': 'inactive'}],
                'LastEvaluatedKey': {'some_key': 'some_value'}
            },
            {
                'Items': [{'status': 'pending'}],
            }
        ]

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['message'], 'Items retrieved successfully')
        self.assertEqual(body['statusArchive'], ['active', 'inactive', 'pending'])
        self.assertEqual(body['total'], 3)

    @patch('boto3.resource')
    @patch('os.getenv')
    def test_lambda_handler_exception(self, mock_getenv, mock_boto3_resource):
        mock_getenv.return_value = 'test_table'

        mock_table = MagicMock()
        mock_boto3_resource.return_value.Table.return_value = mock_table

        event = {
            'requestContext': {
                'authorizer': {
                    'jwt': {
                        'claims': {
                            'sub': 'test_user_id'
                        }
                    }
                }
            }
        }

        mock_table.scan.side_effect = Exception("DynamoDB error")

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 500)
        self.assertIn('Error listing items:', json.loads(response['body'])['error'])

if __name__ == '__main__':
    unittest.main()
