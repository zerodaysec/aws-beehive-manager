# AWS Beehive Manager

This is a utility used to manage HoneyPots on AWS leveraging spot instances and or Lambda API Gateways. This solution allows us

This solution manages honeypot spot instances using AWS Lambda, SQS, S3, and EC2 spot instances. It supports two primary modes:

- **status:** Displays current honeypot details (e.g., instance count, start time).
- **deploy:** Launches honeypot spot instances based on cheapest available spot pricing.

## Components

- **honeypot_manager.py:**  
  The main script that implements the Lambda function and supports CLI execution. It reads configuration from environment variables (or CLI arguments) for parameters such as MIN_HONEYPOTS, INCLUDED_REGIONS, and EXCLUDED_REGIONS.

- **termination_handler.py:**  
  A script intended to be executed on a honeypot instance when it receives a termination notice. It syncs the `/honeypot` directory to S3 and sends a message to an SQS queue with instance details.

- **Terraform Configuration (main.tf):**  
  Provisions the following:
  - An IAM Role and instance profile for EC2 with S3 and SQS permissions.
  - An SQS queue to receive termination notifications.
  - The Lambda function along with an event source mapping that triggers the function upon receiving messages from the SQS queue.

## Deployment Steps

1. **Terraform Setup:**
   - Update `main.tf` with the appropriate values (for example, S3 bucket name and the correct AMI ID in the Lambda code).
   - Run the following commands:

     ```
     terraform init
     terraform plan
     terraform apply
     ```

2. **Lambda Packaging:**
   - Package `honeypot_manager.py` (and any dependencies) into a ZIP file named `lambda_package.zip`.
   - Ensure the ZIP package is uploaded either via Terraform (using the filename attribute) or manually through the AWS Console.

3. **Execution:**
   - **CLI Testing:**  
     Run the manager locally:

     ```
     python3 honeypot_manager.py --mode status
     ```

     or

     ```
     python3 honeypot_manager.py --mode deploy
     ```

   - **AWS Lambda:**  
     Configure the necessary environment variables (MIN_HONEYPOTS, INCLUDED_REGIONS, EXCLUDED_REGIONS, SQS_QUEUE_URL, S3_BUCKET). The Lambda function will be invoked either via scheduled events or in response to SQS messages.

4. **Spot Instance Termination:**
   - Ensure that `termination_handler.py` is configured to run on spot instance termination (for example, as part of the instance shutdown script or via a lifecycle hook).
   - The script syncs the `/honeypot` directory to the designated S3 bucket and sends instance details to the SQS queue.

## Notes

- Adjust instance types, AMI IDs, and pricing logic as needed to fit your production environment.
- Enhance error handling and add logging for improved observability.
- Verify that all AWS permissions are correctly granted, especially for S3 and SQS operations.
