# Cross-Stack Dependencies in AWS CDK

This guide covers detection, prevention, and remediation of cross-stack dependency issues - the most common cause of CDK deployment deadlocks.

## Why Cross-Stack Dependencies Are Problematic

When you pass a resource from one CDK stack to another, CDK automatically creates CloudFormation exports and imports. This creates tight coupling that causes:

1. **Deployment Deadlocks** - Can't update Stack A without updating Stack B first, but Stack B depends on Stack A
2. **Deletion Failures** - Can't delete a stack if another stack imports its values
3. **Circular Dependencies** - Stack A → B → A creates unresolvable loops
4. **Cascade Updates** - Simple changes require updating multiple stacks in order

### How CDK Creates Implicit Exports

```typescript
// Stack A
const bucket = new s3.Bucket(this, 'MyBucket');

// Stack B - passing the bucket creates an implicit export!
new lambda.Function(this, 'Handler', {
  environment: { BUCKET_NAME: bucket.bucketName }
});
```

When you pass `bucket.bucketName` to another stack, CDK:
1. Creates a `CfnOutput` with `Export` in Stack A
2. Uses `Fn::ImportValue` in Stack B
3. CloudFormation now enforces this dependency

---

## Top 10 Tips & Tricks

These practical tips come from real-world experience fixing cross-stack issues:

### 1. L1 (Cfn) Constructs with Plain Strings = No Exports

This is the **golden rule**. L1 constructs with hardcoded strings don't create cross-stack references.

```typescript
// SAFE - no export created
new CfnFunction(this, 'Handler', {
  environment: {
    variables: { BUCKET_NAME: 'my-bucket-name-from-config' }
  }
});
```

### 2. ⚠️ Parameter Store Lookups at Synthesis Time Return Tokens

**THIS IS THE #1 MISTAKE when trying to fix cross-stack dependencies.**

Even though `param.stringValue` looks like a string, it's a CloudFormation reference token:

```typescript
// ❌ WRONG - this creates a cross-stack reference!
const param = ssm.StringParameter.fromStringParameterName(this, 'Param', '/my/param');
// param.stringValue is NOT a string - it's a Token!
console.log(param.stringValue);  // Prints: ${Token[TOKEN.123]}
```

```python
# ❌ WRONG - Same problem in Python!
param = ssm.StringParameter.from_string_parameter_name(self, "Param", "/my/param")
value = param.string_value  # This is a TOKEN, not a string!
```

**Why this fails:**
1. `.stringValue` / `.string_value` returns a CloudFormation Token
2. Tokens resolve at **deploy time**, not synthesis time
3. Using this Token creates the exact cross-stack export you're trying to avoid

**Solution:** Read SSM parameters at **runtime** in Lambda code, not at synthesis time.

### 3. Store Resource IDs in Config Files After Initial Creation

Get the ID once after first deployment, store it in a config file, never look it up again at synthesis time.

```typescript
// config.ts
export const config = {
  bucketName: 'myapp-bucket-abc123',  // Set after first deploy
  tableName: 'myapp-table-xyz789',
};

// Use in other stacks
new lambda.Function(this, 'Handler', {
  environment: { BUCKET_NAME: config.bucketName }
});
```

### 4. Lambda ARN References Are Safe

`Function.fromFunctionAttributes()` with an ARN string doesn't create exports.

```typescript
// SAFE - no export
const fn = lambda.Function.fromFunctionAttributes(this, 'ImportedFn', {
  functionArn: 'arn:aws:lambda:us-east-1:123456789:function:my-function',
  sameEnvironment: true,
});
```

### 5. L2 Constructs Are Convenient but Dangerous for Cross-Stack

Use L2 constructs within a stack, avoid passing them between stacks.

```typescript
// WITHIN same stack - fine
const bucket = new s3.Bucket(this, 'Bucket');
bucket.grantRead(myLambda);

// ACROSS stacks - dangerous!
// Passing 'bucket' to another stack creates exports
```

### 6. Delete Old Routes Before Deploying L1 Replacements

API Gateway will error on duplicate route keys. When migrating from L2 to L1:

```bash
# 1. Delete the L2 route first
# 2. Deploy to remove it
# 3. Add the L1 replacement
# 4. Deploy again
```

### 7. Not All Exports Are Bad

Exports for truly separate systems (like MCP Gateway, external consumers) are acceptable. The problem is exports between stacks that should be independent.

**Acceptable:**
- Exports consumed by completely separate applications
- Exports for manual reference

**Problematic:**
- Exports between stacks in the same CDK app
- Exports that create deployment ordering requirements

### 8. Verify with AWS CLI

Trust but verify. Always check what CloudFormation actually created.

```bash
# List all exports
aws cloudformation list-exports --query 'Exports[*].[Name,ExportingStackId]' --output table

# List what imports a specific export
aws cloudformation list-imports --export-name MyExportName

# Check a specific stack's outputs
aws cloudformation describe-stacks --stack-name MyStack --query 'Stacks[0].Outputs'
```

### 9. Fix One Stack at a Time

Incremental migration is safer than trying to fix everything at once.

1. Identify the most problematic dependency
2. Fix that one stack
3. Deploy and verify
4. Move to the next stack

### 10. Test by Updating the Source Stack

The ultimate test: if you can't update the stack that creates a resource without touching dependent stacks, you have a dependency problem.

```bash
# Can you deploy just this stack?
npx cdk deploy MySourceStack

# If this fails due to "Export cannot be updated", you have a problem
```

---

## Detection Methods

### Method 1: Grep Synthesized Templates

```bash
npx cdk synth --all --quiet

# Find exports
grep -r '"Export"' cdk.out/*.template.json

# Find imports
grep -r 'Fn::ImportValue' cdk.out/*.template.json
```

### Method 2: Custom IValidation Class

Implement a validator that fails synthesis if exports are detected:

```python
import aws_cdk as cdk
from constructs import IConstruct, IValidation
import jsii

@jsii.implements(IValidation)
class NoExportsValidator:
    def __init__(self, stack: cdk.Stack) -> None:
        self.stack = stack

    def validate(self) -> list[str]:
        errors = []
        for child in self.stack.node.children:
            if child.node.id == "Exports":
                errors.append(
                    f"Stack {self.stack.stack_name} has CloudFormation exports. "
                    "Cross-stack references are not allowed."
                )
        return errors

# Add to your stack
self.node.add_validation(NoExportsValidator(stack=self))
```

### Method 3: AWS CLI Audit

```bash
# List all exports in account
aws cloudformation list-exports

# For each export, find importers
for export in $(aws cloudformation list-exports --query 'Exports[*].Name' --output text); do
  echo "=== $export ==="
  aws cloudformation list-imports --export-name "$export" 2>/dev/null || echo "No imports"
done
```

---

## Safe Cross-Stack Patterns

### Pattern 1: Config File with Known Values

```typescript
// config/resources.ts
export const resources = {
  production: {
    vpcId: 'vpc-abc123',
    bucketName: 'prod-bucket-xyz',
    tableArn: 'arn:aws:dynamodb:us-east-1:123456789:table/MyTable',
  },
  staging: {
    vpcId: 'vpc-def456',
    bucketName: 'staging-bucket-xyz',
    tableArn: 'arn:aws:dynamodb:us-east-1:123456789:table/MyTable-staging',
  },
};

// Usage in any stack
const bucket = s3.Bucket.fromBucketName(this, 'Bucket', resources.production.bucketName);
```

### Pattern 2: SSM Parameter Store (Runtime Lookup)

```typescript
// Stack A: Store the value
new ssm.StringParameter(this, 'BucketNameParam', {
  parameterName: '/myapp/prod/bucket-name',
  stringValue: bucket.bucketName,
});

// Stack B: Lambda reads at runtime
const handler = new lambda.Function(this, 'Handler', {
  code: lambda.Code.fromInline(`
    const SSM = require('@aws-sdk/client-ssm');
    const client = new SSM.SSMClient();
    // Read parameter at runtime, not synthesis
  `),
});

// Grant permission to read the parameter
handler.addToRolePolicy(new iam.PolicyStatement({
  actions: ['ssm:GetParameter'],
  resources: ['arn:aws:ssm:*:*:parameter/myapp/*'],
}));
```

### Pattern 3: L1 Constructs with ARN Strings

```typescript
// Instead of passing the L2 construct
const tableArn = 'arn:aws:dynamodb:us-east-1:123456789:table/MyTable';

// Use L1 or fromArn methods
const table = dynamodb.Table.fromTableArn(this, 'Table', tableArn);
table.grantReadData(myLambda);
```

### Pattern 4: Environment-Specific Stack Props

```typescript
interface MyStackProps extends cdk.StackProps {
  bucketName: string;  // Pass as string, not Bucket construct
  tableArn: string;
}

class MyStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: MyStackProps) {
    super(scope, id, props);

    // Import using string ARN - no export created
    const table = dynamodb.Table.fromTableArn(this, 'Table', props.tableArn);
  }
}
```

### Pattern 5: Secrets Manager with Predictable Paths

For sensitive values (credentials, API keys), use a predictable naming convention:

```python
# Stack A (Producer): Creates secret at predictable path
customer = "my-customer"
environment = "prod"
secret_name = f"myapp/{customer}/{environment}/api-credentials"

secret = secretsmanager.Secret(
    self, "ApiSecret",
    secret_name=secret_name,
    generate_secret_string=secretsmanager.SecretStringGenerator(
        secret_string_template=json.dumps({"client_id": client_id}),
        generate_string_key="client_secret",
    ),
)

# Stack B (Consumer): Imports using plain string - NO export created
secret = secretsmanager.Secret.from_secret_name_v2(
    self,
    "ImportedSecret",
    secret_name=f"myapp/{customer}/{environment}/api-credentials",  # Plain string!
)
secret.grant_read(my_lambda)

# Lambda reads actual secret content at RUNTIME via SDK
```

**Key insight:** `from_secret_name_v2()` with a plain string path does NOT create a cross-stack dependency because:
- The path is constructed from config values, not Tokens
- The Lambda reads the actual secret content at runtime
- No CloudFormation export/import is created

### Pattern 6: Custom Resource with Runtime Secret Lookup

When CDK needs values from secrets during deployment, use a Lambda-backed Custom Resource:

```python
# Instead of passing secret values as CDK properties (creates exports),
# pass the secret NAME and have Lambda read it at runtime

from aws_cdk import custom_resources as cr

provider = cr.Provider(
    self, "Provider",
    on_event_handler=on_event_lambda,
)

custom_resource = CustomResource(
    self, "MyCustomResource",
    service_token=provider.service_token,
    properties={
        "SecretName": f"myapp/{environment}/credentials",  # Plain string
        # Lambda reads client_id, api_key from secret at runtime
    },
)

# In Lambda handler:
def on_event(event, context):
    secret_name = event['ResourceProperties']['SecretName']
    response = secrets_client.get_secret_value(SecretId=secret_name)
    secret_data = json.loads(response['SecretString'])
    # Use secret_data['client_id'], secret_data['api_key'] etc.
```

---

## Using fromXxxV2 Methods

CDK has `from_xxx_name_v2` methods that behave better for cross-stack imports:

```python
# ✅ Preferred - handles name-only lookups correctly
secret = secretsmanager.Secret.from_secret_name_v2(
    self, "Secret", secret_name="plain-string-name"
)

# ⚠️ Older method - may have issues with partial names
secret = secretsmanager.Secret.from_secret_name(...)  # Less preferred
```

**Why V2 methods are better:**
- Better handling of partial ARN resolution
- More consistent behavior across regions
- Recommended by AWS for new code

---

## Runtime vs Synthesis Decision Framework

Decide WHEN to read values based on their nature:

| Value Type | Read At | Method | Example |
|------------|---------|--------|---------|
| Resource IDs, ARNs | Synthesis | Config file with plain strings | VPC ID, Table ARN |
| Sensitive credentials | Runtime | Secrets Manager SDK call | API keys, passwords |
| Dynamic/changing values | Runtime | SSM Parameter Store SDK | Feature flags, URLs |
| Constructed ARNs | Synthesis | Build from known components | `arn:aws:s3:::${bucketName}` |

**Rule of thumb:**
- **Sensitive or frequently changing** → Read at runtime
- **Stable infrastructure identifiers** → Store in config file

---

## Secrets Manager vs Parameter Store

Choose the right storage based on the value type:

| Use Case | Storage | Cost | Why |
|----------|---------|------|-----|
| API keys, tokens | Secrets Manager | $0.40/secret/mo | Automatic rotation, encryption |
| Database passwords | Secrets Manager | $0.40/secret/mo | Audit logging, fine-grained access |
| OAuth client secrets | Secrets Manager | $0.40/secret/mo | Rotation support |
| Resource IDs, ARNs | Config file | Free | Version controlled, no AWS dependency |
| Feature flags | Parameter Store | Free | Simple key-value |
| Service URLs | Parameter Store | Free | Can change without redeploy |
| Non-sensitive config | Parameter Store | Free | Up to 10K params free |

**Cost comparison:**
- Secrets Manager: $0.40 per secret per month + $0.05 per 10,000 API calls
- Parameter Store Standard: Free (up to 10,000 parameters)
- Parameter Store Advanced: $0.05 per parameter per month

---

## Migration Strategy

### Step 1: Audit Current State

```bash
# Document all exports
aws cloudformation list-exports > current-exports.json

# Document all import relationships
# (script to iterate through exports and list imports)
```

### Step 2: Prioritize by Impact

1. **Circular dependencies** - Fix first, these block all deployments
2. **Frequently updated stacks** - High pain, high value to fix
3. **Long dependency chains** - Simplify deployment order
4. **Stable stacks** - Lower priority if rarely changed

### Step 3: Create Replacement Pattern

For each problematic export:
1. Add the replacement (config file, SSM, etc.)
2. Update consumers to use replacement
3. Deploy consumers
4. Remove the old export
5. Deploy producer

### Step 4: Verify Independence

After migration, test each stack can be deployed independently:

```bash
for stack in StackA StackB StackC; do
  echo "Testing $stack..."
  npx cdk diff $stack
  npx cdk deploy $stack --require-approval never
done
```

---

## Common Gotchas

### Token vs String Confusion

```typescript
// This LOOKS like a string but it's a Token
const bucketName = bucket.bucketName;
console.log(typeof bucketName);  // "string" - but it's not!
console.log(bucketName);  // "${Token[...]}"

// To check if something is a token
import { Token } from 'aws-cdk-lib';
if (Token.isUnresolved(bucketName)) {
  console.log('This will create a CloudFormation reference');
}
```

### fromXxx Methods Can Still Create Dependencies

```typescript
// SAFE - plain string ARN
const table = Table.fromTableArn(this, 'T', 'arn:aws:dynamodb:...');

// DANGEROUS - Token from another stack
const table = Table.fromTableArn(this, 'T', otherStack.table.tableArn);
```

### Grants Create References

```typescript
// This creates a cross-stack reference if bucket is from another stack
bucket.grantRead(myLambda);

// Instead, create the IAM policy explicitly with string ARN
myLambda.addToRolePolicy(new iam.PolicyStatement({
  actions: ['s3:GetObject'],
  resources: ['arn:aws:s3:::my-bucket-name/*'],
}));
```

---

## Summary

| Pattern | Safe? | Cost | Notes |
|---------|-------|------|-------|
| Stack props with plain strings | Yes | Free | **Recommended first choice** |
| Config file with known values | Yes | Free | Version controlled |
| L1 construct with plain string | Yes | Free | No exports |
| `fromXxxArn()` with string | Yes | Free | No exports |
| `from_secret_name_v2()` with string | Yes | Free | No export, reads at runtime |
| SSM Parameter Store runtime lookup | Yes | Free | Lambda reads via SDK |
| Secrets Manager runtime lookup | Yes | $0.40/mo | For sensitive values |
| Custom Resource runtime lookup | Yes | Free | For deploy-time secret access |
| L2 construct passed between stacks | **No** | - | Creates exports |
| `fromXxxArn()` with Token | **No** | - | Creates exports |
| SSM lookup at synthesis | **No** | - | Creates exports (Token!) |
| Grant methods across stacks | **No** | - | Creates exports |

### Priority Order for Resolving Dependencies

1. **Stack constructor props with plain strings** (Free, simplest)
2. **Config files with resource IDs** (Free, version controlled)
3. **SSM Parameter Store runtime lookup** (Free, for dynamic values)
4. **Secrets Manager runtime lookup** (Paid, for sensitive values only)
