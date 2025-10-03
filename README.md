# luit-sept-2025-red-PythonProject03
# EC2 Auto-Shutdown CI/CD Pipeline

This repository implements an automated CI/CD pipeline that deploys an AWS Lambda function to shut down all running EC2 instances on a scheduled basis.

## Repository Structure

```
.
├── .github/
│   └── workflows/
│       ├── on_pull_request.yml    # Beta deployment workflow
│       └── on_merge.yml            # Production deployment workflow
├── infrastructure/
│   └── cloudformation/
│       └── lambda-ec2-shutdown.yml # CloudFormation template
├── lambda_function.py              # Lambda function code
└── README.md                       # This file
```

## 🚀 Features

- **Automated EC2 Shutdown**: Lambda function stops all running EC2 instances
- **Dual Environment**: Separate Beta and Production deployments
- **Infrastructure as Code**: CloudFormation template for reproducible infrastructure
- **CI/CD Pipeline**: GitHub Actions workflows for automated deployments
- **Scheduled Execution**: EventBridge rule triggers Lambda daily at 7:00 PM UTC

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **GitHub Repository** with Actions enabled
3. **S3 Buckets** for Lambda code storage (one for Beta, one for Prod)
4. **IAM User** with the following permissions:
   - CloudFormation: Full access
   - Lambda: Full access
   - IAM: Create/manage roles and policies
   - EC2: Describe and stop instances
   - EventBridge: Create and manage rules
   - S3: Upload objects to deployment buckets

## Setup Instructions

### Step 1: Create S3 Buckets

Create two S3 buckets for storing Lambda deployment packages:

```bash
# Beta bucket
aws s3 mb s3://your-lambda-deployments-beta --region us-east-1

# Production bucket
aws s3 mb s3://your-lambda-deployments-prod --region us-east-1
```

### Step 2: Configure GitHub Secrets

Navigate to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add the following secrets:

#### AWS Credentials
- `AWS_ACCESS_KEY_ID`: Your AWS access key
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
- `AWS_REGION`: AWS region (e.g., `us-east-1`)

#### Beta Environment
- `CF_STACK_NAME_BETA`: `ec2-shutdown-stack-beta`
- `LAMBDA_NAME_BETA`: `ec2-shutdown-lambda-beta`
- `S3_BUCKET_BETA`: `your-lambda-deployments-beta`
- `S3_PATH_BETA`: `deployments/beta/function.zip`

#### Production Environment
- `CF_STACK_NAME_PROD`: `ec2-shutdown-stack-prod`
- `LAMBDA_NAME_PROD`: `ec2-shutdown-lambda-prod`
- `S3_BUCKET_PROD`: `your-lambda-deployments-prod`
- `S3_PATH_PROD`: `deployments/prod/function.zip`

### Step 3: Set Up Repository Structure

Clone this repository and create the required directory structure:

```bash
# Create directories
mkdir -p .github/workflows
mkdir -p infrastructure/cloudformation

# Add files
# - Copy lambda_function.py to root
# - Copy CloudFormation template to infrastructure/cloudformation/
# - Copy workflow files to .github/workflows/
```

### Step 4: Initial Deployment

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/initial-deployment
   ```

2. **Add all files**:
   ```bash
   git add .
   git commit -m "Initial EC2 auto-shutdown implementation"
   git push origin feature/initial-deployment
   ```

3. **Create a Pull Request**:
   - This triggers the `on_pull_request.yml` workflow
   - Deploys to **Beta** environment
   - Review the deployment logs in GitHub Actions

4. **Merge to Main**:
   - After PR approval and merge
   - This triggers the `on_merge.yml` workflow
   - Deploys to **Production** environment

## CI/CD Workflow

### Pull Request Workflow (Beta Deployment)

**Trigger**: Pull request to `main` branch

**Steps**:
1. Checkout code
2. Configure AWS credentials
3. Validate files exist
4. Create Lambda deployment package (zip)
5. Upload to S3 Beta bucket
6. Validate CloudFormation template
7. Deploy CloudFormation stack to Beta
8. Display stack outputs

### Merge Workflow (Production Deployment)

**Trigger**: Push to `main` branch (after merge)

**Steps**:
1. Checkout code
2. Configure AWS credentials
3. Validate files exist
4. Create Lambda deployment package (zip)
5. Upload to S3 Production bucket
6. Validate CloudFormation template
7. Deploy CloudFormation stack to Production
8. Verify Lambda function deployment
9. Display stack outputs

## Testing the Lambda Function

### Manual Invocation

Test the Lambda function manually:

```bash
# Beta environment
aws lambda invoke \
  --function-name ec2-shutdown-lambda-beta \
  --region us-east-1 \
  response.json

# Production environment
aws lambda invoke \
  --function-name ec2-shutdown-lambda-prod \
  --region us-east-1 \
  response.json

# View response
cat response.json
```

### Expected Output

```json
{
  "statusCode": 200,
  "body": {
    "message": "EC2 instances stopped successfully",
    "stopped_instances": ["i-1234567890abcdef0", "i-0987654321fedcba0"],
    "count": 2
  }
}
```

## CloudFormation Resources

The CloudFormation template creates:

1. **IAM Role** (`LambdaExecutionRole`):
   - Allows Lambda to execute
   - Permissions to describe and stop EC2 instances
   - CloudWatch Logs permissions

2. **Lambda Function** (`EC2ShutdownLambda`):
   - Runtime: Python 3.12
   - Timeout: 60 seconds
   - Handler: `lambda_function.lambda_handler`

3. **EventBridge Rule** (`ScheduledRule`):
   - Schedule: Daily at 7:00 PM UTC (`cron(0 19 * * ? *)`)
   - Target: Lambda function

4. **Lambda Permission** (`LambdaInvokePermission`):
   - Allows EventBridge to invoke Lambda

## Security Best Practices

✅ **Implemented**:
- No hardcoded credentials
- All sensitive values in GitHub Secrets
- IAM roles with least privilege
- CloudWatch logging enabled

**Recommendations**:
- Use IAM roles for GitHub Actions (OIDC) instead of access keys
- Enable CloudTrail for audit logging
- Add resource tags for cost tracking
- Implement SNS notifications for Lambda failures

## Customization

### Change Schedule

Modify the `ScheduleExpression` parameter in CloudFormation:

```yaml
# Every day at 10:00 PM UTC
ScheduleExpression: 'cron(0 22 * * ? *)'

# Every weekday at 6:00 PM UTC
ScheduleExpression: 'cron(0 18 ? * MON-FRI *)'

# Every hour
ScheduleExpression: 'rate(1 hour)'
```

### Filter Specific Instances

Modify `lambda_function.py` to add filters:

```python
# Stop only instances with specific tag
response = ec2_client.describe_instances(
    Filters=[
        {'Name': 'instance-state-name', 'Values': ['running']},
        {'Name': 'tag:AutoShutdown', 'Values': ['true']}
    ]
)
```

## Troubleshooting

### Workflow Fails on S3 Upload

**Error**: `An error occurred (NoSuchBucket) when calling the PutObject operation`

**Solution**: Ensure S3 buckets exist and secrets match bucket names

### CloudFormation Stack Fails

**Error**: `User is not authorized to perform: iam:CreateRole`

**Solution**: Ensure AWS user has IAM permissions or use `CAPABILITY_NAMED_IAM`

### Lambda Function Fails

**Error**: `User is not authorized to perform: ec2:StopInstances`

**Solution**: Check IAM role permissions in CloudFormation template

### View Logs

```bash
# Get recent logs
aws logs tail /aws/lambda/ec2-shutdown-lambda-prod --follow

# Get logs from specific time
aws logs tail /aws/lambda/ec2-shutdown-lambda-prod \
  --since 1h --format short
```

## References

- [AWS SDK for Python (Boto3)](https://aws.amazon.com/sdk-for-python/)
- [Boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [CloudFormation Template Reference](https://gist.github.com/zaireali649/af536f756a1b90e65975fe5b810f4f00)
- [GitHub Actions - AWS Credentials](https://github.com/aws-actions/configure-aws-credentials)

## License

This project is provided as-is for educational and operational purposes.

## Contributing

1. Create a feature branch
2. Make changes
3. Submit a pull request (triggers Beta deployment)
4. After approval, merge to main (triggers Prod deployment)

---

**Important**: This Lambda function will stop **ALL** running EC2 instances. Use appropriate filters or test in a safe environment before production deployment.