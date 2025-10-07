import os
import time
import logging
import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger()

# AWS Region
AWS_REGION = 'us-east-1'

def get_tag_value(tags, key):
    """
    Extract value for a given tag key from a list of tag dictionaries.
    """
    if not tags:
        return None
    for tag in tags:
        if tag.get("Key") == key:
            return tag.get("Value")
    return None

def list_all_instances():
    """
    List all EC2 instances for debugging.
    """
    ec2 = boto3.client('ec2', region_name=AWS_REGION)
    response = ec2.describe_instances()
    
    print("\n" + "="*60)
    print("ALL EC2 INSTANCES:")
    print("="*60)
    
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            inst_id = instance['InstanceId']
            state = instance['State']['Name']
            tags = instance.get('Tags', [])
            name = get_tag_value(tags, 'Name')
            print(f"Instance ID: {inst_id}")
            print(f"  State: {state}")
            print(f"  Name: {name or 'N/A'}")
            print(f"  Tags: {tags}")
            print("-" * 60)
    print("="*60 + "\n")

def stop_running_instances_and_log():
    """
    Stop all running EC2 instances and log to DynamoDB.
    """
    # For testing, use hardcoded table name or environment variable
    table_name = os.environ.get("DDB_TABLE_NAME", "ec2-shutdown-logs-advanced")
    
    print(f"\n Using DynamoDB table: {table_name}")
    
    ec2 = boto3.client('ec2', region_name=AWS_REGION)
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    table = dynamodb.Table(table_name)
    execution_id = str(int(time.time()))
    
    print(f"Execution ID: {execution_id}\n")
    
    try:
        # Get all instances
        response = ec2.describe_instances()
        reservations = response.get("Reservations", [])
        
        logger.info(f"Found {len(reservations)} reservations")
        
        found_any = False
        stopped_count = 0
        
        for reservation in reservations:
            instances = reservation.get("Instances", [])
            
            for inst in instances:
                state = inst.get("State", {}).get("Name")
                inst_id = inst.get("InstanceId")
                
                logger.info(f"Instance {inst_id} is in state: {state}")
                
                if state == "running" and inst_id:
                    found_any = True
                    name = get_tag_value(inst.get("Tags", []), "Name")
                    
                    print(f"\n STOPPING: {inst_id} ({name or 'N/A'})")
                    
                    try:
                        # Stop instance
                        stop_response = ec2.stop_instances(InstanceIds=[inst_id])
                        logger.info(f"Successfully stopped instance: ID={inst_id}, Name={name or 'N/A'}")
                        print(f"  Stop response: {stop_response['StoppingInstances'][0]['CurrentState']['Name']}")
                        
                        # Log to DynamoDB
                        item = {
                            "ExecutionId": execution_id,
                            "InstanceId": inst_id,
                            "Name": name or "N/A",
                            "ShutdownTimestamp": int(time.time())
                        }
                        
                        print(f"   Writing to DynamoDB: {item}")
                        table.put_item(Item=item)
                        logger.info(f"Successfully logged shutdown instance to DynamoDB: {inst_id}")
                        
                        stopped_count += 1
                        
                    except ClientError as e:
                        logger.error(f"ClientError for instance {inst_id}: {e}")
                        logger.error(f"   Error code: {e.response['Error']['Code']}")
                        logger.error(f"   Error message: {e.response['Error']['Message']}")
                    except Exception as e:
                        logger.error(f"Unexpected error for instance {inst_id}: {e}", exc_info=True)
        
        if not found_any:
            logger.info("ℹ  No running instances found.")
        else:
            logger.info(f"Successfully stopped and logged {stopped_count} instances")
        
        return stopped_count
            
    except ClientError as e:
        logger.error(f"   AWS ClientError: {e}")
        logger.error(f"   Error code: {e.response['Error']['Code']}")
        logger.error(f"   Error message: {e.response['Error']['Message']}")
        raise
    except Exception as e:
        logger.error(f" Unexpected error: {e}", exc_info=True)
        raise

def verify_dynamodb_entries(table_name="ec2-shutdown-logs-advanced"):
    """
    Scan DynamoDB table to verify entries.
    """
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    table = dynamodb.Table(table_name)
    
    print("\n" + "="*60)
    print("DYNAMODB ENTRIES:")
    print("="*60)
    
    response = table.scan()
    items = response.get('Items', [])
    
    if not items:
        print("No items found in DynamoDB table")
    else:
        for item in items:
            print(f"ExecutionId: {item.get('ExecutionId')}")
            print(f"  InstanceId: {item.get('InstanceId')}")
            print(f"  Name: {item.get('Name')}")
            print(f"  ShutdownTimestamp: {item.get('ShutdownTimestamp')}")
            print("-" * 60)
    
    print(f"Total items: {len(items)}")
    print("="*60 + "\n")

if __name__ == "__main__":
    print("\n Starting EC2 Shutdown Test Script\n")
    
    # Step 1: List all instances
    print("STEP 1: Listing all EC2 instances...")
    list_all_instances()
    
    # Step 2: Ask for confirmation
    confirm = input("Do you want to proceed with stopping running instances? (yes/no): ")
    
    if confirm.lower() != 'yes':
        print("Aborted by user.")
        exit(0)
    
    # Step 3: Stop instances and log
    print("\nSTEP 2: Stopping running instances and logging to DynamoDB...")
    stopped = stop_running_instances_and_log()
    
    # Step 4: Verify DynamoDB entries
    print("\nSTEP 3: Verifying DynamoDB entries...")
    verify_dynamodb_entries()
    
    print(f"\n Script completed! Stopped {stopped} instances.\n")