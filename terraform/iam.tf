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