import os
import secrets

from aws_cdk import (
    aws_ec2 as ec2,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    Stack,
    RemovalPolicy,
    CfnOutput,  # Import CfnOutput
)
from constructs import Construct
import requests  # Ensure this is imported

ALLOWED_PORTS = [22, 3000]


class Playground1Stack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        predefined_token = secrets.token_urlsafe(32)

        # Get your current public IP address
        public_ip = requests.get('https://api.ipify.org').text.strip()

        # Read your local SSH public key
        with open(os.path.expanduser('~/.ssh/id_rsa.pub'), 'r') as pubkey_file:
            public_key = pubkey_file.read().strip()

        # Use the default VPC
        vpc = ec2.Vpc.from_lookup(
            self, "DefaultVpc",
            is_default=True
        )

        # Create an S3 Bucket
        my_bucket = s3.Bucket(
            self, "MyBucket",
            removal_policy=RemovalPolicy.DESTROY
        )

        # Create a DynamoDB Table
        my_table = dynamodb.Table(
            self, "MyTable",
            partition_key=dynamodb.Attribute(
                name="id",
                type=dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY
        )

        # Create an IAM Role for EC2 Instance
        ec2_role = iam.Role(
            self, "EC2InstanceRole",
            assumed_by=iam.ServicePrincipal(
                "ec2.amazonaws.com")  # type: ignore
        )

        # Create a Policy for S3 access
        s3_policy = iam.PolicyStatement(
            actions=[
                "s3:GetObject",
                "s3:ListBucket",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            resources=[
                my_bucket.bucket_arn,
                f"{my_bucket.bucket_arn}/*"
            ]
        )

        # Create a Policy for DynamoDB access
        dynamodb_policy = iam.PolicyStatement(
            actions=[
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Query",
                "dynamodb:Scan"
            ],
            resources=[my_table.table_arn]
        )

        cloudformation_policy = iam.PolicyStatement(
            actions=[
                'cloudformation:DescribeStacks'
            ],
            resources=[
                f'arn:aws:cloudformation:us-east-1:404449475211:stack/{id}/*'
            ]
        )

        # Attach Policies to the Role
        ec2_role.add_to_policy(s3_policy)
        ec2_role.add_to_policy(dynamodb_policy)
        ec2_role.add_to_policy(cloudformation_policy)

        # Create a Security Group for EC2
        ec2_sg = ec2.SecurityGroup(
            self, "EC2SecurityGroup",
            vpc=vpc,
            description="Allow SSH from current IP and outbound internet access",
            allow_all_outbound=True
        )

        # Allow access on ALLOWED_PORTS from your current public IP address
        for port in ALLOWED_PORTS:
            ec2_sg.add_ingress_rule(
                ec2.Peer.ipv4(f"{public_ip}/32"),
                ec2.Port.tcp(port),
                f"Allow access to port {port} from current public IP"
            )

        # Create user data to add your SSH public key to authorized_keys
        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            # Configure SSH access
            'mkdir -p /home/ec2-user/.ssh',
            f'echo "{public_key}" >> /home/ec2-user/.ssh/authorized_keys',
            'chown -R ec2-user:ec2-user /home/ec2-user/.ssh',
            'chmod 700 /home/ec2-user/.ssh',
            'chmod 600 /home/ec2-user/.ssh/authorized_keys'

            # Update and upgrade OS
            'yum update -y',
            'yum upgrade -y',

            # Install jupyter
            'yum install python3-pip -y',
            'sudo -u ec2-user pip3 install jupyter boto3',

            # Add python binaries to PATH
            'export PATH=$PATH:/usr/local/bin:/home/ec2-user/.local/bin',
            'echo "export PATH=$PATH:/usr/local/bin:/home/ec2-user/.local/bin" >> /home/ec2-user/.bashrc',

            'sudo -u ec2-user mkdir /home/ec2-user/code',
            'sudo -u ec2-user touch /home/ec2-user/jupyter.log',

            # Configure Jupyter to allow access with predefined token
            'echo "from jupyter_server.auth.security import passwd" > /home/ec2-user/.jupyter/jupyter_notebook_config.py',
            'echo "password = passwd(\'predefined\')" >> /home/ec2-user/.jupyter/jupyter_notebook_config.py',
            'echo "c = get_config()" >> /home/ec2-user/.jupyter/jupyter_notebook_config.py',
            'echo "c.PasswordIdentityProvider.hashed_password = password" >> /home/ec2-user/.jupyter/jupyter_notebook_config.py',
            'echo "c.ServerApp.ip = \'0.0.0.0\'" >> /home/ec2-user/.jupyter/jupyter_notebook_config.py',
            'echo "c.ServerApp.allow_origin = \'*\'" >> /home/ec2-user/.jupyter/jupyter_notebook_config.py',
            f'echo "c.IdentityProvider.token = \'{predefined_token}\'" >> /home/ec2-user/.jupyter/jupyter_notebook_config.py',
            'echo "c.ServerApp.allow_remote_access = True" >> /home/ec2-user/.jupyter/jupyter_notebook_config.py',
            'echo "c.ExtensionApp.open_browser = False" >> /home/ec2-user/.jupyter/jupyter_notebook_config.py',
            'echo "c.ServerApp.open_browser = False" >> /home/ec2-user/.jupyter/jupyter_notebook_config.py',
            'echo "c.ServerApp.port = 3000" >> /home/ec2-user/.jupyter/jupyter_notebook_config.py',
            'echo "c.ServerApp.root_dir = \'/home/ec2-user/code\'" >> /home/ec2-user/.jupyter/jupyter_notebook_config.py',

            # Start Jupyter Notebook on port 3000
            'nohup sudo -u ec2-user /home/ec2-user/.local/bin/jupyter notebook --config=/home/ec2-user/.jupyter/jupyter_notebook_config.py > /home/ec2-user/jupyter.log 2>&1 &'

            # Add 2GB swapfile
            'dd if=/dev/zero of=/swapfile bs=128M count=16',
            'chmod 600 /swapfile',
            'mkswap /swapfile',
            'swapon /swapfile',
            'echo "/swapfile swap swap defaults 0 0" >> /etc/fstab'
        )

        instance_type = ec2.InstanceType("t2.micro")

        # Use the latest Amazon Linux 2023 image ami-012967cc5a8c9f891
        amazon_linux_2023 = ec2.MachineImage.generic_linux(
            ami_map={
                "us-east-1": "ami-012967cc5a8c9f891"
            }
        )

        # Create an EC2 Instance with the user data in the public subnet
        ec2_instance = ec2.Instance(
            self, "EC2Instance",
            associate_public_ip_address=True,
            instance_type=instance_type,
            machine_image=amazon_linux_2023,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_group=ec2_sg,
            role=ec2_role,  # type: ignore
            user_data=user_data
        )

        # Output the Public IP of the EC2 Instance
        CfnOutput(
            self,
            "InstancePublicIP",
            value=ec2_instance.instance_public_ip,
            description="Public IP address of the EC2 instance",
        )

        # Output the URL to access Jupyter Notebook
        CfnOutput(
            self,
            "JupyterURL",
            value=f"http://{ec2_instance.instance_public_ip}:3000/?token={predefined_token}",
            description="URL to access Jupyter Notebook",
        )

        # Output the S3 Bucket Name
        CfnOutput(
            self,
            "BucketName",
            value=my_bucket.bucket_name,
            description="Name of the S3 Bucket",
        )
