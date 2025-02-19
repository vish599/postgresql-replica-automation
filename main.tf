
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
    
