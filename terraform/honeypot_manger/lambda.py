#!/usr/bin/env python3
import os
import boto3
import json
import subprocess

def sync_to_s3():
    s3_bucket = os.environ.get('S3_BUCKET', '')
    # Use AWS CLI to sync the /honeypot directory to S3.
    subprocess.run(['aws', 's3', 'sync', '/honeypot', f's3://{s3_bucket}/honeypot'], check=True)

def notify_sqs(instance_details):
    sqs_queue_url = os.environ.get('SQS_QUEUE_URL', '')
    sqs = boto3.client('sqs')
    message = json.dumps(instance_details)
    sqs.send_message(
        QueueUrl=sqs_queue_url,
        MessageBody=message
    )

def main():
    # Retrieve instance details; in production, these might be obtained via instance metadata.
    instance_details = {
        'instance_id': os.environ.get('INSTANCE_ID', 'unknown'),
        'region': os.environ.get('AWS_REGION', 'unknown'),
        'termination_time': 'imminent'
    }
    sync_to_s3()
    notify_sqs(instance_details)

if __name__ == '__main__':
    main()