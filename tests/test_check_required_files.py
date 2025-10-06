import time
import os
from unittest.mock import patch, MagicMock

import pytest

import lambda_function_foundational as lambda_function




class DummyContext:
    """Minimal Lambda context for testing."""
    def __init__(self, aws_request_id="dummy-req-id"):
        self.aws_request_id = aws_request_id


@pytest.fixture(autouse=True)
def patch_env(monkeypatch):
    """Ensure the DDB_TABLE_NAME env var is set before import/usage."""
    monkeypatch.setenv("DDB_TABLE_NAME", "EC2ShutdownLogTable")


@patch("lambda_function.boto3.client")
@patch("lambda_function.boto3.resource")
def test_lambda_handler_no_instances(mock_boto_resource, mock_boto_client):
    """
    If describe_instances returns no matching instances, expect {'stopped': []}
    and no stop or writes to DynamoDB.
    """
    # Mock EC2 client
    mock_ec2 = MagicMock()
    mock_boto_client.return_value = mock_ec2
    mock_ec2.describe_instances.return_value = {"Reservations": []}

    # Mock DynamoDB table/resource
    mock_ddb = MagicMock()
    mock_boto_resource.return_value = mock_ddb
    mock_table = MagicMock()
    mock_ddb.Table.return_value = mock_table

    ctx = DummyContext(aws_request_id="ctx-1")
    result = lambda_function.lambda_handler(event={}, context=ctx)

    assert result == {"stopped": []}
    mock_ec2.stop_instances.assert_not_called()
    mock_table.batch_writer.assert_not_called()


@patch("lambda_function.boto3.client")
@patch("lambda_function.boto3.resource")
def test_lambda_handler_with_instances(mock_boto_resource, mock_boto_client):
    """
    When there are matching instances:
    - describe_instances returns instances
    - stop_instances is called
    - DynamoDB writes items
    - return contains stopped list, timestamp, execution_id
    """
    # Prepare a dummy instance with tags
    dummy_inst = {
        "InstanceId": "i-1234567890",
        "Tags": [
            {"Key": "Environment", "Value": "Dev"},
            {"Key": "AutoShutdown", "Value": "True"},
            {"Key": "OtherTag", "Value": "ValueX"},
        ],
    }
    describe_resp = {"Reservations": [{"Instances": [dummy_inst]}]}

    # Mock EC2
    mock_ec2 = MagicMock()
    mock_boto_client.return_value = mock_ec2
    mock_ec2.describe_instances.return_value = describe_resp
    mock_ec2.stop_instances.return_value = {"StoppingInstances": []}

    # Mock DynamoDB
    mock_ddb = MagicMock()
    mock_boto_resource.return_value = mock_ddb
    mock_table = MagicMock()
    mock_ddb.Table.return_value = mock_table

    # Set up batch_writer context manager behavior
    batch_writer_cm = mock_table.batch_writer.return_value
    batch_writer_cm.__enter__.return_value = batch_writer_cm
    batch_writer_cm.__exit__.return_value = None

    ctx = DummyContext(aws_request_id="exec-42")

    before = int(time.time())
    result = lambda_function.lambda_handler(event={}, context=ctx)
    after = int(time.time())

    # Check EC2 calls
    mock_ec2.describe_instances.assert_called_once_with(
        Filters=[
            {"Name": "instance-state-name", "Values": ["running"]},
            {"Name": "tag:Environment", "Values": ["Dev"]},
            {"Name": "tag:AutoShutdown", "Values": ["True"]}
        ]
    )
    mock_ec2.stop_instances.assert_called_once_with(
        InstanceIds=[dummy_inst["InstanceId"]]
    )

    # Check DynamoDB writes
    mock_table.batch_writer.assert_called_once()
    assert batch_writer_cm.put_item.call_count == 1

    # Inspect the item that was passed to put_item
    # It might be passed as keyword or positional argument
    _, kwargs = batch_writer_cm.put_item.call_args
    item = kwargs.get("Item") if "Item" in kwargs else kwargs

    assert item["ExecutionId"] == ctx.aws_request_id
    assert item["InstanceId"] == dummy_inst["InstanceId"]
    ts = item["ShutdownTimestamp"]
    assert before <= ts <= after
    tags = item["Tags"]
    assert isinstance(tags, dict)
    assert tags["Environment"] == "Dev"
    assert tags["AutoShutdown"] == "True"
    assert tags["OtherTag"] == "ValueX"

    # Check returned result
    assert "stopped" in result
    assert result["stopped"] == [dummy_inst["InstanceId"]]
    assert result["execution_id"] == ctx.aws_request_id
    assert result["shutdown_timestamp"] == ts


@patch("lambda_function.boto3.client")
@patch("lambda_function.boto3.resource")
def test_lambda_handler_dynamo_failure(mock_boto_resource, mock_boto_client):
    """
    Simulate failure in DynamoDB put_item (e.g. raises exception). Depending on your design,
    the function might propagate it or handle it. This test assumes it propagates.
    """
    dummy_inst = {"InstanceId": "i-0fail", "Tags": []}
    mock_ec2 = MagicMock()
    mock_boto_client.return_value = mock_ec2
    mock_ec2.describe_instances.return_value = {"Reservations": [{"Instances": [dummy_inst]}]}
    mock_ec2.stop_instances.return_value = {"StoppingInstances": []}

    mock_ddb = MagicMock()
    mock_boto_resource.return_value = mock_ddb
    mock_table = MagicMock()
    mock_ddb.Table.return_value = mock_table

    batch_cm = mock_table.batch_writer.return_value
    batch_cm.__enter__.return_value = batch_cm
    batch_cm.__exit__.return_value = None

    # Make put_item raise
    batch_cm.put_item.side_effect = Exception("Dynamo write failed")

    ctx = DummyContext(aws_request_id="ctx-fail")

    with pytest.raises(Exception) as excinfo:
        lambda_function.lambda_handler(event={}, context=ctx)
    assert "Dynamo write failed" in str(excinfo.value)