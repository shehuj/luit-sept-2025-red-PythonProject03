import boto3

# Create EC2 Client
ec2 = boto3.client('ec2')
instances = ec2.describe_instances()['Reservations']
for instance in instances:
    for i in instance['Instances']:
        
# Check for all running ec2 instances, stops them and print their ID's
        if i['State']['Name'] == 'running':
            ec2.stop_instances(InstanceIds=[i['InstanceId']])
            print(f'Stopping {i["InstanceId"]}')
            break
        print(instances, "has been stopped successfully")
print('No running instances found.')
