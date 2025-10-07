import boto3

def get_tag_value(tags, key_name):
    """Helper: from a list of tag dictionaries, return the Value for Key == key_name, or None."""
    for tag in tags or []:
        if tag.get("Key") == key_name:
            return tag.get("Value")
    return None

def stop_running_instances_and_print():
    ec2 = boto3.client('ec2')
    response = ec2.describe_instances().get("Reservations", [])
    found_any = False

    for reservation in response:
        for inst in reservation.get("Instances", []):
            state = inst.get("State", {}).get("Name")
            inst_id = inst.get("InstanceId")
            if state == "running" and inst_id is not None:
                found_any = True
                ec2.stop_instances(InstanceIds=[inst_id])
                name = get_tag_value(inst.get("Tags", []), "Name")
                print(f"Stopping instance: id={inst_id}", end="")
                if name:
                    print(f", name={name}, state={state}, tags={inst.get('Tags')}")
                else:
                    print()
    if not found_any:
        print("No running instances found.")

if __name__ == "__main__":
    stop_running_instances_and_print()
print("=======================================================")