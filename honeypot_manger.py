#!/usr/bin/env python3
import os
import json
import argparse
import boto3
import datetime

def get_env_config():
    return {
        'min_honeypots': int(os.environ.get('MIN_HONEYPOTS', 3)),
        'included_regions': os.environ.get('INCLUDED_REGIONS', '').split(',') if os.environ.get('INCLUDED_REGIONS') else [],
        'excluded_regions': os.environ.get('EXCLUDED_REGIONS', '').split(',') if os.environ.get('EXCLUDED_REGIONS') else [],
        'sqs_queue_url': os.environ.get('SQS_QUEUE_URL', ''),
        's3_bucket': os.environ.get('S3_BUCKET', '')
    }

def get_status():
    """
    Query each in-scope region for EC2 instances tagged with application=honeypot.
    Returns a dictionary with the expected number of honeypots,
    the current count, and a list of instance details.
    """
    config = get_env_config()
    session = boto3.session.Session()
    # Determine regions based on included_regions if provided, else all available regions.
    all_regions = config['included_regions'] if config['included_regions'] else session.get_available_regions('ec2')
    regions = [r for r in all_regions if r not in config['excluded_regions']]
    
    honeypots = []
    for region in regions:
        ec2 = boto3.client('ec2', region_name=region)
        response = ec2.describe_instances(
            Filters=[
                {'Name': 'tag:application', 'Values': ['honeypot']},
                {'Name': 'instance-state-name', 'Values': ['pending', 'running']}
            ]
        )
        for reservation in response.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                launch_time = instance.get('LaunchTime')
                honeypots.append({
                    'instance_id': instance.get('InstanceId'),
                    'region': region,
                    'start_time': launch_time.isoformat() if launch_time else 'unknown'
                })
    return {
        'expected_honeypots': config['min_honeypots'],
        'current_count': len(honeypots),
        'honeypots': honeypots
    }

def fetch_spot_prices(regions):
    spot_prices = {}
    for region in regions:
        ec2 = boto3.client('ec2', region_name=region)
        # Simplified call: in production, refine filters for instance type, availability zone, etc.
        prices = ec2.describe_spot_price_history(
            InstanceTypes=['t3.micro'],
            ProductDescriptions=['Linux/UNIX'],
            MaxResults=1
        )
        if prices['SpotPriceHistory']:
            price = float(prices['SpotPriceHistory'][0]['SpotPrice'])
            spot_prices[region] = price
    return spot_prices

def deploy_honeypots():
    """
    Determine the cheapest region based on spot pricing, then deploy the required number
    of honeypot EC2 spot instances. Each instance is tagged with application=honeypot.
    """
    config = get_env_config()
    session = boto3.session.Session()
    all_regions = config['included_regions'] if config['included_regions'] else session.get_available_regions('ec2')
    regions = [r for r in all_regions if r not in config['excluded_regions']]
    
    # Retrieve spot pricing information.
    spot_prices = fetch_spot_prices(regions)
    if not spot_prices:
        return {"error": "No spot pricing data available."}
    
    # Select the region with the lowest spot price.
    cheapest_region = min(spot_prices, key=spot_prices.get)
    
    ec2 = boto3.client('ec2', region_name=cheapest_region)
    # Launch spot instance requests with the necessary tags.
    response = ec2.request_spot_instances(
        SpotPrice=str(spot_prices[cheapest_region]),
        InstanceCount=config['min_honeypots'],
        LaunchSpecification={
            'ImageId': 'ami-xxxxxxxx',  # Replace with the correct AMI ID.
            'InstanceType': 't3.micro',
            'IamInstanceProfile': {'Name': 'honeypot-instance-profile'},
            'UserData': '#!/bin/bash\necho "Honeypot instance launched"', # FIXME pull from S3s
            # Adding tag specifications so that the launched instance is tagged with application=honeypot.
            'TagSpecifications': [{
                'ResourceType': 'instance',
                'Tags': [{'Key': 'application', 'Value': 'honeypot'}]
            }]
        }
    )
    return {
        "message": f"Deployed honeypots in {cheapest_region}",
        "spot_request": response.get('SpotInstanceRequests', [])
    }

def process_event(event):
    mode = event.get('mode', 'status')
    if mode == 'deploy':
        result = deploy_honeypots()
    else:
        result = get_status()
    return result

def lambda_handler(event, context):
    return process_event(event)

def main():
    parser = argparse.ArgumentParser(description='Honeypot Manager CLI')
    parser.add_argument('--mode', type=str, default='status', help='Mode to run: status or deploy')
    args = parser.parse_args()
    
    event = {'mode': args.mode}
    result = process_event(event)
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()