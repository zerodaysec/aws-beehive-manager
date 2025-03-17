#!/usr/bin/env python3
import boto3
import time
from datetime import datetime, timezone
import argparse

# =======================
# Configuration Variables (defaults)
# =======================
AWS_REGION = "us-west-2"
INSTANCE_TYPE = "t3.micro"
# AMI name uses the current UTC timestamp; will be updated in main()
AMI_NAME = f"aws-beehive-honeypot-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
TARGET_REGIONS = [
    "us-east-1",
    "us-east-2",
    "us-west-1",
    "eu-west-1",
    "eu-central-1",
    "ap-southeast-1",
    "ap-southeast-2",
    "ap-northeast-1",
    "ap-northeast-2",
    "sa-east-1",
]
# S3 details for the termination_handler script
S3_BUCKET = "aws-beehive-tools-us-west-2"
HANDLER_KEY = "latest/termination_handler.py"
# SSH key name to be used when launching the EC2 instance
SSH_KEY_NAME = "your-ssh-key"  # Replace with your key name or set to None if not needed

# SOURCE_AMI will be determined dynamically based on the base_ami_type
SOURCE_AMI = None

# =======================
# Helper Functions
# =======================


def get_latest_ami(base_ami_type, region):
    """
    Searches for the latest AMI of the specified base type in the given region.
    Supported types: Ubuntu, AmazonLinux2.
    """
    ec2 = boto3.client("ec2", region_name=region)
    if base_ami_type.lower() == "ubuntu":
        filters = [
            {
                "Name": "name",
                "Values": ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"],
            },
            {"Name": "architecture", "Values": ["x86_64"]},
        ]
        owners = ["099720109477"]
    elif base_ami_type.lower() == "amazonlinux2":
        filters = [
            {"Name": "name", "Values": ["amzn2-ami-hvm-*-x86_64-ebs"]},
            {"Name": "architecture", "Values": ["x86_64"]},
        ]
        owners = ["137112412989"]
    else:
        raise ValueError(f"Unsupported base_ami_type: {base_ami_type}")

    response = ec2.describe_images(Owners=owners, Filters=filters)
    images = response.get("Images", [])
    if not images:
        raise Exception(
            f"No AMIs found for base type {base_ami_type} in region {region}"
        )

    # Sort images by CreationDate descending and return the latest one
    images.sort(key=lambda x: x["CreationDate"], reverse=True)
    latest_ami = images[0]["ImageId"]
    print(f"Latest {base_ami_type} AMI in {region}: {latest_ami}")
    return latest_ami


def get_user_data():
    """
    Returns the user data script that installs Python3, boto3, downloads the termination_handler,
    and sets it up to run as a systemd service on boot.
    """
    user_data = f"""#!/bin/bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip awscli
sudo pip3 install boto3
sudo mkdir -p /usr/local/bin
sudo aws s3 cp s3://{S3_BUCKET}/{HANDLER_KEY} /usr/local/bin/termination_handler.py
sudo chmod +x /usr/local/bin/termination_handler.py
sudo bash -c 'cat > /etc/systemd/system/termination_handler.service <<EOF
[Unit]
Description=Termination Handler Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/termination_handler.py
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF'
sudo systemctl enable termination_handler.service
"""
    return user_data


# In the launch_instance function definition, update the signature and parameters:
def launch_instance(key_name, instance_profile):
    """
    Launch an EC2 instance in AWS_REGION with the determined SOURCE_AMI, instance type,
    user data script, optional SSH key, and the specified IAM instance profile.
    Returns the instance ID.
    """
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    params = {
        "ImageId": SOURCE_AMI,
        "InstanceType": INSTANCE_TYPE,
        "MinCount": 1,
        "MaxCount": 1,
        "UserData": get_user_data(),
        "IamInstanceProfile": {"Name": instance_profile},
    }
    if key_name:
        params["KeyName"] = key_name
    response = ec2.run_instances(**params)
    instance_id = response["Instances"][0]["InstanceId"]
    print(f"Launched instance: {instance_id}")
    return instance_id


def wait_for_instance(instance_id):
    """
    Wait until the instance is in the 'running' state.
    """
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    print(f"Waiting for instance {instance_id} to reach running state...")
    waiter = ec2.get_waiter("instance_running")
    waiter.wait(InstanceIds=[instance_id])
    print(f"Instance {instance_id} is running.")


def create_ami(instance_id):
    """
    Create an AMI from the given instance and wait for it to become available.
    Returns the AMI ID.
    """
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    print(f"Creating AMI from instance {instance_id}...")
    response = ec2.create_image(
        InstanceId=instance_id,
        Name=AMI_NAME,
        Description="AMI with termination_handler installed; runs on boot using systemd",
        NoReboot=True,
    )
    ami_id = response["ImageId"]
    print(f"AMI creation initiated: {ami_id}")
    print(f"Waiting for AMI {ami_id} to become available...")
    waiter = ec2.get_waiter("image_available")
    waiter.wait(ImageIds=[ami_id])
    print(f"AMI {ami_id} is now available.")
    return ami_id


def copy_ami_to_regions(ami_id, target_regions):
    """
    Copies the given AMI to the list of target regions.
    Returns a dictionary mapping region to the new AMI ID.
    """
    copied_amis = {}
    for region in target_regions:
        ec2 = boto3.client("ec2", region_name=region)
        print(f"Copying AMI {ami_id} to region {region}...")
        response = ec2.copy_image(
            SourceRegion=AWS_REGION,
            SourceImageId=ami_id,
            Name=AMI_NAME,
            Description="Copied AMI with termination_handler installed; runs on boot using systemd",
        )
        new_ami_id = response["ImageId"]
        print(f"Copied AMI in {region}: {new_ami_id}")
        print(f"Waiting for AMI {new_ami_id} in region {region} to become available...")
        waiter = ec2.get_waiter("image_available")
        waiter.wait(ImageIds=[new_ami_id])
        print(f"AMI {new_ami_id} in region {region} is available.")
        copied_amis[region] = new_ami_id
    return copied_amis


def make_ami_public(region, ami_id):
    """
    Modify the AMI attribute in the given region to allow public launch (shared with all AWS accounts).
    """
    ec2 = boto3.client("ec2", region_name=region)
    print(f"Making AMI {ami_id} in region {region} public...")
    ec2.modify_image_attribute(
        ImageId=ami_id, LaunchPermission={"Add": [{"Group": "all"}]}
    )
    print(f"AMI {ami_id} in region {region} is now public.")


def terminate_instance(instance_id):
    """
    Terminate the given instance.
    """
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    print(f"Terminating instance {instance_id}...")
    ec2.terminate_instances(InstanceIds=[instance_id])
    print(f"Instance {instance_id} termination initiated.")


# =======================
# Main Process
# =======================


def main():
    parser = argparse.ArgumentParser(description="AMI Maker")
    parser.add_argument(
        "--aws_region", default="us-west-2", help="AWS region to launch the instance"
    )
    parser.add_argument(
        "--base_ami_type",
        default="Ubuntu",
        choices=["Ubuntu", "AmazonLinux2"],
        help="Base AMI type to search for the latest AMI",
    )
    parser.add_argument("--instance_type", default="t3.micro", help="EC2 instance type")
    parser.add_argument(
        "--ssh_key_name",
        default="your-ssh-key",
        help="SSH key name for EC2 instance",
        required=True,
    )
    parser.add_argument(
        "--s3_bucket",
        default="aws-beehive-tools-us-west-2",
        help="S3 bucket for termination_handler script",
    )
    parser.add_argument(
        "--handler_key",
        default="latest/termination_handler.py",
        help="S3 key for termination_handler script",
    )
    parser.add_argument(
        "--iam_instance_profile",
        default="ami_maker_instance_profile",
        help="EC2 instance profile to be attached to the instance",
    )
    args = parser.parse_args()

    global AWS_REGION, INSTANCE_TYPE, SSH_KEY_NAME, S3_BUCKET, HANDLER_KEY, SOURCE_AMI, AMI_NAME
    AWS_REGION = args.aws_region
    INSTANCE_TYPE = args.instance_type
    SSH_KEY_NAME = args.ssh_key_name
    S3_BUCKET = args.s3_bucket
    HANDLER_KEY = args.handler_key
    AMI_NAME = (
        f"aws-beehive-honeypot-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    )

    # Get the latest source AMI based on the base_ami_type argument
    SOURCE_AMI = get_latest_ami(args.base_ami_type, AWS_REGION)

    # Launch instance with SSH key and instance profile support
    instance_id = launch_instance(SSH_KEY_NAME, args.iam_instance_profile)
    wait_for_instance(instance_id)
    print("Sleeping for 60 seconds to allow instance provisioning to complete...")
    time.sleep(60)

    ami_id = create_ami(instance_id)
    copied_amis = copy_ami_to_regions(ami_id, TARGET_REGIONS)
    for region, ami in copied_amis.items():
        make_ami_public(region, ami)
    terminate_instance(instance_id)

    print("AMI creation and distribution complete.")
    print(f"Base AMI in {AWS_REGION}: {ami_id}")
    print("Copied AMIs:")
    for region, ami in copied_amis.items():
        print(f"  {region}: {ami}")
        print(f"  {region}: {ami}")


if __name__ == "__main__":
    main()
