import os
import time
import boto3

def get_ec2_client():
    return boto3.client("ec2")

def get_dynamodb_resource():
    return boto3.resource("dynamodb")

def lambda_handler(event, context):
    ec2 = get_ec2_client()
    dynamodb = get_dynamodb_resource()

    filters = [
        {"Name": "instance-state-name", "Values": ["running"]},
        {"Name": "tag:Environment", "Values": ["Dev"]},
        {"Name": "tag:AutoShutdown", "Values": ["True"]}
    ]
    resp = ec2.describe_instances(Filters=filters)
    to_stop = []
    for res in resp.get("Reservations", []):
        for inst in res.get("Instances", []):
            to_stop.append(inst)

    if not to_stop:
        print("No matching running instances to stop.")
        return {"stopped": []}

    instance_ids = [inst["InstanceId"] for inst in to_stop]
    ec2.stop_instances(InstanceIds=instance_ids)
    print(f"Stopping instances: {instance_ids}")

    # DynamoDB logging
    table_name = os.environ["DDB_TABLE_NAME"]
    table = dynamodb.Table(table_name)

    timestamp = int(time.time())
    exec_id = context.aws_request_id

    with table.batch_writer() as batch:
        for inst in to_stop:
            inst_id = inst["InstanceId"]
            tags = {}
            for t in inst.get("Tags", []):
                key = t.get("Key")
                val = t.get("Value")
                if key and val is not None:
                    tags[key] = val
            item = {
                "ExecutionId": exec_id,
                "InstanceId": inst_id,
                "ShutdownTimestamp": timestamp,
                "Tags": tags
            }
            batch.put_item(Item=item)

    return {
        "stopped": instance_ids,
        "shutdown_timestamp": timestamp,
        "execution_id": exec_id
    }