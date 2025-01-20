from flask import Flask, request, jsonify
import subprocess
import os
import json


app = Flask(__name__)

TERRAFORM_DIR = './terraform'
ANSIBLE_DIR = './ansible'


def run_command(command, cwd=None,env=None):
    try:
        result = subprocess.run(command, cwd=cwd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,env=env)
        return result.stdout.decode('utf-8')
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr.decode('utf-8')}"


def generate_terraform_code(params):
    terraform_code = f"""
    provider "aws" {{
      region = "{params.get('region', 'us-east-1')}"
    }}

    # Define Security Group for PostgreSQL
    resource "aws_security_group" "postgres_sg" {{
      name        = "postgres_sg"
      description = "Allow PostgreSQL traffic"

      ingress {{
        from_port   = 5432
        to_port     = 5432
        protocol    = "tcp"
        cidr_blocks = ["0.0.0.0/0"]  # Change this to restrict access if needed
      }}

      egress {{
        from_port   = 0
        to_port     = 0
        protocol    = "-1"
        cidr_blocks = ["0.0.0.0/0"]
      }}
    }}
    resource "aws_security_group" "postgres_sg_ssh" {{
      name        = "postgres_sg_ssh"
      description = "Allow PostgreSQL traffic"

      ingress {{
        from_port   = 22
        to_port     = 22
        protocol    = "tcp"
        cidr_blocks = ["0.0.0.0/0"]  # Change this to restrict access if needed
      }}

      egress {{
        from_port   = 0
        to_port     = 0
        protocol    = "-1"
        cidr_blocks = ["0.0.0.0/0"]
      }}
    }}

    # Primary PostgreSQL EC2 instance
    resource "aws_instance" "postgres_primary" {{
      ami                = "{params.get('ami', 'ami-12345678')}"
      instance_type      = "{params['instance_type']}"
      key_name           = "{params['key_name']}"
      security_groups    = [aws_security_group.postgres_sg.name,aws_security_group.postgres_sg_ssh.name]
      tags = {{
        Name = "primary"
      }}
    }}

    # Replica PostgreSQL EC2 instances
    resource "aws_instance" "postgres_replica" {{
      count              = {params['num_replicas']}
      ami                = "{params.get('ami', 'ami-12345678')}"
      instance_type      = "{params['instance_type']}"
      key_name           = "{params['key_name']}"
      security_groups    = [aws_security_group.postgres_sg.name,aws_security_group.postgres_sg_ssh.name]
      tags = {{
        Name = "replica${{count.index + 1}}"
      }}
    }}
    """

    
    os.makedirs(TERRAFORM_DIR, exist_ok=True)
    
   
    with open(os.path.join(TERRAFORM_DIR, 'main.tf'), 'w') as file:
        file.write(terraform_code)

    return "Terraform code generated successfully."

# Generate Ansible playbook


def generate_ansible_playbook(params):
    playbook = f"""

    - name: Setup PostgreSQL replication
      hosts: all
      gather_facts: no
      vars:
        REPLICATOR_PASSWORD: "Dish599@"
        ansible_ssh_common_args: "-o StrictHostKeyChecking=no"

      tasks:
        - name: Primary Setup
          block:
            - name: Install PostgreSQL on Primary
              ansible.builtin.shell: |
                sudo apt update && sudo apt install -y postgresql-"{params['pg_version']}" postgresql-client-"{params['pg_version']}"

            - name: Start PostgreSQL on Primary
              ansible.builtin.shell: |
                sudo systemctl start postgresql && sudo systemctl enable postgresql

            - name: Update PostgreSQL config for replication on Primary
              ansible.builtin.shell: |
                echo "listen_addresses = '*'" | sudo tee -a /etc/postgresql/"{params['pg_version']}"/main/postgresql.conf
                echo "wal_level = 'replica'" | sudo tee -a /etc/postgresql/"{params['pg_version']}"/main/postgresql.conf
                echo "max_wal_senders = {params['max_connections']}" | sudo tee -a /etc/postgresql/"{params['pg_version']}"/main/postgresql.conf
                echo "shared_buffers = {params['shared_buffers']}" | sudo tee -a /etc/postgresql/"{params['pg_version']}"/main/postgresql.conf
                echo "max_replication_slots = 3" | sudo tee -a /etc/postgresql/"{params['pg_version']}"/main/postgresql.conf
                echo "archive_mode = 'on'" | sudo tee -a /etc/postgresql/"{params['pg_version']}"/main/postgresql.conf
                echo "archive_command = 'cp %p /path/to/archive/%f'" | sudo tee -a /etc/postgresql/"{params['pg_version']}"/main/postgresql.conf

            - name: Update pg_hba.conf and start PostgreSQL on Primary
              ansible.builtin.shell: |
                echo "host replication all {{ hostvars['ec2-54-234-207-68.compute-1.amazonaws.com']['REPLICA_PRIVATE_IP'] }}/32 md5" | sudo tee -a /etc/postgresql/"{params['pg_version']}"/main/pg_hba.conf

            - name: Create replicator user on Primary
              ansible.builtin.shell: |
                sudo sed -i '60s/^/#/' /etc/postgresql/"{params['pg_version']}"/main/postgresql.conf
                sudo systemctl restart postgresql
                sudo -u postgres psql -c "CREATE USER replicator WITH REPLICATION PASSWORD '{{ REPLICATOR_PASSWORD }}';"
          when: "'primary' in group_names"

        - name: Replica Setup
          block:
            - name: Install PostgreSQL on Replica
              ansible.builtin.shell: |
                sudo apt update && sudo apt install -y postgresql-"{params['pg_version']}" postgresql-client-"{params['pg_version']}"

            - name: Stop PostgreSQL and remove data on Replica
              ansible.builtin.shell: |
                sudo systemctl stop postgresql && sudo rm -rf /var/lib/postgresql/"{params['pg_version']}"/main/*

            - name: Take base backup from Primary to Replica
              ansible.builtin.shell: |
                sudo -u postgres pg_basebackup -h {{ hostvars['ec2-100-27-205-19.compute-1.amazonaws.com']['PRIMARY_PRIVATE_IP'] }} -D /var/lib/postgresql/"{params['pg_version']}"/main -U replicator -v -P --password <<EOF
                {{ REPLICATOR_PASSWORD }}
                EOF

            - name: Copy config files and start PostgreSQL on Replica
              ansible.builtin.shell: |
                sudo cp -rf /etc/postgresql/"{params['pg_version']}"/main/* /var/lib/postgresql/"{params['pg_version']}"/main/
                echo -e "primary_conninfo = 'host={{ hostvars['ec2-100-27-205-19.compute-1.amazonaws.com']['PRIMARY_PRIVATE_IP'] }} port=5432 user=replicator password={{ REPLICATOR_PASSWORD }}'" | sudo tee -a /var/lib/postgresql/"{params['pg_version']}"/main/postgresql.conf
                sudo systemctl enable postgresql
                sudo systemctl start postgresql
          when: "'replica' in group_names"

    """

    os.makedirs(ANSIBLE_DIR, exist_ok=True)
    with open(os.path.join(ANSIBLE_DIR, 'playbook.yml'), 'w') as file:
        file.write(playbook)

    return "Ansible playbook generated successfully."



@app.route('/generate-code', methods=['POST'])
def generate_code():
    params = request.json

    if not params:
        return jsonify({"error": "Invalid input"}), 400
    key_name = os.path.basename(params['private_key_name']).split('.')[0] 
    params['key_name'] = key_name  

    terraform_status = generate_terraform_code(params)
    ansible_status = generate_ansible_playbook(params)

    return jsonify({"terraform": terraform_status, "ansible": ansible_status})

# API to initialize and plan Terraform
@app.route('/terraform-plan', methods=['POST'])
def terraform_plan():
    output = run_command("terraform init && terraform plan", cwd=TERRAFORM_DIR)
    return jsonify({"output": output})


@app.route('/terraform-apply', methods=['POST'])

def terraform_apply():
    run_command("terraform refresh", cwd=TERRAFORM_DIR)
    output = run_command("terraform apply -auto-approve", cwd=TERRAFORM_DIR)
    terraform_output = run_command("terraform output -json", cwd=TERRAFORM_DIR)
    try:
        output_data = json.loads(terraform_output)
        primary_ip = output_data.get('postgres_primary_public_ip', {}).get('value', 'N/A')
        replica_ips = output_data.get('postgres_replica_public_ips', {}).get('value', [])
    except json.JSONDecodeError:
        return jsonify({"error": "Failed to parse Terraform output"}), 500

    return jsonify({
        "output": output,
        "primary_ip": primary_ip,
        "replica_ips": replica_ips
    })




@app.route('/terraform-destroy', methods=['POST'])
def terraform_destroy():
    output = run_command("terraform destroy -auto-approve", cwd=TERRAFORM_DIR)
    return jsonify({"output": output})


@app.route('/configure-postgresql', methods=['POST'])
def configure_postgresql():



    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    inventory_path = os.path.join(BASE_DIR, "ansible", "inventory.ini")
    playbook_path = os.path.join(BASE_DIR, "ansible", "playbook.yml")
    ansible_dir = os.path.join(BASE_DIR, "ansible")
    terraform_state_path = os.path.join(BASE_DIR, "terraform", "terraform.tfstate")
    try:
        with open(terraform_state_path, 'r') as tfstate_file:
            terraform_state = json.load(tfstate_file)
        instances = terraform_state.get('resources', [])
        instance_dns = {}
        instance_private_ip = {}

        for resource in instances:
            if resource['type'] == 'aws_instance':  
                for instance in resource.get('instances', []):
                    attributes = instance.get('attributes', {}) 

                    
                    tags = attributes.get('tags', {})
                    instance_name = tags.get('Name')
                    public_dns = attributes.get('public_dns') 
                    private_ip = attributes.get('private_ip')

                    if instance_name and public_dns:
                        instance_dns[instance_name] = public_dns

                    if instance_name and private_ip:
                        instance_private_ip[instance_name] = private_ip

        print(instance_dns)
        print(instance_private_ip)

    except FileNotFoundError:
        print(f"The file at {terraform_state_path} was not found.")
    except json.JSONDecodeError:
        print("Error decoding the JSON in the terraform state file.")

    hosts = ['primary', 'replica1', 'replica2']


    with open(inventory_path, 'w') as inventory_file:
        inventory_file.write("[all]\n")
        for host in hosts:
            if host == 'primary':
                inventory_file.write("[primary]\n")
            else:
                inventory_file.write("[replica]\n")

            
            dns = instance_dns.get(host)
            private_ip = instance_private_ip.get(host)

            if dns:

                inventory_file.write(f"{dns} ansible_user=ubuntu ansible_ssh_private_key_file=/Users/vishalpal/Desktop/untitled_folder/chalo/vishal.pem {host}_PRIVATE_IP={private_ip}\n")
            else:
                print(f"Warning: No DNS found for {host}")

    print(f"Inventory Path: {inventory_path}")
    print(f"Playbook Path: {playbook_path}")
    print(f"ANSIBLE_DIR: {ansible_dir}")
    with open(inventory_path, 'r') as file:
        print("Inventory File Content:\n", file.read())

    output = run_command(f"ansible-playbook -i {inventory_path} {playbook_path}", cwd=ansible_dir)
    return jsonify({"output": output})

if __name__ == '__main__':
    app.run(debug=True)
