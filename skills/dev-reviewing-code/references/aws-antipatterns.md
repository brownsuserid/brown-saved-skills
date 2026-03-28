# AWS Infrastructure Anti-Patterns Catalog

This reference covers AWS cloud architecture anti-patterns and IaC issues.

## Architecture Anti-Patterns

### Lift-and-Shift Without Optimization

**What:** Moving on-premises architecture to cloud without redesign.

**Why Bad:** Misses cloud benefits, often more expensive than on-prem.

**Signs:**
- VMs instead of containers/serverless
- Self-managed databases instead of RDS/Aurora
- File storage on EBS instead of S3
- No auto-scaling configured

**Fix:**
- Evaluate managed services (RDS, ECS/EKS, Lambda)
- Design for horizontal scaling
- Use cloud-native storage patterns
- Implement proper auto-scaling

### Monolithic Deployment

**What:** Deploying entire system as single unit.

**Why Bad:** High blast radius, slow deployments, limited scaling.

```yaml
# Bad: Single deployment
Resources:
  MonolithicApp:
    Type: AWS::ECS::Service
    Properties:
      DesiredCount: 3
      # Everything in one container

# Good: Microservices
Resources:
  UserService:
    Type: AWS::ECS::Service
  OrderService:
    Type: AWS::ECS::Service
  PaymentService:
    Type: AWS::ECS::Service
```

**Fix:**
- Break into microservices
- Use cell-based architecture
- Implement staged rollouts

### Single Region Without DR

**What:** All resources in one region with no disaster recovery.

**Why Bad:** Region outage = complete downtime.

**Fix:**
- Multi-AZ at minimum
- Multi-region for critical workloads
- Backup/restore procedures tested
- RTO/RPO defined and validated

### Hardcoded Values

**What:** ARNs, account IDs, or resource names hardcoded.

**Why Bad:** Can't deploy to different environments/accounts.

```python
# Bad: Hardcoded
bucket = s3.Bucket(self, "Bucket",
    bucket_name="my-company-prod-bucket"
)

role_arn = "arn:aws:iam::123456789012:role/MyRole"

# Good: Dynamic
bucket = s3.Bucket(self, "Bucket",
    bucket_name=f"{props.environment}-{props.app_name}-bucket"
)

role = iam.Role.from_role_arn(
    self, "Role",
    role_arn=Fn.sub("arn:aws:iam::${AWS::AccountId}:role/MyRole")
)
```

## Security Anti-Patterns

### Overly Permissive IAM Policies

**What:** Using `*` for resources or actions.

**Why Bad:** Violates least privilege, security risk.

```python
# Bad: Too permissive
policy = iam.PolicyStatement(
    actions=["s3:*"],
    resources=["*"]
)

# Good: Least privilege
policy = iam.PolicyStatement(
    actions=["s3:GetObject", "s3:PutObject"],
    resources=[bucket.arn_for_objects("*")]
)
```

### Public S3 Buckets

**What:** S3 buckets accessible from internet.

**Why Bad:** Data exposure, compliance violations.

```python
# Bad: Public bucket
bucket = s3.Bucket(self, "Bucket",
    public_read_access=True
)

# Good: Private with explicit access
bucket = s3.Bucket(self, "Bucket",
    block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
    encryption=s3.BucketEncryption.S3_MANAGED
)
```

### Unencrypted Data at Rest

**What:** Databases, S3, EBS without encryption.

**Why Bad:** Compliance violations, data breach risk.

```python
# Bad: No encryption
table = dynamodb.Table(self, "Table",
    partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING)
)

# Good: Encrypted
table = dynamodb.Table(self, "Table",
    partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING),
    encryption=dynamodb.TableEncryption.AWS_MANAGED
)
```

### Overly Permissive Security Groups

**What:** Security groups allowing 0.0.0.0/0 access.

**Why Bad:** Exposes resources to entire internet.

```python
# Bad: Open to world
sg.add_ingress_rule(
    ec2.Peer.any_ipv4(),
    ec2.Port.tcp(22),
    "SSH access"
)

# Good: Restricted
sg.add_ingress_rule(
    ec2.Peer.ipv4("10.0.0.0/8"),
    ec2.Port.tcp(22),
    "SSH from VPN only"
)
```

### Missing VPC Endpoints

**What:** Traffic to AWS services going over internet.

**Why Bad:** Slower, costs more, security exposure.

**Fix:**
```python
# Add VPC endpoints for frequently used services
vpc.add_gateway_endpoint("S3Endpoint",
    service=ec2.GatewayVpcEndpointAwsService.S3
)

vpc.add_interface_endpoint("SecretsManagerEndpoint",
    service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER
)
```

## Operations Anti-Patterns

### Manual Infrastructure (ClickOps)

**What:** Creating resources via AWS Console.

**Why Bad:** Not reproducible, no version control, human error.

**Signs:**
- Resources created manually
- No CloudFormation/CDK/Terraform
- "I'll document it later"

**Fix:**
- Use IaC (CDK, CloudFormation, Terraform)
- Version control infrastructure code
- Automated deployments via CI/CD

### No Observability

**What:** Missing monitoring, logging, tracing.

**Why Bad:** Can't detect issues, blind to performance.

**Required observability:**
- CloudWatch Alarms for key metrics
- CloudWatch Logs for application logs
- X-Ray for distributed tracing
- CloudTrail for API auditing

```python
# Add alarms
alarm = cloudwatch.Alarm(self, "HighErrors",
    metric=function.metric_errors(),
    threshold=5,
    evaluation_periods=1,
    alarm_description="High error rate detected"
)

# Enable X-Ray
function = lambda_.Function(self, "Function",
    tracing=lambda_.Tracing.ACTIVE,
    ...
)
```

### Missing Cost Allocation Tags

**What:** Resources without cost tracking tags.

**Why Bad:** Can't understand or optimize costs.

**Required tags:**
- Environment (prod, staging, dev)
- Owner (team or individual)
- Project/Application
- CostCenter (for billing)

```python
Tags.of(self).add("Environment", props.environment)
Tags.of(self).add("Project", props.project_name)
Tags.of(self).add("Owner", props.team)
Tags.of(self).add("CostCenter", props.cost_center)
```

### No Backup/Retention Policies

**What:** Data without backups or retention settings.

**Why Bad:** Data loss, compliance violations.

```python
# Good: Backup enabled
table = dynamodb.Table(self, "Table",
    point_in_time_recovery=True,
    ...
)

bucket = s3.Bucket(self, "Bucket",
    versioned=True,
    lifecycle_rules=[
        s3.LifecycleRule(
            noncurrent_version_expiration=Duration.days(90)
        )
    ]
)
```

## CI/CD Anti-Patterns

### Infrequent Deployments

**What:** Deploying weekly/monthly instead of continuously.

**Why Bad:** Larger changes = more risk, longer feedback loops.

**Fix:**
- Deploy multiple times per day
- Small, incremental changes
- Feature flags for incomplete work

### No Staged Rollouts

**What:** Deploying to all instances simultaneously.

**Why Bad:** Issues affect everyone immediately.

**Fix:**
- Canary deployments (10% traffic first)
- Blue/green deployments
- Rolling deployments with health checks

```python
deployment_config = codedeploy.EcsDeploymentConfig.CANARY_10_PERCENT_5_MINUTES
```

### Missing Rollback Strategy

**What:** No plan for reverting failed deployments.

**Why Bad:** Extended downtime during incidents.

**Fix:**
- Automated rollback on health check failure
- Keep previous versions available
- Database migrations must be backward compatible

## CDK-Specific Anti-Patterns

### Cross-Stack References Creating Circular Dependencies

**What:** Stacks that depend on each other's outputs.

**Why Bad:** Deployment failures, can't update or delete.

```python
# Bad: Circular reference
# Stack A exports bucket ARN
# Stack B uses bucket, exports role ARN
# Stack A uses role

# Good: Dependency injection via props
class DatabaseStack(Stack):
    def __init__(self, ...):
        self.table = dynamodb.Table(...)

class ApiStack(Stack):
    def __init__(self, ..., database_stack: DatabaseStack):
        # Use database_stack.table directly
```

### Not Using cdk-nag

**What:** No automated security/best practice checks.

**Fix:**
```python
from cdk_nag import AwsSolutionsChecks

app = App()
Aspects.of(app).add(AwsSolutionsChecks())
```

## Detection Commands

```bash
# Find hardcoded account IDs
rg "[0-9]{12}" --type ts --type py

# Find hardcoded ARNs
rg "arn:aws:" --type ts --type py

# Find public access
rg -i "public.*true|publicly.*accessible" --type ts --type yaml

# Find permissive IAM
rg '"\\*"' --type ts --type py | grep -i "action\|resource"

# Run CDK synth and check for warnings
cdk synth 2>&1 | grep -i "warning\|error"
```

## References

- [AWS Cloud Design Patterns](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/introduction.html)
- [AWS DevOps Anti-Patterns](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/anti-patterns-for-advanced-deployment-strategies.html)
- [AWS Anti-Patterns Guide](https://www.techtarget.com/searchcloudcomputing/feature/A-look-at-AWS-antipatterns-What-not-to-do-in-the-cloud)
- [10 Cloud Antipatterns](https://en.paradigmadigital.com/dev/10-cloud-antipatterns/)
