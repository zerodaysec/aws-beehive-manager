provider "aws" {
  region = "us-east-1"
}

# IAM Role for EC2 to allow S3 sync and SQS messaging.
resource "aws_iam_role" "honeypot_ec2_role" {
  name = "honeypot-ec2-role"
  assume_role_policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [{
      "Action": "sts:AssumeRole",
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_policy" "honeypot_policy" {
  name        = "honeypot-policy"
  description = "Policy for honeypot EC2 to access S3 and SQS"
  policy      = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": [
          "s3:PutObject",
          "s3:ListBucket",
          "s3:GetObject"
        ],
        "Effect": "Allow",
        "Resource": "*"
      },
      {
        "Action": [
          "sqs:SendMessage"
        ],
        "Effect": "Allow",
        "Resource": "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "attach_honeypot_policy" {
  role       = aws_iam_role.honeypot_ec2_role.name
  policy_arn = aws_iam_policy.honeypot_policy.arn
}

resource "aws_iam_instance_profile" "honeypot_instance_profile" {
  name = "honeypot-instance-profile"
  role = aws_iam_role.honeypot_ec2_role.name
}

# SQS Queue for instance termination notifications.
resource "aws_sqs_queue" "honeypot_queue" {
  name = "honeypot-queue"
}

# Lambda function definition.
resource "aws_lambda_function" "honeypot_manager" {
  function_name = "honeypot-manager"
  role          = aws_iam_role.honeypot_ec2_role.arn
  handler       = "honeypot_manager.lambda_handler"
  runtime       = "python3.8"
  filename      = "lambda_package.zip" # This ZIP package should contain honeypot_manager.py and dependencies.
  environment {
    variables = {
      MIN_HONEYPOTS     = "3"
      INCLUDED_REGIONS  = "us-east-1,us-west-2"
      EXCLUDED_REGIONS  = ""
      SQS_QUEUE_URL     = aws_sqs_queue.honeypot_queue.id
      S3_BUCKET         = "your-s3-bucket-name"
    }
  }
}

# Event source mapping so that SQS messages trigger the Lambda.
resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.honeypot_queue.arn
  function_name    = aws_lambda_function.honeypot_manager.arn
  batch_size       = 1
}