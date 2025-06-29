import json

import boto3
from botocore.exceptions import ClientError

# Initialize the SES client.
# If you're running the function locally, make sure your AWS credentials are set up (e.g., via `~/.aws/credentials`
# If you're running this on AWS Lambda, ensure the execution role has permissions to use SES.
ses_client = boto3.client('ses')  # Adjust the region if necessary.

def send_templated_email(receiver_email: str, template_name: str, sender_email: str, template_data: dict):
    print(f"Sending email to {receiver_email} using template {template_name} from {sender_email} with data: {template_data}")
    try:
        response = ses_client.send_templated_email(
            Source=sender_email,
            Destination={
                'ToAddresses': [
                    receiver_email,
                ],
            },
            Template=template_name,
            TemplateData=json.dumps(template_data)
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
        return {
            "statusCode": 400,
            "body": json.dumps({'error_message': e.response['Error']['Message']})
        }

    print("Email sent! Message ID:", response['MessageId'])
    return {
        "statusCode": 200,
        "body": json.dumps({'message': 'Email sent successfully!'})
    }

def lambda_handler(event, context):
    for message in event['Records']:
        process_message(message)
    print("Messages processed successfully.")

def process_message(message):
    
    try:
        message_body = json.loads(message['body'])
        receiver_email = message_body["receiver_email"]
        sender_email = message_body["sender_email"]
        template_name = message_body["template_name"]
        placeholders = message_body["placeholders"]

        return send_templated_email(receiver_email, template_name, sender_email, placeholders)
    except Exception as e:
        return {
            "statusCode": 400,
            "body": json.dumps({'error_message': f'Missing key in input: {str(e)}'})
        }
