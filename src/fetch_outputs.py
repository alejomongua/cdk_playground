import os
import boto3

stack_name = "Playground1Stack"
region = os.getenv('CDK_DEFAULT_REGION', 'us-east-1')

# Initialize a session using Boto3
session = boto3.Session(region_name=region)
cloudformation = session.client('cloudformation')

try:
    response = cloudformation.describe_stacks(StackName=stack_name)
    stack_outputs = response['Stacks'][0].get('Outputs', [])

    # Print all outputs
    for output in stack_outputs:
        if output['OutputKey'] == 'InstancePublicIP':
            print('To connect to the instance, run:')
            print()
            print(f"ssh ec2-user@{output['OutputValue']}")
            print()
            continue
        if output['OutputKey'] == 'JupyterURL':
            print('To access Jupyter Notebook, open the following URL in your browser:')
            print()
            print(output['OutputValue'])
            print()
            continue
        print(f"{output['OutputKey']}: {output['OutputValue']}")

except Exception as e:
    print(f"Error retrieving stack outputs: {e}")
