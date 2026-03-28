# AWS CDK Best Practices

This guide covers AWS CDK best practices for stack organization, construct design, security, and maintainability.

## Stack Organization

### Model with Constructs, Deploy with Stacks

**Constructs** represent logical units of your application (e.g., "API Service", "Data Pipeline").
**Stacks** represent deployment units.

```typescript
// GOOD: Logical unit as a construct
class ApiService extends Construct {
  public readonly api: apigateway.RestApi;
  public readonly handler: lambda.Function;

  constructor(scope: Construct, id: string, props: ApiServiceProps) {
    super(scope, id);
    // All API-related resources defined here
  }
}

// Stack composes constructs for deployment
class ProductionStack extends Stack {
  constructor(scope: Construct, id: string, props: StackProps) {
    super(scope, id, props);

    new ApiService(this, 'Api', { /* props */ });
    new DataPipeline(this, 'Pipeline', { /* props */ });
  }
}
```

### Layered Architecture

Organize stacks in layers with clear dependency direction:

```
┌─────────────────────────────────────────┐
│           Presentation Layer            │  (CloudFront, Route53)
│              Depends on ↓               │
├─────────────────────────────────────────┤
│           Stateless Layer               │  (Lambda, API Gateway, ECS)
│              Depends on ↓               │
├─────────────────────────────────────────┤
│           Stateful Layer                │  (RDS, DynamoDB, S3)
│              Depends on ↓               │
├─────────────────────────────────────────┤
│           Foundation Layer              │  (VPC, Subnets, Security Groups)
└─────────────────────────────────────────┘
```

**Rules:**
- Dependencies flow DOWN only
- No circular dependencies
- Foundation changes rarely
- Stateful resources are protected

### Separate Stateful from Stateless

```typescript
// Stateful stack - rarely changes, protected
class DataStack extends Stack {
  public readonly table: dynamodb.Table;
  public readonly bucket: s3.Bucket;

  constructor(scope: Construct, id: string, props: StackProps) {
    super(scope, id, {
      ...props,
      terminationProtection: true,  // Protect from accidental deletion
    });

    this.table = new dynamodb.Table(this, 'Table', {
      removalPolicy: RemovalPolicy.RETAIN,  // Never delete data
      pointInTimeRecovery: true,
    });
  }
}

// Stateless stack - changes frequently
class ComputeStack extends Stack {
  constructor(scope: Construct, id: string, props: ComputeStackProps) {
    super(scope, id, props);

    // Use string references to stateful resources
    const table = dynamodb.Table.fromTableArn(this, 'Table', props.tableArn);
  }
}
```

### Stack Size Guidelines

| Metric | Guideline | Why |
|--------|-----------|-----|
| Resources | < 500 per stack | CloudFormation limit is 500 |
| Parameters | < 60 per stack | CloudFormation limit is 200 |
| Outputs | < 60 per stack | CloudFormation limit is 200 |
| Template size | < 1MB | CloudFormation limit |
| Deployment time | < 30 minutes | Practical limit for feedback |

**Signs you need to split a stack:**
- Deployment takes > 30 minutes
- Approaching 500 resources
- Unrelated resources changing together
- Multiple teams owning different resources

---

## Construct Design

### Accept Configuration via Props

```typescript
// GOOD: Configurable via props
interface MyConstructProps {
  bucketName?: string;
  enableVersioning?: boolean;
  environment: 'dev' | 'staging' | 'prod';
}

class MyConstruct extends Construct {
  constructor(scope: Construct, id: string, props: MyConstructProps) {
    super(scope, id);

    new s3.Bucket(this, 'Bucket', {
      bucketName: props.bucketName,
      versioned: props.enableVersioning ?? true,
    });
  }
}

// BAD: Reading from environment variables in constructs
class BadConstruct extends Construct {
  constructor(scope: Construct, id: string) {
    super(scope, id);

    // Don't do this! Makes testing hard, non-deterministic
    const bucketName = process.env.BUCKET_NAME;
  }
}
```

### Environment Variables Only at App Level

```typescript
// bin/app.ts - ONLY place for env vars
const app = new App();

const environment = process.env.ENVIRONMENT || 'dev';
const config = loadConfig(environment);

new MyStack(app, `MyStack-${environment}`, {
  env: { account: config.account, region: config.region },
  bucketName: config.bucketName,  // Pass as props, not env var
});
```

### Logical ID Stability

Logical IDs determine resource identity. Changing them causes resource replacement.

```typescript
// Logical ID = construct path + id
// MyStack/MyConstruct/Bucket → MyStackMyConstructBucket1234ABCD

// DANGER: Changing construct ID
new s3.Bucket(this, 'Bucket');      // Original
new s3.Bucket(this, 'DataBucket');  // Changed ID = NEW RESOURCE!

// DANGER: Moving in construct tree
class OldStructure extends Construct {
  constructor(scope: Construct, id: string) {
    super(scope, id);
    new s3.Bucket(this, 'Bucket');  // Path: Stack/OldStructure/Bucket
  }
}

class NewStructure extends Construct {
  constructor(scope: Construct, id: string) {
    super(scope, id);
    // Moving bucket here = NEW RESOURCE!
    new s3.Bucket(this, 'Bucket');  // Path: Stack/NewStructure/Bucket
  }
}
```

### Test Logical ID Stability

```typescript
import { Template } from 'aws-cdk-lib/assertions';

test('Stateful resource logical IDs are stable', () => {
  const app = new App();
  const stack = new MyStack(app, 'TestStack');
  const template = Template.fromStack(stack);

  // Assert specific logical IDs haven't changed
  template.hasResource('AWS::DynamoDB::Table', {
    // Use exact logical ID from previous deployment
    LogicalId: 'MyTableABCD1234',
  });
});
```

---

## Resource Naming

### Prefer Generated Names

```typescript
// GOOD: Let CDK generate names
new s3.Bucket(this, 'Bucket');
// Name: mystack-bucket1234abcd-xyz

// BAD: Hardcoded names
new s3.Bucket(this, 'Bucket', {
  bucketName: 'my-company-bucket',  // Causes problems!
});
```

**Problems with hardcoded names:**
- Can't deploy multiple copies of stack
- Can't change immutable properties (requires replacement)
- Name collisions across environments

### When Names Are Necessary

Some resources require names (e.g., SSM parameters, some integrations):

```typescript
// Use environment/stage prefix for uniqueness
const prefix = `${props.environment}-${props.stage}`;

new ssm.StringParameter(this, 'Param', {
  parameterName: `/${prefix}/my-app/config`,
  stringValue: 'value',
});
```

---

## IAM Best Practices

### Use Grant Methods

```typescript
// GOOD: Grant methods create minimal permissions
const bucket = new s3.Bucket(this, 'Bucket');
const handler = new lambda.Function(this, 'Handler', { /* ... */ });

bucket.grantRead(handler);  // Only s3:GetObject, s3:ListBucket
bucket.grantWrite(handler); // Only s3:PutObject, s3:DeleteObject
bucket.grantReadWrite(handler); // Both

// BAD: Manual overly-permissive policy
handler.addToRolePolicy(new iam.PolicyStatement({
  actions: ['s3:*'],
  resources: ['*'],
}));
```

### Scope Permissions to Resources

```typescript
// GOOD: Scoped to specific resources
handler.addToRolePolicy(new iam.PolicyStatement({
  actions: ['dynamodb:GetItem', 'dynamodb:PutItem'],
  resources: [table.tableArn],
}));

// BAD: Wildcard resources
handler.addToRolePolicy(new iam.PolicyStatement({
  actions: ['dynamodb:GetItem', 'dynamodb:PutItem'],
  resources: ['*'],  // Too permissive!
}));
```

### Use Conditions When Appropriate

```typescript
handler.addToRolePolicy(new iam.PolicyStatement({
  actions: ['s3:GetObject'],
  resources: [`${bucket.bucketArn}/*`],
  conditions: {
    StringEquals: {
      's3:ExistingObjectTag/classification': 'public',
    },
  },
}));
```

---

## Environment Configuration

### Build Environments into Code

```typescript
// config/environments.ts
export const environments = {
  dev: {
    account: '111111111111',
    region: 'us-east-1',
    instanceType: 't3.micro',
    minCapacity: 1,
  },
  staging: {
    account: '222222222222',
    region: 'us-east-1',
    instanceType: 't3.small',
    minCapacity: 2,
  },
  prod: {
    account: '333333333333',
    region: 'us-east-1',
    instanceType: 't3.medium',
    minCapacity: 3,
  },
};

// bin/app.ts
const envName = process.env.ENVIRONMENT || 'dev';
const config = environments[envName];

new MyStack(app, `MyStack-${envName}`, {
  env: { account: config.account, region: config.region },
  instanceType: config.instanceType,
  minCapacity: config.minCapacity,
});
```

### Use Secrets Manager for Sensitive Values

```typescript
// Retrieve secret at synthesis (for CDK operations)
const secret = secretsmanager.Secret.fromSecretNameV2(
  this, 'Secret', 'my-app/api-key'
);

// Pass to Lambda as environment variable (resolved at deploy time)
new lambda.Function(this, 'Handler', {
  environment: {
    API_KEY: secret.secretValue.unsafeUnwrap(),  // Use carefully!
  },
});

// Better: Let Lambda retrieve at runtime
new lambda.Function(this, 'Handler', {
  environment: {
    SECRET_ARN: secret.secretArn,
  },
});
secret.grantRead(handler);
```

---

## Testing Infrastructure

### Snapshot Testing

```typescript
import { Template } from 'aws-cdk-lib/assertions';

test('Stack matches snapshot', () => {
  const app = new App();
  const stack = new MyStack(app, 'TestStack');
  const template = Template.fromStack(stack);

  expect(template.toJSON()).toMatchSnapshot();
});
```

### Fine-Grained Assertions

```typescript
test('Creates DynamoDB table with correct configuration', () => {
  const app = new App();
  const stack = new MyStack(app, 'TestStack');
  const template = Template.fromStack(stack);

  template.hasResourceProperties('AWS::DynamoDB::Table', {
    BillingMode: 'PAY_PER_REQUEST',
    PointInTimeRecoverySpecification: {
      PointInTimeRecoveryEnabled: true,
    },
    SSESpecification: {
      SSEEnabled: true,
    },
  });
});
```

### Test Resource Counts

```typescript
test('Creates expected number of Lambda functions', () => {
  const template = Template.fromStack(stack);

  template.resourceCountIs('AWS::Lambda::Function', 3);
});
```

---

## Aspects for Enforcement

Use Aspects to enforce policies across all resources:

```typescript
import { IAspect, Annotations } from 'aws-cdk-lib';
import { IConstruct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';

class BucketVersioningChecker implements IAspect {
  visit(node: IConstruct): void {
    if (node instanceof s3.Bucket) {
      if (!node.versioned) {
        Annotations.of(node).addError('S3 buckets must have versioning enabled');
      }
    }
  }
}

class RequiredTagsChecker implements IAspect {
  constructor(private readonly requiredTags: string[]) {}

  visit(node: IConstruct): void {
    if (Tags.of(node)) {
      for (const tag of this.requiredTags) {
        // Check tag exists
      }
    }
  }
}

// Apply to app
Aspects.of(app).add(new BucketVersioningChecker());
Aspects.of(app).add(new RequiredTagsChecker(['Environment', 'CostCenter']));
```

---

## Common Anti-Patterns

### Anti-Pattern: Giant Monolithic Stack

```typescript
// BAD: Everything in one stack
class EverythingStack extends Stack {
  constructor(scope: Construct, id: string) {
    super(scope, id);

    // VPC, databases, lambdas, APIs, frontends all here
    // 400+ resources, 45 minute deployments
  }
}

// GOOD: Split by concern
class NetworkStack extends Stack { /* VPC, subnets */ }
class DataStack extends Stack { /* RDS, DynamoDB */ }
class ComputeStack extends Stack { /* Lambda, ECS */ }
class ApiStack extends Stack { /* API Gateway */ }
```

### Anti-Pattern: Passing L2 Constructs Between Stacks

```typescript
// BAD: Creates cross-stack exports
const dataStack = new DataStack(app, 'Data');
new ComputeStack(app, 'Compute', {
  table: dataStack.table,  // L2 construct = export!
});

// GOOD: Pass identifiers as strings
const dataStack = new DataStack(app, 'Data');
new ComputeStack(app, 'Compute', {
  tableArn: 'arn:aws:dynamodb:...',  // String from config
});
```

### Anti-Pattern: Synthesis-Time Lookups for Cross-Stack Data

```typescript
// BAD: SSM lookup at synthesis creates dependency
const param = ssm.StringParameter.fromStringParameterName(
  this, 'Param', '/other-stack/resource-id'
);
// param.stringValue is a Token, not a string!

// GOOD: Store in config, read at runtime
const resourceId = config.resources.tableArn;  // Plain string
```

### Anti-Pattern: Hardcoded Account/Region

```typescript
// BAD: Hardcoded values
new Stack(app, 'MyStack', {
  env: { account: '123456789012', region: 'us-east-1' },
});

// GOOD: From config or environment
new Stack(app, 'MyStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});
```

---

## Repository Hygiene

### Critical .gitignore Patterns

CDK generates build artifacts that should never be committed:

```gitignore
# CDK output directories - include ALL variants
cdk.out/
cdk/cdk.out/
cdk/cdk.out2/        # Alternate output from different deploy scripts!
cdk/cdk.out.backup/  # Manual backups
.cdk.staging/
cdk-outputs.json

# CDK context (optional - can be committed for reproducibility)
# cdk.context.json
```

**Common Mistake:** Only excluding `cdk.out/` while alternate output directories (`cdk.out2`, `cdk.out.dev`, etc.) slip through. These are created when:
- Using different `--output` flags in deploy scripts
- Running parallel deployments to different stages
- Manual CDK synth with custom output paths

### Asset Bundling: Exclude .git Directories

CDK asset bundling can accidentally include `.git` directories, causing **massive repository bloat** (3-5MB per asset copy).

```typescript
// GOOD: Exclude .git in asset bundling
new lambda.Function(this, 'Handler', {
  code: lambda.Code.fromAsset('../lambda', {
    exclude: [
      '.git',
      '.git/**',
      '__pycache__',
      '*.pyc',
      '.pytest_cache',
      '.mypy_cache',
      '.venv',
      'node_modules',
      '*.md',
      'tests',
    ],
  }),
});

// For Python bundling with requirements
new lambda.PythonFunction(this, 'Handler', {
  entry: '../lambda',
  bundling: {
    assetExcludes: ['.git', '.venv', '__pycache__', 'tests'],
  },
});
```

**Symptoms of .git in assets:**
- `cdk.out/asset.*` directories are 10-50MB+ each
- Multiple copies of git history in build output
- Repository grows rapidly after CDK deployments

**Audit command:**
```bash
# Find .git directories in CDK output
find cdk.out -name ".git" -type d 2>/dev/null

# Check asset sizes
du -sh cdk.out/asset.* | sort -h
```

### Pre-Commit CDK Checks

Add to `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: no-cdk-output
      name: Ensure no CDK output committed
      entry: bash -c 'git diff --cached --name-only | grep -E "cdk\.out|cdk\.out2" && exit 1 || exit 0'
      language: system
      pass_filenames: false
```

---

## Summary Checklist

### Stack Organization
- [ ] Constructs for logical units, stacks for deployment
- [ ] Layered architecture (Foundation → Stateful → Stateless → Presentation)
- [ ] Stateful resources in protected stacks
- [ ] Stacks < 500 resources

### Construct Design
- [ ] Configuration via props, not env vars
- [ ] Logical IDs stable for stateful resources
- [ ] Tests verify logical ID stability

### Resource Naming
- [ ] Generated names preferred
- [ ] Environment prefix when names required

### IAM
- [ ] Grant methods used
- [ ] No wildcard resources
- [ ] Least privilege applied

### Cross-Stack References
- [ ] No L2 constructs passed between stacks
- [ ] String identifiers in config
- [ ] No synthesis-time lookups for cross-stack data
