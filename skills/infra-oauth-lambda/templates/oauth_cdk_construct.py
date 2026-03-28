"""
OAuth Infrastructure CDK Construct Template.

This construct creates the infrastructure for a self-service OAuth credential
collection flow:
- HTTP API Gateway with routes for OAuth flow
- Lambda function to handle OAuth callbacks
- IAM role with Secrets Manager read/write access

CUSTOMIZATION POINTS (marked with # CUSTOMIZE):
- Resource naming convention
- Lambda runtime and memory
- Additional environment variables

Usage in your stack:
    oauth = OAuthConstruct(
        self,
        "OAuth",
        environment="dev",
        secret=gmail_secret,
        resource_prefix="bb-gtm-dev-comm",
    )
"""

from aws_cdk import (
    CfnOutput,
    Duration,
)
from aws_cdk import (
    aws_apigatewayv2 as apigwv2,
)
from aws_cdk import (
    aws_apigatewayv2_integrations as apigwv2_integrations,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_lambda as _lambda,
)
from aws_cdk import (
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct


class OAuthConstruct(Construct):
    """CDK Construct for OAuth credential collection infrastructure."""

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        environment: str,
        secret: secretsmanager.ISecret,
        resource_prefix: str,
        lambda_code_path: str,
    ) -> None:
        """
        Create OAuth infrastructure.

        Args:
            scope: CDK scope
            id: Construct ID
            environment: Environment name (dev, prod)
            secret: Secrets Manager secret to store credentials
            resource_prefix: Prefix for resource names (e.g., "bb-gtm-dev-comm")
            lambda_code_path: Path to Lambda code directory
        """
        super().__init__(scope, id)

        self.environment = environment
        self.resource_prefix = resource_prefix

        # CUSTOMIZE: Helper for consistent naming
        def get_resource_name(resource: str) -> str:
            return f"{resource_prefix}-{resource}"

        # =====================================================================
        # IAM Role - Needs WRITE access to Secrets Manager
        # =====================================================================
        self.lambda_role = iam.Role(
            self,
            "OAuthLambdaRole",
            role_name=get_resource_name("oauth-lambda-role"),
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

        # Grant read AND write access to credentials secret
        secret.grant_read(self.lambda_role)
        secret.grant_write(self.lambda_role)

        # =====================================================================
        # HTTP API Gateway (not REST API - simpler and cheaper)
        # =====================================================================
        self.api = apigwv2.HttpApi(
            self,
            "OAuthApi",
            api_name=get_resource_name("oauth-api"),
            description=f"OAuth callback API for {environment} credential collection",
            # CUSTOMIZE: CORS not needed for OAuth redirects (browser navigations).
            # Add cors_preflight only if your OAuth pages make XHR requests.
        )

        # Build the callback URL
        oauth_callback_url = f"{self.api.url}oauth/callback"

        # =====================================================================
        # Lambda Function
        # =====================================================================
        # CUSTOMIZE: Runtime and memory settings
        self.lambda_function = _lambda.Function(
            self,
            "OAuthCallbackFunction",
            function_name=get_resource_name("oauth-callback"),
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(lambda_code_path),
            runtime=_lambda.Runtime.PYTHON_3_12,  # CUSTOMIZE: latest
            role=self.lambda_role,
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "ENVIRONMENT": environment,
                "CREDENTIALS_SECRET": secret.secret_name,
                # These placeholders are updated by deploy script
                "OAUTH_CLIENT_ID": "PLACEHOLDER_CLIENT_ID",
                "OAUTH_CLIENT_SECRET": "PLACEHOLDER_CLIENT_SECRET",
                "OAUTH_REDIRECT_URI": oauth_callback_url,
            },
        )

        # =====================================================================
        # API Gateway Integration and Routes
        # =====================================================================
        oauth_integration = apigwv2_integrations.HttpLambdaIntegration(
            "OAuthIntegration",
            self.lambda_function,
        )

        # Add routes for OAuth flow
        self.api.add_routes(
            path="/oauth",
            methods=[apigwv2.HttpMethod.GET],
            integration=oauth_integration,
        )
        self.api.add_routes(
            path="/oauth/start",
            methods=[apigwv2.HttpMethod.GET],
            integration=oauth_integration,
        )
        self.api.add_routes(
            path="/oauth/callback",
            methods=[apigwv2.HttpMethod.GET],
            integration=oauth_integration,
        )

        # =====================================================================
        # Outputs
        # =====================================================================
        CfnOutput(
            self,
            "OAuthApiUrl",
            value=self.api.url or "",
            description="Base URL for OAuth API Gateway",
            export_name=get_resource_name("oauth-api-url"),
        )

        CfnOutput(
            self,
            "OAuthStartUrl",
            value=f"{self.api.url}oauth/start",
            description="URL to start OAuth flow (visit in browser)",
            export_name=get_resource_name("oauth-start-url"),
        )

        CfnOutput(
            self,
            "OAuthCallbackFunctionArn",
            value=self.lambda_function.function_arn,
            description="ARN of the OAuth callback Lambda function",
            export_name=get_resource_name("oauth-callback-arn"),
        )


# =============================================================================
# Example Usage in Stack
# =============================================================================
"""
from oauth_construct import OAuthConstruct

class MyStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Create secret for credentials
        credentials_secret = secretsmanager.Secret(
            self,
            "CredentialsSecret",
            secret_name="my-app-credentials",
        )

        # Create OAuth infrastructure
        oauth = OAuthConstruct(
            self,
            "OAuth",
            environment="dev",
            secret=credentials_secret,
            resource_prefix="my-app-dev",
            lambda_code_path="../lambda_functions/oauth_callback",
        )

        # Access outputs
        self.oauth_api = oauth.api
        self.oauth_lambda = oauth.lambda_function
"""
