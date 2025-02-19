
    provider "aws" {
      region = "us-east-1"
    }

    # Define Security Group for PostgreSQL
    resource "aws_security_group" "postgres_sg" {
      name        = "postgres_sg"
      description = "Allow PostgreSQL traffic"

      ingress {
        from_port   = 5432
        to_port     = 5432
        protocol    = "tcp"
        cidr_blocks = ["0.0.0.0/0"]  # Change this to restrict access if needed
      }

      egress {
        from_port   = 0
        to_port     = 0
        protocol    = "-1"
        cidr_blocks = ["0.0.0.0/0"]
      }
    }
    resource "aws_security_group" "postgres_sg_ssh" {
      name        = "postgres_sg_ssh"
      description = "Allow PostgreSQL traffic"

      ingress {
        from_port   = 22
        to_port     = 22
        protocol    = "tcp"
        cidr_blocks = ["0.0.0.0/0"]  # Change this to restrict access if needed
      }

      egress {
        from_port   = 0
        to_port     = 0
        protocol    = "-1"
        cidr_blocks = ["0.0.0.0/0"]
      }
    }

    # Primary PostgreSQL EC2 instance
    resource "aws_instance" "postgres_primary" {
      ami                = "ami-04b4f1a9cf54c11d0"
      instance_type      = "t2.micro"
      key_name           = "vishal"
      security_groups    = [aws_security_group.postgres_sg.name,aws_security_group.postgres_sg_ssh.name]
      tags = {
        Name = "primary"
      }
    }

    # Replica PostgreSQL EC2 instances
    resource "aws_instance" "postgres_replica" {
      count              = 2
      ami                = "ami-04b4f1a9cf54c11d0"
      instance_type      = "t2.micro"
      key_name           = "vishal"
      security_groups    = [aws_security_group.postgres_sg.name,aws_security_group.postgres_sg_ssh.name]
      tags = {
        Name = "replica${count.index + 1}"
      }
    }



Example: Creating and Using a Terraform Module
Let's create a module that provisions an AWS S3 bucket.

Step 1: Create a Module Directory
bash
Copy
Edit
mkdir terraform-modules
cd terraform-modules
mkdir s3_bucket
Step 2: Define the Module
Inside s3_bucket/, create the following files:

main.tf (Define the S3 bucket)
hcl
Copy
Edit
resource "aws_s3_bucket" "example" {
  bucket = var.bucket_name
}
variables.tf (Define Inputs)
hcl
Copy
Edit
variable "bucket_name" {
  description = "The name of the S3 bucket"
  type        = string
}
outputs.tf (Define Outputs)
h
Copy
Edit
output "bucket_id" {
  description = "The ID of the S3 bucket"
  value       = aws_s3_bucket.example.id
}
Step 3: Use the Module in Main Terraform Configuration
Now, create a main.tf file outside the module directory.

hcl
Copy
Edit
provider "aws" {
  region = "us-east-1"
}

module "s3" {
  source      = "./s3_bucket"
  bucket_name = "my-unique-bucket-name"
}

output "bucket_id" {
  value = module.s3.bucket_id
}

