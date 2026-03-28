# AWS Security Audit

Create a task list to follow this step by step guide to audit our aws security.  Each Section should be checked thoroughly and in order without skipping any.


Introduction: Establishing a Secure Foundation

You have been tasked with conducting a complete security audit of our current codebase. Before we can secure the code itself, we must first audit the foundation it's built upon. A secure application is impossible without a secure infrastructure, which is why this audit will begin with a thorough review of the Amazon Web Services (AWS) environment where our code is deployed and executed. Many critical vulnerabilities don't live in the application logic, but in the misconfiguration of the cloud services that support it. This guide will serve as your detailed, step-by-step manual for this process. It is designed specifically for developers and will walk you through each critical area, explaining not just what to check, but why it’s important for the overall security of our applications. The audit process is structured around three foundational pillars: understanding your responsibilities, adopting a strategic framework, and using a tactical checklist.

Section 1: Auditing Identity and Access Management (IAM) - The Keys to the Kingdom

Identity and Access Management (IAM) is the heart of security in AWS. It controls who (users, services) can access what (resources) under which conditions. Misconfigurations in IAM are one of the most common and dangerous sources of security breaches. This section of the audit focuses on verifying that a strong identity foundation has been implemented, adhering strictly to the principle of least privilege.

1.1. Securing the Root User: The Non-Negotiable First Step

The root user is the most privileged identity in an AWS account, with unrestricted access to all services and resources, including billing information. A compromise of the root user is a catastrophic event. Therefore, the first and highest-priority audit check is to ensure this account is locked down and not used for routine operations.
Audit Objective: Verify that the account's root user is secured and not used for daily tasks.
Step-by-Step Guide:
Check 1: Access Keys: Confirm that there are NO active access keys for the root user. Root access keys provide unrestricted programmatic access and are a significant security risk.18 This check requires credentials for the root user to be configured for the AWS CLI.
Bash
# This command should return an empty list.
# Run this command using root user credentials.
aws iam list-access-keys

If any keys exist, they must be immediately deactivated and deleted after confirming they are not in use.
Bash
# Deactivate the key
aws iam update-access-key --access-key-id <ACCESS_KEY_ID> --status Inactive

# Delete the key
aws iam delete-access-key --access-key-id <ACCESS_KEY_ID>


Check 2: Multi-Factor Authentication (MFA): Verify that MFA is enabled for the root user. The CIS Benchmark recommends using a hardware MFA device for the root user.13
Bash
# This command must be run with administrative privileges.
# The output should show "AccountMFAEnabled": 1
aws iam get-account-summary

If MFA is not active, it must be enabled immediately. Once these checks are complete, the root user credentials should be securely stored, and an IAM user with administrative privileges should be used for all day-to-day administrative tasks.

1.2. Reviewing IAM Users, Groups, and Credentials

This part of the audit focuses on how human users access the AWS account, ensuring that strong authentication and credential management practices are enforced.
Audit Objective: Ensure human access is managed securely, adhering to best practices for passwords and MFA.
Step-by-Step Guide:
Check 1: Password Policy: Audit the current account password policy against established best practices. A strong policy is a fundamental defense against brute-force attacks.18
Bash
# View the current password policy
aws iam get-account-password-policy

If the policy is weak, update it to enforce stronger requirements.
Bash
# Example: Update the password policy
aws iam update-account-password-policy \
  --minimum-password-length 14 \
  --require-symbols \
  --require-numbers \
  --require-uppercase-characters \
  --require-lowercase-characters \
  --password-reuse-prevention 5 \
  --max-password-age 90


Check 2: MFA Enforcement: Verify that MFA is active for every user with console access. This can be enforced with an IAM policy that denies actions if the user is not authenticated with MFA.22

Example MFA Enforcement Policy:
JSON
{
    "Version": "2012-10-17",
    "Statement":,
            "Resource": "*",
            "Condition": {
                "BoolIfExists": {
                    "aws:MultiFactorAuthPresent": "false"
                }
            }
        }
    ]
}

Save this policy to a file (e.g., enforce-mfa-policy.json) and apply it to a group containing all human users.
Bash
# Create the policy
aws iam create-policy --policy-name EnforceMFA --policy-document file://enforce-mfa-policy.json

# Attach the policy to a user group
aws iam attach-group-policy --group-name AllConsoleUsers --policy-arn <policy_arn>


Check 3: Unused Credentials: Generate and download the IAM credential report to find dormant users or unused access keys.18
Bash
# Start the report generation
aws iam generate-credential-report

# Wait a few moments, then download and decode the report
aws iam get-credential-report --query 'Content' --output text | base64 --decode > credential_report.csv

Analyze the downloaded credential_report.csv file for users with password_last_used or access_key_*_last_used_date older than 90 days. These dormant credentials represent an unnecessary security risk and should be disabled or deleted.

1.3. Analyzing IAM Policies and Roles for Least Privilege

The principle of least privilege dictates that an identity should only have the exact permissions required to perform its function, and no more.9 Overly permissive policies are a common finding and can dramatically increase the "blast radius" of a compromised credential.
Audit Objective: Identify and remediate overly permissive IAM policies.
Step-by-Step Guide:
Check 1: Manual Policy Review: Systematically review customer-managed policies for overly broad permissions, such as Action: "*", Resource: "*".19
Bash
# List customer-managed policies
aws iam list-policies --scope Local --query 'Policies[*].Arn'

# For each policy ARN, get the default policy version
aws iam get-policy --policy-arn <policy_arn> --query 'Policy.DefaultVersionId'

# Get the policy document for review
aws iam get-policy-version --policy-arn <policy_arn> --version-id <version_id>

The audit should identify these policies and recommend scoping them down to specific actions (e.g., s3:GetObject instead of s3:*) and specific resources (e.g., an ARN for a specific S3 bucket instead of *).26
Check 2: Use IAM Access Analyzer: This service automatically analyzes resource-based policies to identify resources shared with an external principal, which is invaluable for finding misconfigurations that grant public or unintended cross-account access.25
Bash
# List analyzers in the region
aws accessanalyzer list-analyzers

# List active findings for a specific analyzer
aws accessanalyzer list-findings --analyzer-arn <analyzer_arn> --filter status=ACTIVE

Review any active findings. Each finding provides details on the shared resource and the external principal, allowing for targeted remediation.

1.4. Auditing Programmatic Access: Access Keys

Long-lived static credentials like access keys are a primary target for attackers. Once compromised, they can be used from anywhere in the world. Auditing their management and lifecycle is critical.
Audit Objective: Minimize the risk associated with long-lived static credentials.
Step-by-Step Guide:
Check 1: Key Rotation: Using the Credential Report downloaded in section 1.2, filter the access_key_1_active and access_key_2_active columns to find all TRUE values. Then, check the corresponding access_key_*_last_rotated column. Any active key that has not been rotated in over 90 days is a security finding.19
Action: Rotate Keys: A key rotation must be performed carefully to avoid application downtime. The following five-step process is the recommended, safe procedure 86:
Create a new access key for the IAM user.
Bash
aws iam create-access-key --user-name <user_name>


Update all applications and tools that use the old key to use the new key.
Change the state of the old key to Inactive.
Bash
aws iam update-access-key --access-key-id <old_access_key_id> --status Inactive --user-name <user_name>


Validate that all applications are still working as expected with the new key.
Once confirmed, delete the inactive, old key.
Bash
aws iam delete-access-key --access-key-id <old_access_key_id> --user-name <user_name>



1.5. EC2 Instance Profiles vs. Static Keys: A Critical Distinction

A common anti-pattern among developers new to AWS is to create an IAM user, generate access keys, and then embed those keys into an application's configuration file or environment variables on an EC2 instance. This practice is highly insecure. The correct approach is to use IAM Roles for EC2. Finding static keys on an instance is not merely a configuration error; it often signals a fundamental misunderstanding of core AWS security mechanisms, indicating a need for both technical remediation and developer education.
Audit Objective: Eradicate the use of hard-coded IAM user access keys on EC2 instances.
Step-by-Step Guide:
The "Why": The audit should begin by explaining the superiority of IAM Roles.
Static Access Keys: These are long-lived credentials. If an instance is compromised, an attacker can exfiltrate these keys and use them from their own machine indefinitely, or until the keys are manually rotated. Managing and rotating these keys across a fleet of instances is a significant operational burden.31
IAM Roles for EC2: When an IAM Role is attached to an EC2 instance, the instance is granted the ability to request temporary security credentials from the EC2 metadata service. These credentials (an access key, a secret key, and a session token) are automatically rotated by AWS, typically every few hours. They are only available from the instance's metadata endpoint (http://169.254.169.254/latest/meta-data/) and cannot be used from outside the instance. The AWS SDKs and CLI are designed to automatically and transparently retrieve these credentials, meaning no code changes are needed to switch from static keys to a role.31
Check 1: Instance Configuration: Check each running instance to see if it has an IAM role attached.
Bash
# Query for instance IDs and their associated IAM instance profile ARN
aws ec2 describe-instances --query "Reservations[*].Instances[*].[InstanceId, IamInstanceProfile.Arn]" --output text

If the ARN column is blank for an instance, it is a major security red flag, suggesting the application on the instance might be using static keys.
Check 2: Search for Hard-coded Keys: This is a crucial, though more manual, part of the audit. The development team must be instructed to scan their application code repositories, deployment scripts, and configuration files using command-line tools like grep for any instances of AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY. Finding these hard-coded credentials is a high-severity issue that requires immediate remediation by replacing them with an IAM Role.

Section 2: Auditing Network and Infrastructure Protection

This section focuses on the controls that protect your AWS resources from network-based threats. It involves auditing the logical network structure (VPC), the firewall rules that govern traffic flow (Security Groups and NACLs), and the security posture of the compute instances themselves (EC2). The goal is to ensure a defense-in-depth approach, where multiple layers of security work together to protect critical assets.

2.1. Virtual Private Cloud (VPC) Sanity Check

A VPC is a logically isolated section of the AWS Cloud where resources are launched. A well-designed VPC uses segmentation to separate resources with different security requirements, preventing an attacker who compromises one part of the system from easily moving to another.
Audit Objective: Ensure the VPC is logically segmented to protect internal resources.
Step-by-Step Guide:
Check 1: Public vs. Private Subnets: A subnet is public if its route table has a route to an Internet Gateway (IGW).36 A subnet is
private if it does not.
Bash
# Describe route tables to identify routes to an internet gateway (igw-*)
aws ec2 describe-route-tables --query "RouteTables]"

Review the Associations in the output to see which subnets are associated with these public route tables.
Check 2: Resource Placement: Verify that sensitive resources like databases are in private subnets. Only resources like web servers or load balancers should be in public subnets.38
Bash
# Check instances in a given subnet
aws ec2 describe-instances --filters "Name=subnet-id,Values=<subnet-id>"

# Check RDS instances and their subnets
aws rds describe-db-instances --query "DBInstances[*]..SubnetIdentifier]"

An RDS instance found in a public subnet is a critical security finding.
Check 3: NAT Gateway for Private Subnets: Instances in private subnets that need outbound internet access should use a NAT Gateway.36
Bash
# Describe route tables and look for routes to a NAT gateway (nat-*)
aws ec2 describe-route-tables --query "RouteTables]"

Verify that this route table is associated with your private subnets.

2.2. Firewall Layers: Security Groups and Network Access Control Lists (NACLs)

AWS provides two layers of virtual firewalls: Security Groups (SGs) and Network Access Control Lists (NACLs). Using both effectively creates a robust defense-in-depth strategy.
Audit Objective: Verify that firewall rules are configured according to the principle of least privilege.
Step-by-Step Guide:
Check 1: Auditing Security Groups (SGs): Security Groups act as a stateful firewall for resources.41 The most critical finding is an overly permissive rule allowing traffic from
0.0.0.0/0 to management ports like SSH (22) or RDP (3389).41
Bash
# Describe security groups and filter for inbound rules open to the internet
aws ec2 describe-security-groups \
  --filters Name=ip-permission.cidr,Values='0.0.0.0/0' \
  --query "SecurityGroups[*]..CidrIp, '0.0.0.0/0')]]"

Review the output for any rules allowing access to sensitive ports. Also, verify that security groups are chained correctly (e.g., a database SG should only allow traffic from an application SG).44
Check 2: Auditing Network ACLs (NACLs): NACLs are a stateless firewall at the subnet level.45 While the default NACL allows all traffic, it is a best practice to create custom, more restrictive NACLs for sensitive subnets.
Bash
# Describe a specific network ACL to review its rules
aws ec2 describe-network-acls --network-acl-ids <acl-id>

For a private subnet, a custom NACL could explicitly Allow traffic from the application subnet's CIDR range and Deny all other traffic. Remember that because NACLs are stateless, you must also add a corresponding outbound rule to allow response traffic.47

Table 2: Security Group vs. NACL: Key Differences

Feature
Security Group (SG)
Network Access Control List (NACL)
Scope
Operates at the resource level (e.g., EC2 instance, RDS instance).
Operates at the subnet level, affecting all resources within that subnet.
Statefulness
Stateful: If you allow inbound traffic, the return traffic is automatically allowed.
Stateless: Return traffic must be explicitly allowed by an outbound rule.
Rule Types
Supports Allow rules only. Traffic is implicitly denied if no allow rule matches.
Supports both Allow and Deny rules.
Rule Evaluation
All rules are evaluated before making a decision.
Rules are evaluated in numerical order, from lowest to highest. The first matching rule is applied.
Association
A resource can be associated with multiple SGs.
A subnet can be associated with only one NACL at a time.


2.3. Hardening Amazon EC2 Instances

Beyond the network firewalls, the security of the guest operating system on an EC2 instance is a crucial customer responsibility. This process is often referred to as "hardening."
Audit Objective: Ensure the guest operating system and instance configuration are secure.
Step-by-Step Guide:
Check 1: AMI Selection: Verify that instances are launched from trusted and up-to-date Amazon Machine Images (AMIs). Best practice is to maintain internal "golden AMIs" that are pre-hardened and scanned.48
Check 2: Patch Management: The customer must patch the guest OS.1 Confirm that a patch management process is in place, preferably using
AWS Systems Manager Patch Manager.49
Bash
# Check the patch compliance status for an instance
aws ssm describe-instance-patch-states --instance-ids <instance-id>


Check 3: IMDSv2 Enforcement: The Instance Metadata Service Version 2 (IMDSv2) is more secure than its predecessor. The audit must verify that IMDSv2 is enforced.13
Bash
# Check metadata options for an instance
aws ec2 describe-instances --instance-ids <instance-id> --query "Reservations[*].Instances[*].MetadataOptions"

# Enforce IMDSv2 on an existing instance
aws ec2 modify-instance-metadata-options --instance-id <instance-id> --http-tokens required --http-endpoint enabled



Section 3: Auditing Data Protection and Encryption Controls

Protecting data is the ultimate goal of most security programs. This section of the audit focuses on verifying that data is protected both when it is stored (at rest) and when it is moving across the network (in transit). This involves auditing the configuration of storage services like S3, block storage like EBS, databases like RDS, and the use of encryption keys and TLS certificates.

3.1. Amazon S3: Securing Your Object Storage

Amazon S3 is a highly durable and scalable object storage service, but misconfigurations can easily lead to data exposure. Auditing S3 buckets for public access and proper encryption is a top priority.
Audit Objective: Ensure S3 buckets are not publicly exposed and that data is encrypted.
Step-by-Step Guide:
Check 1: Block Public Access: This feature is a powerful safety mechanism that should be enabled unless a bucket is intentionally public.13
Bash
# Check the Public Access Block configuration for a bucket
aws s3api get-public-access-block --bucket <bucket-name>

# Apply a restrictive Public Access Block configuration
aws s3api put-public-access-block --bucket <bucket-name> \
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"


Check 2: Default Encryption: Setting default encryption on a bucket ensures all new objects are automatically encrypted.52
Bash
# Check the default encryption configuration for a bucket
aws s3api get-bucket-encryption --bucket <bucket-name>

# Apply default SSE-S3 encryption to a bucket
aws s3api put-bucket-encryption --bucket <bucket-name> \
  --server-side-encryption-configuration '{"Rules":}'


Check 3: Bucket Policies: Review the bucket policy for any statements that grant public access (Principal of "*").
Bash
# Get the bucket policy for review
aws s3api get-bucket-policy --bucket <bucket-name> --query Policy --output text



3.2. Verifying Encryption at Rest for EBS and RDS

Data stored on virtual hard drives (EBS volumes) and in managed databases (RDS) must also be encrypted at rest.
Audit Objective: Confirm that block storage and databases are encrypted.
Step-by-Step Guide:
EBS Volumes:
Check all volumes in a region for their encryption status.
Bash
# Describe volumes and show their VolumeId and Encryption status
aws ec2 describe-volumes --query "Volumes[*].{ID:VolumeId,Encrypted:Encrypted}" --output table


To encrypt an unencrypted volume, you must create an encrypted copy via a snapshot.56
Bash
# 1. Create snapshot of the unencrypted volume
aws ec2 create-snapshot --volume-id <unencrypted-volume-id>
# 2. Copy the snapshot and encrypt it
aws ec2 copy-snapshot --source-snapshot-id <snapshot-id> --encrypted --kms-key-id <key-id>
# 3. Create a new volume from the encrypted snapshot
aws ec2 create-volume --snapshot-id <encrypted-snapshot-id> --availability-zone <az>
# 4. Stop instance, detach old volume, attach new volume, restart instance


To prevent this issue, enable encryption by default for the region.56
Bash
aws ec2 enable-ebs-encryption-by-default


RDS Instances:
Check the encryption status of an RDS instance.
Bash
# Check if storage is encrypted for a specific DB instance
aws rds describe-db-instances --db-instance-identifier <instance-name> --query "DBInstances[*].StorageEncrypted"


Similar to EBS, an existing unencrypted RDS instance must be encrypted by creating an encrypted snapshot and restoring a new instance from it.59
Bash
# 1. Create a snapshot of the unencrypted instance
aws rds create-db-snapshot --db-instance-identifier <instance-name> --db-snapshot-identifier <snapshot-name>
# 2. Copy the snapshot and encrypt it
aws rds copy-db-snapshot --source-db-snapshot-identifier <snapshot-arn> --target-db-snapshot-identifier <new-encrypted-snapshot> --kms-key-id <key-id>
# 3. Restore a new, encrypted instance from the encrypted snapshot
aws rds restore-db-instance-from-db-snapshot --db-instance-identifier <new-encrypted-instance-name> --db-snapshot-identifier <encrypted-snapshot-arn>



3.3. Managing Keys with AWS KMS

AWS Key Management Service (KMS) is a managed service that makes it easy to create and control the keys used for encryption.
Audit Objective: Ensure encryption keys are managed securely.
Step-by-Step Guide:
Check 1: Key Policies: Review the key policy to ensure it adheres to the principle of least privilege.62
Bash
# Get the key policy for a specific KMS key
aws kms get-key-policy --key-id <key-id> --policy-name default --query Policy --output text


Check 2: Key Rotation: Verify that automatic key rotation is enabled for customer-managed keys.62
Bash
# Check the rotation status for a KMS key
aws kms get-key-rotation-status --key-id <key-id>

# Enable automatic key rotation
aws kms enable-key-rotation --key-id <key-id>



3.4. Securing Data in Transit with TLS

Encrypting data at rest is only half the battle; data must also be protected as it travels over the network using Transport Layer Security (TLS).64
Audit Objective: Verify that all external communication is encrypted using TLS.
Step-by-Step Guide:
Check 1: Application Load Balancers (ALBs): ALBs should have an HTTPS listener configured with a valid TLS certificate from AWS Certificate Manager (ACM).55
Bash
# Describe listeners for a load balancer
aws elbv2 describe-listeners --load-balancer-arn <lb-arn>

Review the output to confirm a listener exists with Protocol: HTTPS on port 443 and has a valid certificate ARN. Any HTTP listener on port 80 should be configured to redirect to HTTPS.
Check 2: CloudFront Distributions: CloudFront distributions should be configured to enforce HTTPS between viewers and CloudFront.66
Bash
# Get the distribution configuration
aws cloudfront get-distribution-config --id <distribution-id>

Review the output JSON. Check that ViewerCertificate is configured with a valid ACM certificate ARN (which must be in the us-east-1 region) and that ViewerProtocolPolicy in the DefaultCacheBehavior is set to either redirect-to-https or https-only.66

Section 4: Auditing Detection, Logging, and Monitoring Capabilities

A robust security posture requires not only preventative controls but also detective controls. This section focuses on ensuring that comprehensive logging is enabled and that automated alerts are in place for critical security events.

4.1. AWS CloudTrail: Your Account's Audit Log

AWS CloudTrail provides a detailed record of actions taken in your AWS account, making it essential for security analysis and auditing.
Audit Objective: Ensure a complete and immutable record of all API activity is being captured.
Step-by-Step Guide:
Check 1 & 2: Multi-Region Trail with Log File Integrity: Verify that at least one trail is multi-region and has log file validation enabled. This ensures all API activity is captured and cannot be tampered with.69
Bash
# Describe all trails in the current region
aws cloudtrail describe-trails

In the output, look for a trail where IsMultiRegionTrail is true and LogFileValidationEnabled is true.
Check 3: Secure Log Storage: The S3 bucket for CloudTrail logs must be secure.
Bash
# Get the bucket policy for the CloudTrail bucket
aws s3api get-bucket-policy --bucket <cloudtrail-bucket-name>

# Check if server access logging is enabled for the bucket
aws s3api get-bucket-logging --bucket <cloudtrail-bucket-name>

The bucket policy should only grant access to the CloudTrail service principal and authorized security personnel. Server access logging for the bucket itself is a best practice.70

4.2. Amazon CloudWatch: Alarming on Suspicious Activity

CloudTrail logs must be monitored in near real-time to detect suspicious activity. This is achieved by creating Metric Filters and CloudWatch Alarms.71
Audit Objective: Ensure that proactive alerts are configured for high-risk security events.
Step-by-Step Guide:
The audit should verify the existence of critical security alarms. The following example shows the CLI commands to create an alarm for Root Account Usage.
Create a Metric Filter for Root Account Usage:
Bash
aws logs put-metric-filter \
  --log-group-name <cloudtrail_log_group_name> \
  --filter-name "RootAccountUsage" \
  --filter-pattern '{ $.userIdentity.type = "Root" && $.userIdentity.invokedBy NOT EXISTS && $.eventType!= "AwsServiceEvent" }' \
  --metric-transformations metricName=RootAccountUsageCount,metricNamespace=CloudTrailMetrics,metricValue=1


Create a CloudWatch Alarm for the Metric:
Bash
aws cloudwatch put-metric-alarm \
  --alarm-name "RootAccountUsageAlarm" \
  --alarm-description "Alarm when Root account is used" \
  --metric-name RootAccountUsageCount \
  --namespace CloudTrailMetrics \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --evaluation-periods 1 \
  --alarm-actions <sns_topic_arn>

Similar alarms should be created for other critical events, such as IAM policy changes, CloudTrail configuration changes, and unauthorized API calls.72

Table 3: High-Priority CloudTrail Events for CloudWatch Alarms

Event Name / Pattern
Security Significance
Recommended Action
ConsoleLogin with errorMessage: "Failed authentication"
Potential brute-force or password-spraying attack against the console.
Investigate the source IP address and user agent. Consider blocking the IP if activity is malicious.
DeleteTrail, StopLogging
An attacker is attempting to disable logging to cover their tracks. This is a high-confidence indicator of malicious activity.
Trigger a high-priority, immediate alert to the security incident response team.
PutGroupPolicy, AttachRolePolicy, CreatePolicyVersion
Potential privilege escalation. An attacker or insider may be attempting to grant themselves more permissions.
Review the change immediately. Cross-reference with authorized changes in a change management system. Revert if unauthorized.
AuthorizeSecurityGroupIngress (with CIDR 0.0.0.0/0)
A firewall rule is being opened to the entire internet. This could be for a management port like SSH or RDP, creating a major vulnerability.
Immediately investigate the security group, port, and the identity that made the change. Revert if unauthorized.
CreateAccessKey, CreateUser
A new credential or user is being created, which could be used as a backdoor for persistent access.
Review the new identity and its permissions. Ensure it was created as part of an authorized process.


4.3. Amazon GuardDuty: Intelligent Threat Detection

Amazon GuardDuty is a managed threat detection service that uses machine learning and anomaly detection to identify potential threats.
Audit Objective: Ensure a managed threat detection service is active.
Step-by-Step Guide:
Check 1: Enabled in All Regions: GuardDuty is a regional service and must be enabled in all active regions.75
Bash
# This shell command loops through all available EC2 regions and lists GuardDuty detectors
for region in $(aws ec2 describe-regions --query "Regions.RegionName" --output text); do
  echo "Checking region: $region"
  aws guardduty list-detectors --region $region
done

If a region returns an empty list, GuardDuty is not enabled there.
Action: Interpret Findings: Review any active findings for potential threats.76
Bash
# First, get the DetectorId for a region
DETECTOR_ID=$(aws guardduty list-detectors --query "DetectorIds" --output text)

# Then, list the active findings for that detector
aws guardduty list-findings --detector-id $DETECTOR_ID --finding-criteria '{"Criterion":{"service.archived":{"Eq":["false"]}}}'



Section 5: Auditing Serverless and Application Security

As organizations adopt serverless architectures, the security focus shifts from managing servers to securing the code and configuration of services like AWS Lambda.

5.1. AWS Lambda Function Security

While AWS manages the Lambda execution environment, the developer is responsible for the security of the function's code, its permissions, and how it handles data.
Audit Objective: Review Lambda functions for common security misconfigurations.
Step-by-Step Guide:
Check 1: Least Privilege Execution Role: The function's execution role must grant only the minimum permissions necessary.78
Bash
# Get the function's execution role ARN
ROLE_ARN=$(aws lambda get-function-configuration --function-name <function-name> --query 'Role' --output text)

# List policies attached to the role
aws iam list-attached-role-policies --role-name $(basename $ROLE_ARN)

# Get the details of a specific policy to review it
aws iam get-policy-version --policy-arn <policy_arn> --version-id <version_id>


Check 2: Secure Secret Management: Sensitive information should never be hard-coded or stored in plaintext environment variables. Use AWS Secrets Manager or SSM Parameter Store instead.81
Bash
# Check a function's environment variables
aws lambda get-function-configuration --function-name <function-name> --query 'Environment'

Review the output for plaintext secrets. Also, check the KMSKeyArn field to ensure environment variables are encrypted at rest.
Check 3: VPC Placement: A function should only be connected to a VPC if it needs to access private resources within that VPC.84
Bash
# Check a function's VPC configuration
aws lambda get-function-configuration --function-name <function-name> --query 'VpcConfig'

If the function does not need to access private resources, a non-empty VpcConfig may be an unnecessary configuration.

Conclusion: From Audit to Action - The Path to Continuous Security

Completing this security audit is a significant step toward improving the security posture of an AWS infrastructure. However, the audit itself is not the end goal; it is the beginning of a continuous process of improvement. The findings from this guide must be translated into actionable tasks, and the principles must be integrated into the development lifecycle.

A. Prioritizing Your Findings

After conducting the audit, there will likely be a list of findings with varying levels of severity. It is crucial to prioritize remediation efforts to address the most critical risks first. A simple framework for prioritization can be used:
Critical: These are issues that pose an immediate and significant threat to the environment, such as publicly accessible S3 buckets containing sensitive data, exposed management ports (SSH/RDP) open to the world, or active access keys for the root user. These must be remediated immediately.
High: These are serious vulnerabilities that could lead to a compromise, such as overly permissive IAM roles, unpatched EC2 instances with known critical vulnerabilities, or the absence of MFA on user accounts. These should be addressed within a short, defined timeframe (e.g., one week).
Medium: These are deviations from best practices that increase risk but are not immediately exploitable, such as missing log file validation on a CloudTrail trail, unencrypted EBS volumes for non-sensitive data, or access keys that have not been rotated in over 90 days. These should be scheduled for remediation.
Low: These are minor configuration improvements or informational findings that enhance security hygiene, such as adding descriptive tags to resources or cleaning up unused security groups.



