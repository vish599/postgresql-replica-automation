# PostgreSQL Primary-Read-Replica Automation Project

This project provides APIs to automate the setup of a PostgreSQL primary-read-replica architecture using Terraform and Ansible.

## Prerequisites
Ensure the following is installed before starting the project:
```python3
from flask import Flask, request, jsonify
```

## Project Setup
1. Pass your `.pem` key in `api.py` at line number 292 as shown below:
   ```
   ansible_ssh_private_key_file=/Users/vishalpal/Desktop/untitled_folder/chalo/vishal.pem
   ```

2. Start the API by running:
   ```bash
   python3 api.py
   ```

## Overview of APIs

### 1. `Generate-code`
This API sets up the necessary Terraform code for infrastructure creation (e.g., EC2 instances, security groups) and generates an Ansible playbook for configuring both the primary and replica PostgreSQL instances.

**Request:**
```bash
curl --location 'http://127.0.0.1:5000/generate-code' \
--header 'Content-Type: application/json' \
--data '{
    "region": "us-east-1",
    "ami": "ami-04b4f1a9cf54c11d0",
    "instance_type": "t2.micro",
    "num_replicas": 2,
    "private_key_name": "vishal.pem",
    "pg_version": "13",
    "max_connections": 100,
    "shared_buffers": "128MB"
}'
```

### 2. `Terraform Plan`
This API shows the plan of the resources that will be created or deleted.

**Request:**
```bash
curl --location 'http://127.0.0.1:5000/terraform-plan' \
--header 'Content-Type: application/json' \
--data '{}'
```

### 3. `Terraform Apply`
This API applies the Terraform configuration to create or delete resources.

**Request:**
```bash
curl --location 'http://127.0.0.1:5000/terraform-apply' \
--header 'Content-Type: application/json' \
--data '{}'
```

### 4. `Configure-postgresql`
This API generates an inventory file for the Ansible playbook and executes the playbook to configure routes and parameters for the primary PostgreSQL instance and its replicas.

**Request:**
```bash
curl --location 'http://127.0.0.1:5000/configure-postgresql' \
--header 'Content-Type: application/json' \
--data '{
    "ANSIBLE_HOST_KEY_CHECKING": "False"
}'
```

### 5. `Terraform-destroy`
This API destroys the infrastructure created by Terraform.

**Request:**
```bash
curl --location 'http://127.0.0.1:5000/terraform-destroy' \
--header 'Content-Type: application/json' \
--data '{}'
```

---



