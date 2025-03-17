provider "aws" {
  region = "us-east-1"
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
      MIN_HONEYPOTS    = "3"
      INCLUDED_REGIONS = "us-east-1,us-west-2"
      EXCLUDED_REGIONS = ""
      SQS_QUEUE_URL    = aws_sqs_queue.honeypot_queue.id
      S3_BUCKET        = "your-s3-bucket-name"
    }
  }
}

# Event source mapping so that SQS messages trigger the Lambda.
resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.honeypot_queue.arn
  function_name    = aws_lambda_function.honeypot_manager.arn
  batch_size       = 1
}
