variable "s3_bucket" {
  description = "The S3 bucket containing the termination_handler.py script"
  default     = "aws-beehive-tools-us-west-2"
  type        = string
}

variable "handler_key" {
  description = "The key (path) in the S3 bucket for termination_handler.py"
  default     = "latest/termination_handler.py"
  type        = string
}

resource "aws_iam_role" "termination_handler_role" {
  name = "termination_handler_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "ami_maker_instance_profile" {
  name        = "ami_maker_instance_profile"
  description = "Policy to allow access to a specific S3 bucket and object"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "s3:ListBucket"
        ],
        Effect   = "Allow",
        Resource = "arn:aws:s3:::${var.s3_bucket}"
      },
      {
        Action = [
          "s3:GetObject"
        ],
        Effect   = "Allow",
        Resource = "arn:aws:s3:::${var.s3_bucket}/${var.handler_key}"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "termination_handler_attachment" {
  role       = aws_iam_role.termination_handler_role.name
  policy_arn = aws_iam_policy.ami_maker_instance_profile.arn
}

resource "aws_iam_instance_profile" "ami_maker_instance_profile" {
  name = "ami_maker_instance_profile"
  role = aws_iam_role.termination_handler_role.name
}

resource "aws_s3_object" "object" {
  bucket = var.s3_bucket
  key    = var.handler_key
  source = "termination_handler.py"

  # The filemd5() function is available in Terraform 0.11.12 and later
  # For Terraform 0.11.11 and earlier, use the md5() function and the file() function:
  # etag = "${md5(file("path/to/file"))}"
  etag = filemd5("termination_handler.py")
}
