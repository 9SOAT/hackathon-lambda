import json
import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from main import send_templated_email, lambda_handler, process_message

@patch('main.ses_client')
def test_send_templated_email_successful(mock_ses_client):
    # Setup mock response
    mock_ses_client.send_templated_email.return_value = {'MessageId': '123456789'}

    # Call function
    result = send_templated_email(
        'recipient@example.com',
        'welcome_template',
        'sender@example.com',
        {'name': 'John', 'company': 'ACME'}
    )

    # Verify SES client was called correctly
    mock_ses_client.send_templated_email.assert_called_once_with(
        Source='sender@example.com',
        Destination={
            'ToAddresses': ['recipient@example.com'],
        },
        Template='welcome_template',
        TemplateData=json.dumps({'name': 'John', 'company': 'ACME'})
    )

    # Verify result
    assert result['statusCode'] == 200
    assert json.loads(result['body'])['message'] == 'Email sent successfully!'

@patch('main.ses_client')
def test_send_templated_email_handles_client_error(mock_ses_client):
    # Setup mock error
    error_response = {
        'Error': {
            'Message': 'Template does not exist'
        }
    }
    mock_ses_client.send_templated_email.side_effect = ClientError(
        error_response, 'SendTemplatedEmail'
    )

    # Call function
    result = send_templated_email(
        'recipient@example.com',
        'nonexistent_template',
        'sender@example.com',
        {'name': 'John'}
    )

    # Verify result contains error
    assert result['statusCode'] == 400
    assert json.loads(result['body'])['error_message'] == 'Template does not exist'

def test_lambda_handler_processes_all_records():
    # Setup mock event
    event = {
        'Records': [
            {'id': '1', 'body': '{"data": "message1"}'},
            {'id': '2', 'body': '{"data": "message2"}'}
        ]
    }

    with patch('main.process_message') as mock_process:
        # Call handler
        lambda_handler(event, None)

        # Verify each record was processed
        assert mock_process.call_count == 2
        mock_process.assert_any_call({'id': '1', 'body': '{"data": "message1"}'})
        mock_process.assert_any_call({'id': '2', 'body': '{"data": "message2"}'})

@patch('main.send_templated_email')
def test_process_message_with_valid_input(mock_send):
    # Setup mock
    mock_send.return_value = {
        "statusCode": 200,
        "body": json.dumps({'message': 'Email sent successfully!'})
    }

    # Setup message
    message = {
        'body': json.dumps({
            'receiver_email': 'test@example.com',
            'sender_email': 'sender@example.com',
            'template_name': 'welcome_template',
            'placeholders': {'name': 'John', 'company': 'ACME'}
        })
    }

    # Call function
    result = process_message(message)

    # Verify templated email was sent with correct parameters
    mock_send.assert_called_once_with(
        'test@example.com',
        'welcome_template',
        'sender@example.com',
        {'name': 'John', 'company': 'ACME'}
    )

    # Verify result
    assert result['statusCode'] == 200
    assert json.loads(result['body'])['message'] == 'Email sent successfully!'

def test_process_message_missing_receiver_email():
    # Setup message with missing receiver_email
    message = {
        'body': json.dumps({
            'sender_email': 'sender@example.com',
            'template_name': 'welcome_template',
            'placeholders': {'name': 'John'}
        })
    }

    # Call function
    result = process_message(message)

    # Verify error response
    assert result['statusCode'] == 400
    assert 'Missing key' in json.loads(result['body'])['error_message']

def test_process_message_missing_sender_email():
    # Setup message with missing sender_email
    message = {
        'body': json.dumps({
            'receiver_email': 'test@example.com',
            'template_name': 'welcome_template',
            'placeholders': {'name': 'John'}
        })
    }

    # Call function
    result = process_message(message)

    # Verify error response
    assert result['statusCode'] == 400
    assert 'Missing key' in json.loads(result['body'])['error_message']

def test_process_message_missing_template_name():
    # Setup message with missing template_name
    message = {
        'body': json.dumps({
            'receiver_email': 'test@example.com',
            'sender_email': 'sender@example.com',
            'placeholders': {'name': 'John'}
        })
    }

    # Call function
    result = process_message(message)

    # Verify error response
    assert result['statusCode'] == 400
    assert 'Missing key' in json.loads(result['body'])['error_message']

def test_process_message_missing_placeholders():
    # Setup message with missing placeholders
    message = {
        'body': json.dumps({
            'receiver_email': 'test@example.com',
            'sender_email': 'sender@example.com',
            'template_name': 'welcome_template'
        })
    }

    # Call function
    result = process_message(message)

    # Verify error response
    assert result['statusCode'] == 400
    assert 'Missing key' in json.loads(result['body'])['error_message']

def test_process_message_with_invalid_json():
    # Setup message with invalid JSON
    message = {
        'body': 'This is not valid JSON'
    }

    # Call function
    result = process_message(message)

    # Verify error response
    assert result['statusCode'] == 400
    assert 'error_message' in json.loads(result['body'])

@patch('main.send_templated_email')
def test_process_message_with_complex_placeholders(mock_send):
    # Setup mock
    mock_send.return_value = {
        "statusCode": 200,
        "body": json.dumps({'message': 'Email sent successfully!'})
    }

    # Setup complex placeholders
    complex_placeholders = {
        'user': {'name': 'Alice', 'id': 123},
        'order': {
            'items': [
                {'product': 'Widget', 'qty': 2, 'price': 19.99},
                {'product': 'Gadget', 'qty': 1, 'price': 59.99}
            ],
            'total': 99.97
        },
        'shipping': {
            'address': '123 Main St',
            'city': 'Anytown',
            'country': 'USA'
        }
    }

    # Setup message
    message = {
        'body': json.dumps({
            'receiver_email': 'complex@example.com',
            'sender_email': 'orders@example.com',
            'template_name': 'order_confirmation',
            'placeholders': complex_placeholders
        })
    }

    # Call function
    result = process_message(message)

    # Verify correct parameters passed
    mock_send.assert_called_once_with(
        'complex@example.com',
        'order_confirmation',
        'orders@example.com',
        complex_placeholders
    )

    # Verify result
    assert result['statusCode'] == 200
