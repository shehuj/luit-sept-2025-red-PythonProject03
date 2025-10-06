import time
import os
from unittest.mock import patch, MagicMock

import pytest

import lambda_function_advance


class DummyContext:
    def __init__(self, aws_request_id="req-xyz"):
        self.aws_request_id = aws_request_id


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    """Ensure DDB_TABLE_NAME is defined in environment."""
    monkeypatch.setenv("DDB_TABLE_NAME", "TestTable")


@patch("lambda_function_advance.get_ec2_client")
@patch("lambda_function_advance.get_dynamodb_resource")
def test_no_instances(mock_get_dynamo, mock_get_ec2):
    """When describe_instances returns no matching instances."""
    # Setup mocks
    mock_ec2 = MagicMock()
    mock_get_ec2.return_value = mock_ec2
    mock_ec2.describe_instances.return_value = {"Reservations": []}

    mock_dynamo = MagicMock()
    mock_get_dynamo.return_value = mock_dynamo
    mock_table = MagicMock()
    mock_dynamo.Table.return_value = mock_table

    ctx = DummyContext("ctx-1")
    result = lambda_function_advance.lambda_handler(event={}, context=ctx)

    assert result == {"stopped": []}
    mock_ec2.stop_instances.assert_not_called()
    mock_table.batch_writer.assert_not_called()


@patch("lambda_function_advance.get_ec2_client")
@patch("lambda_function_advance.get_dynamodb_resource")
def test_with_instances(mock_get_dynamo, mock_get_ec2):
    """When there are matching instances."""
    dummy_inst = {
        "InstanceId": "i-1234",
        "Tags": [
            {"Key": "Environment", "Value": "Dev"},
            {"Key": "AutoShutdown", "Value": "True"},
            {"Key": "Extra", "Value": "Val"}
        ]
    }
    describe_resp = {"Reservations": [{"Instances": [dummy_inst]}]}

    mock_ec2 = MagicMock()
    mock_get_ec2.return_value = mock_ec2
    mock_ec2.describe_instances.return_value = describe_resp
    mock_ec2.stop_instances.return_value = {"StoppingInstances": []}

    mock_dynamo = MagicMock()
    mock_get_dynamo.return_value = mock_dynamo
    mock_table = MagicMock()
    mock_dynamo.Table.return_value = mock_table

    batch_cm = mock_table.batch_writer.return_value
    batch_cm.__enter__.return_value = batch_cm
    batch_cm.__exit__.return_value = None

    ctx = DummyContext("exec-77")
    before = int(time.time())
    result = lambda_function_advance.lambda_handler(event={}, context=ctx)
    after = int(time.time())

    # EC2 assertions
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

    # DynamoDB assertions
    mock_table.batch_writer.assert_called_once()
    assert batch_cm.put_item.call_count == 1
    _, kwargs = batch_cm.put_item.call_args
    item = kwargs.get("Item") if "Item" in kwargs else kwargs

    assert item["ExecutionId"] == ctx.aws_request_id
    assert item["InstanceId"] == dummy_inst["InstanceId"]
    ts = item["ShutdownTimestamp"]
    assert before <= ts <= after
    tags = item["Tags"]
    assert tags["Environment"] == "Dev"
    assert tags["AutoShutdown"] == "True"
    assert tags["Extra"] == "Val"

    # Return value assertions
    assert result["stopped"] == [dummy_inst["InstanceId"]]
    assert result["execution_id"] == ctx.aws_request_id
    assert result["shutdown_timestamp"] == ts


@patch("lambda_function_advance.get_ec2_client")
@patch("lambda_function_advance.get_dynamodb_resource")
def test_dynamo_failure(mock_get_dynamo, mock_get_ec2):
    """Simulate DynamoDB put_item failure."""
    dummy_inst = {"InstanceId": "i-fail", "Tags": []}
    mock_ec2 = MagicMock()
    mock_get_ec2.return_value = mock_ec2
    mock_ec2.describe_instances.return_value = {"Reservations": [{"Instances": [dummy_inst]}]}
    mock_ec2.stop_instances.return_value = {"StoppingInstances": []}

    mock_dynamo = MagicMock()
    mock_get_dynamo.return_value = mock_dynamo
    mock_table = MagicMock()
    mock_dynamo.Table.return_value = mock_table

    batch_cm = mock_table.batch_writer.return_value
    batch_cm.__enter__.return_value = batch_cm
    batch_cm.__exit__.return_value = None
    batch_cm.put_item.side_effect = Exception("Dynamo write failed")

    ctx = DummyContext("ctx-fail")
    with pytest.raises(Exception) as excinfo:
        lambda_function_advance.lambda_handler(event={}, context=ctx)

    assert "Dynamo write failed" in str(excinfo.value)