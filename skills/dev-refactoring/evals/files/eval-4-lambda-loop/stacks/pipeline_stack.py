"""CDK stack for the order processing pipeline.

This stack wires up the Lambdas, SNS topic, SQS queues, DynamoDB tables,
and the Step Function. The wiring creates several circular event paths
that can cause infinite loops in production.
"""

from aws_cdk import Duration, Stack
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_lambda_event_sources as event_sources
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as subs
from aws_cdk import aws_sqs as sqs
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as tasks
from constructs import Construct


class OrderPipelineStack(Stack):
    """Order processing pipeline with Step Functions orchestration.

    Architecture:
    - SQS -> Validator Lambda -> Step Function -> Enricher -> Payment
    - SNS topic used for ALL events (no filtering)
    - Restock queue triggered by enricher on out-of-stock
    - DynamoDB streams on inventory table trigger enricher

    Known issues (that need refactoring):
    1. Single SNS topic for all event types with no subscription filters
    2. Enricher triggered by both Step Function AND SNS (double processing)
    3. Restock -> inventory update -> DynamoDB stream -> enricher loop
    4. Payment failure -> SNS -> validator re-processes as new order
    5. Step Function retry + SNS retry = duplicate processing
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # ---- Tables ----
        orders_table = dynamodb.Table(
            self,
            "OrdersTable",
            partition_key=dynamodb.Attribute(name="order_id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        )

        inventory_table = dynamodb.Table(
            self,
            "InventoryTable",
            partition_key=dynamodb.Attribute(name="sku", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
        )

        # ---- SNS: Single topic for ALL events (problem #1) ----
        order_events_topic = sns.Topic(self, "OrderEventsTopic", display_name="Order Events")

        # ---- SQS Queues ----
        # Incoming orders queue
        order_queue = sqs.Queue(
            self,
            "OrderQueue",
            visibility_timeout=Duration.seconds(300),
        )

        # Restock queue (part of the loop)
        restock_queue = sqs.Queue(
            self,
            "RestockQueue",
            visibility_timeout=Duration.seconds(60),
        )

        # Queue for SNS -> Enricher (no message filtering!)
        enricher_queue = sqs.Queue(
            self,
            "EnricherQueue",
            visibility_timeout=Duration.seconds(300),
        )

        # ---- Lambdas ----
        common_env = {
            "ORDERS_TABLE": orders_table.table_name,
            "INVENTORY_TABLE": inventory_table.table_name,
            "ORDER_EVENTS_TOPIC": order_events_topic.topic_arn,
            "RESTOCK_QUEUE_URL": restock_queue.queue_url,
        }

        validator_fn = lambda_.Function(
            self,
            "ValidatorFn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="order_validator.handler",
            code=lambda_.Code.from_asset("src"),
            environment={
                **common_env,
                "PIPELINE_STATE_MACHINE": "placeholder",
            },
            timeout=Duration.seconds(30),
        )

        enricher_fn = lambda_.Function(
            self,
            "EnricherFn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="order_enricher.handler",
            code=lambda_.Code.from_asset("src"),
            environment=common_env,
            timeout=Duration.seconds(60),
        )

        payment_fn = lambda_.Function(
            self,
            "PaymentFn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="payment_processor.handler",
            code=lambda_.Code.from_asset("src"),
            environment=common_env,
            timeout=Duration.seconds(30),
        )

        restock_fn = lambda_.Function(
            self,
            "RestockFn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="restock_handler.handler",
            code=lambda_.Code.from_asset("src"),
            environment=common_env,
            timeout=Duration.seconds(30),
        )

        # ---- Step Function ----
        enrich_step = tasks.LambdaInvoke(
            self,
            "EnrichOrder",
            lambda_function=enricher_fn,
            output_path="$.Payload",
            # PROBLEM #2: Step Function invokes enricher directly,
            # but enricher is ALSO triggered via SNS subscription
            # (see below), causing double processing
        )

        payment_step = tasks.LambdaInvoke(
            self,
            "ProcessPayment",
            lambda_function=payment_fn,
            output_path="$.Payload",
        )

        # PROBLEM #5: Step Function retries on failure, but the
        # payment lambda ALSO publishes to SNS on failure, which
        # triggers the validator to restart the whole pipeline
        payment_step.add_retry(
            errors=["States.ALL"],
            interval=Duration.seconds(5),
            max_attempts=3,
            backoff_rate=2.0,
        )

        # On payment failure after retries, go back to enrichment
        # (maybe prices changed) — this is a LOOP within the
        # Step Function itself
        payment_retry_choice = sfn.Choice(self, "PaymentSucceeded?")
        re_enrich = tasks.LambdaInvoke(
            self,
            "ReEnrichOrder",
            lambda_function=enricher_fn,
            output_path="$.Payload",
        )

        definition = enrich_step.next(payment_step).next(
            payment_retry_choice.when(
                sfn.Condition.string_equals("$.payment_status", "failed"),
                re_enrich.next(payment_step),
            ).otherwise(sfn.Succeed(self, "OrderComplete"))
        )

        state_machine = sfn.StateMachine(
            self,
            "OrderPipeline",
            definition_body=sfn.DefinitionBody.from_chainable(definition),
            timeout=Duration.minutes(30),
        )

        # Update validator with actual state machine ARN
        validator_fn.add_environment(
            "PIPELINE_STATE_MACHINE",
            state_machine.state_machine_arn,
        )

        # ---- Event Wiring (where the loops happen) ----

        # Validator triggered by incoming order queue
        validator_fn.add_event_source(event_sources.SqsEventSource(order_queue))

        # PROBLEM #1: SNS topic subscribes enricher queue with
        # NO filter — enricher gets ALL events including its own
        # "enrichment_complete" events
        order_events_topic.add_subscription(subs.SqsSubscription(enricher_queue))
        enricher_fn.add_event_source(event_sources.SqsEventSource(enricher_queue))

        # Restock handler triggered by restock queue
        restock_fn.add_event_source(event_sources.SqsEventSource(restock_queue))

        # PROBLEM #3: Inventory DynamoDB stream triggers enricher
        # directly — after restock updates inventory, enricher
        # re-runs, may find still insufficient stock, sends another
        # restock request...
        enricher_fn.add_event_source(
            event_sources.DynamoEventSource(
                inventory_table,
                starting_position=lambda_.StartingPosition.LATEST,
                batch_size=10,
            )
        )

        # ---- Permissions ----
        orders_table.grant_read_write_data(validator_fn)
        orders_table.grant_read_write_data(enricher_fn)
        orders_table.grant_read_write_data(payment_fn)
        inventory_table.grant_read_write_data(enricher_fn)
        inventory_table.grant_read_write_data(restock_fn)
        order_events_topic.grant_publish(validator_fn)
        order_events_topic.grant_publish(enricher_fn)
        order_events_topic.grant_publish(payment_fn)
        order_events_topic.grant_publish(restock_fn)
        restock_queue.grant_send_messages(enricher_fn)
        state_machine.grant_start_execution(validator_fn)
