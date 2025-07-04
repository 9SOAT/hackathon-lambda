import unittest
from unittest.mock import patch, MagicMock
import lambda_listing
import json
import os

class TestLambdaHandler(unittest.TestCase):

    @patch('lambda_listing.boto3.resource')
    @patch.dict(os.environ, {'DDB_TABLE': 'MockTable'})
    def test_items_found(self, mock_boto3_resource):
        mock_table = MagicMock()
        mock_table.scan.side_effect = [
            {
                'Items': [{'user_id': 'abc123', 'status': 'active'}],
                'LastEvaluatedKey': {'someKey': 'value'}
            },
            {
                'Items': [{'user_id': 'abc123', 'status': 'archived'}]
            }
        ]
        mock_boto3_resource.return_value.Table.return_value = mock_table

        event = {
            'requestContext': {
                'authorizer': {
                    'jwt': {
                        'claims': {
                            'sub': 'abc123'
                        }
                    }
                }
            }
        }

        result = lambda_listing.lambda_handler(event, None)
        body = json.loads(result['body'])

        self.assertEqual(result['statusCode'], 200)
        self.assertIn('statusArchive', body)
        self.assertEqual(body['total'], 2)
        self.assertEqual(body['statusArchive'][0]['status'], 'active')
        self.assertEqual(body['statusArchive'][1]['status'], 'archived')

    @patch('lambda_listing.boto3.resource')
    @patch.dict(os.environ, {'DDB_TABLE': 'MockTable'})
    def test_no_items_found(self, mock_boto3_resource):
        # Mock da tabela retornando lista vazia
        mock_table = MagicMock()
        mock_table.scan.return_value = {'Items': []}
        mock_boto3_resource.return_value.Table.return_value = mock_table

        event = {
            'requestContext': {
                'authorizer': {
                    'jwt': {
                        'claims': {
                            'sub': 'user456'
                        }
                    }
                }
            }
        }

        result = lambda_listing.lambda_handler(event, None)
        body = json.loads(result['body'])

        self.assertEqual(result['statusCode'], 200)
        self.assertIn('message', body)
        self.assertEqual(body['message'], 'No items found for this user')

    @patch('lambda_listing.boto3.resource')
    @patch.dict(os.environ, {'DDB_TABLE': 'MockTable'})
    def test_error_handling(self, mock_boto3_resource):
        # Mock da tabela com erro no scan
        mock_table = MagicMock()
        mock_table.scan.side_effect = Exception('DynamoDB error')
        mock_boto3_resource.return_value.Table.return_value = mock_table

        event = {
            'requestContext': {
                'authorizer': {
                    'jwt': {
                        'claims': {
                            'sub': 'user789'
                        }
                    }
                }
            }
        }

        result = lambda_listing.lambda_handler(event, None)
        body = json.loads(result['body'])

        self.assertEqual(result['statusCode'], 500)
        self.assertIn('error', body)
        self.assertIn('DynamoDB error', body['error'])

if __name__ == '__main__':
    unittest.main()
