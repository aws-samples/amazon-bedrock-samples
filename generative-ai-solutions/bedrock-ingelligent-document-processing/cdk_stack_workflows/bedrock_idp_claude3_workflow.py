from constructs import Construct
import os
import re
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_stepfunctions as sfn
import aws_cdk.aws_stepfunctions_tasks as tasks
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_lambda_event_sources as eventsources
import aws_cdk.aws_iam as iam
import aws_cdk.custom_resources as cr
import amazon_textract_idp_cdk_constructs as tcdk
import cdk_nag as nag
from aws_cdk import CfnOutput, RemovalPolicy, Stack, Duration, Aws, Fn, Aspects
from aws_solutions_constructs.aws_lambda_opensearch import LambdaToOpenSearch
from aws_cdk import aws_opensearchservice as opensearch
import aws_cdk.aws_ssm as ssm


class BedrockIDPClaude3Workflow(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(
            scope,
            construct_id,
            description="Information extraction using GenAI with Bedrock Claude3",
            **kwargs,
        )

        script_location = os.path.dirname(__file__)
        
        workflow_name = "BedrockIDPClaude3"
        current_region = Stack.of(self).region
        account_id = Stack.of(self).account
        stack_name = Stack.of(self).stack_name
        
        '''
        We will first create the S3 bucket that will handle uploads, trigger the Step Functions state machine, and store files at different stages of the IDP workflow
        '''
        
        s3_upload_prefix = "uploads"
        s3_converted_pdf_prefix = "converted-pdf-output"
        s3_split_document_prefix = "split-document-output"
        s3_csv_output_prefix = "forms-tables-output"
        s3_textract_output_prefix = "textract-output"
        s3_txt_output_prefix = "textract-text-output"
        s3_bedrock_classification_output_prefix = "bedrock-classification-output"
        s3_bedrock_extraction_output_prefix = "bedrock-extraction-output"

        #######################################
        # BEWARE! This is a demo/POC setup
        # Remove the auto_delete_objects=True and removal_policy=RemovalPolicy.DESTROY
        # when the documents should remain after deleting the CloudFormation stack!
        #######################################

        # Create the bucket for the documents and outputs
        document_bucket = s3.Bucket(
            self,
            f"{workflow_name}Bucket",
            removal_policy=RemovalPolicy.DESTROY,
            enforce_ssl=True,
            auto_delete_objects=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )
        s3_output_bucket = document_bucket.bucket_name
        
        # Get the event source that will be used later to trigger the executions
        s3_event_source = eventsources.S3EventSource(
            document_bucket,
            events=[s3.EventType.OBJECT_CREATED],
            filters=[s3.NotificationKeyFilter(prefix=s3_upload_prefix)],
        )
        
        # Create Systems Manager parameters on initial deployment
        classification_parameter = ssm.CfnParameter(self, "ClassificationParameter",
            type="String",
            name="/BedrockIDP/CLASSIFICATION",
            value="""Give the document one of the following classifications: {INVOICE: a invoice, OTHER: something else} return only a JSON in the following format {CLASSIFCIATION: result} with CLASSIFICATION remaining the same and result being one of the listed classifications. Put the values in double quotes and do not output any text other than the JSON."""
        )
        
        invoice_parameter = ssm.CfnParameter(self, "InvoiceParameter",
            type="String",
            name="/BedrockIDP/INVOICE",
            value="""Given the document, as a information extraction process, export the following values: TOTAL CHARGES, INVOICE NUMBER. Format responses in JSON format, for example
            <example>
            {
            ‘INVOICE NUMBER’: 'value'
            }
            </example>
            where the value is extracted from the document. 
            Do not include any commas in the numeric values. Use double quotes for all values. Do not include any text besides the JSON output"""
        )
        
        '''
        We will now define the Task states that will be executing the document preparation and IDP tasks in our state machine
        '''

        # Decider checks if the document is of valid format. Returns mime type and number of pages in the document
        decider_task = tcdk.TextractPOCDecider(
            self,
            "GetFileType",
            textract_decider_max_retries=10000,
            s3_input_bucket=document_bucket.bucket_name,
            s3_input_prefix=s3_upload_prefix,
        )
        
        # Converts single page PDFs to JPEGs for Claude 3 image capabilities
        pdf_converter_function: lambda_.IFunction = lambda_.DockerImageFunction(  # type: ignore
            self,
            "PDFConverterFunction",
            code=lambda_.DockerImageCode.from_image_asset(
                os.path.join(script_location, "../lambda/pdf_converter")
            ),
            memory_size=128,
            timeout=Duration.seconds(900),
            architecture=lambda_.Architecture.X86_64,
            environment={
                "LOG_LEVEL": "DEBUG",
                "S3_OUTPUT_PREFIX": s3_converted_pdf_prefix,
                "S3_OUTPUT_BUCKET": document_bucket.bucket_name
            },
        )

        # Grant the PDF converter function access to the S3 bucket
        document_bucket.grant_read_write(pdf_converter_function)

        # PDF converter task
        pdf_converter_task = tasks.LambdaInvoke(
            self,
            "PDFConverter",
            lambda_function=pdf_converter_function,
            output_path="$.Payload",
        )
        
        # The splitter takes a document and splits into the max_number_of_pages_per_document
        # This is particulary useful when working with documents that exceed the Textract limits or when the workflow requires per page processing
        document_splitter_function: lambda_.IFunction = lambda_.DockerImageFunction(
            self,
            "DocSplitterFunction",
            code=lambda_.DockerImageCode.from_image_asset(
                os.path.join(script_location, "../lambda/document_splitter")
            ),
            memory_size=128,
            timeout=Duration.seconds(900),
            architecture=lambda_.Architecture.X86_64,
            environment={
                "LOG_LEVEL": "DEBUG",
                "S3_OUTPUT_PREFIX": s3_split_document_prefix,
                "S3_OUTPUT_BUCKET": document_bucket.bucket_name,
                "max_number_of_pages_per_doc": "1"
            },
        )

        # Grant the document splitter function access to the S3 bucket
        document_bucket.grant_read_write(document_splitter_function)

        # Document splitter task
        document_splitter_task = tasks.LambdaInvoke(
            self,
            "DocSplitter",
            lambda_function=document_splitter_function,
            output_path="$.Payload",
        )

        # Calls the Textract synchronous API
        textract_sync_task = tcdk.TextractGenericSyncSfnTask(
            self,
            "TextractSync",
            s3_output_bucket=document_bucket.bucket_name,
            s3_output_prefix=s3_textract_output_prefix,
            integration_pattern=sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            lambda_log_level="DEBUG",
            timeout=Duration.hours(24),
            input=sfn.TaskInput.from_object({
                "Token":
                sfn.JsonPath.task_token,
                "ExecutionId":
                sfn.JsonPath.string_at('$$.Execution.Id'),
                "Payload":
                sfn.JsonPath.entire_payload,
            }),
            result_path="$.textract_result")
            
        # Generates CSV data based on Textract output from TextractSync.
        # Texctract features are defined in map state initialization (default is FORMS and TABLES)
        generate_csv = tcdk.TextractGenerateCSV(
            self,
            "GenerateFormsTables",
            csv_s3_output_bucket=document_bucket.bucket_name,
            csv_s3_output_prefix=s3_csv_output_prefix,
            s3_input_bucket=document_bucket.bucket_name,
            s3_input_prefix=s3_textract_output_prefix,
            lambda_log_level="DEBUG",
            output_type='CSV',
            integration_pattern=sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            input=sfn.TaskInput.from_object({
                "Token":
                sfn.JsonPath.task_token,
                "ExecutionId":
                sfn.JsonPath.string_at('$$.Execution.Id'),
                "Payload":
                sfn.JsonPath.entire_payload,
            }),
            result_path="$.csv_output_location")

        # Generate raw text based on Textract output from TextractSync
        generate_text = tcdk.TextractGenerateCSV(
            self,
            "FormatTextractOutput",
            csv_s3_output_bucket=document_bucket.bucket_name,
            csv_s3_output_prefix=s3_txt_output_prefix,
            output_type="LINEARIZED",
            lambda_log_level="DEBUG",
            integration_pattern=sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            input=sfn.TaskInput.from_object(
                {
                    "Token": sfn.JsonPath.task_token,
                    "ExecutionId": sfn.JsonPath.string_at("$$.Execution.Id"),
                    "Payload": sfn.JsonPath.entire_payload,
                }
            ),
            result_path="$.txt_output_location",
        )

        # Calls Bedrock to classify documents based on /BedrockIDP/CLASSIFICATION parameter prompt in Systems Manager Parameter Store
        bedrock_doc_classification_function: lambda_.IFunction = lambda_.DockerImageFunction(  # type: ignore
            self,
            "BedrockDocClassificationFunction",
            code=lambda_.DockerImageCode.from_image_asset(
                os.path.join(script_location, "../lambda/bedrock")
            ),
            memory_size=128,
            timeout=Duration.seconds(900),
            architecture=lambda_.Architecture.X86_64,
            environment={
                "LOG_LEVEL": "DEBUG",
                "FIXED_KEY": "CLASSIFICATION",
                "S3_OUTPUT_PREFIX": s3_bedrock_classification_output_prefix,
                "S3_OUTPUT_BUCKET": document_bucket.bucket_name
            },
        )

        # Grant document classification function permissions to Systems Manager and Bedrock
        document_bucket.grant_read_write(bedrock_doc_classification_function)
        bedrock_doc_classification_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel", "ssm:GetParameter"],
                resources=["*"],
            )
        )

        # Bedrock document classification task
        bedrock_doc_classification_task = tasks.LambdaInvoke(
            self,
            "BedrockDocClassification",
            lambda_function=bedrock_doc_classification_function,
            output_path="$.Payload",
        )

        bedrock_doc_classification_task.add_retry(
            max_attempts=10,
            errors=[
                "Lambda.TooManyRequestsException",
                "ModelNotReadyException",
                "ModelTimeoutException",
                "ServiceQuotaExceededException",
                "ThrottlingException",
            ],
        )

        # Calls Bedrock to extract information off the document
        # Gets prompt from Systems Manager Parameter Store based on the classification output
        bedrock_doc_extraction_function: lambda_.IFunction = lambda_.DockerImageFunction(  # type: ignore
            self,
            "BedrockDocExtractionFunction",
            code=lambda_.DockerImageCode.from_image_asset(
                os.path.join(script_location, "../lambda/bedrock")
            ),
            memory_size=512,
            timeout=Duration.seconds(900),
            architecture=lambda_.Architecture.X86_64,
            environment={
                "LOG_LEVEL": "DEBUG",
                "S3_OUTPUT_PREFIX": s3_bedrock_extraction_output_prefix,
                "S3_OUTPUT_BUCKET": document_bucket.bucket_name
            },
        )

        # Grant document extraction function permissions to Systems Manager and Bedrock
        document_bucket.grant_read_write(bedrock_doc_extraction_function)
        bedrock_doc_extraction_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel", "ssm:GetParameter"],
                resources=["*"],
            )
        )

        # Bedrock document extraction task
        bedrock_doc_extraction_task = tasks.LambdaInvoke(
            self,
            "BedrockDocExtraction",
            lambda_function=bedrock_doc_extraction_function,
            output_path="$.Payload",
        )

        bedrock_doc_extraction_task.add_retry(
            max_attempts=10,
            errors=[
                "Lambda.TooManyRequestsException",
                "ModelNotReadyException",
                "ModelTimeoutException",
                "ServiceQuotaExceededException",
                "ThrottlingException",
            ],
        )
        
        # Calls Bedrock to classify images based on /BedrockIDP/CLASSIFICATION parameter prompt in Systems Manager Parameter Store
        bedrock_image_classification_function: lambda_.IFunction = lambda_.DockerImageFunction(  # type: ignore
            self,
            "BedrockImageClassificationFunction",
            code=lambda_.DockerImageCode.from_image_asset(
                os.path.join(script_location, "../lambda/bedrock_image")
            ),
            memory_size=512,
            timeout=Duration.seconds(900),
            architecture=lambda_.Architecture.X86_64,
            environment={
                "LOG_LEVEL": "DEBUG",
                "FIXED_KEY": "CLASSIFICATION",
                "S3_OUTPUT_PREFIX": s3_bedrock_classification_output_prefix,
                "S3_OUTPUT_BUCKET": document_bucket.bucket_name
            },
        )

        # Grant image classification function permissions to Systems Manager and Bedrock
        document_bucket.grant_read_write(bedrock_image_classification_function)
        bedrock_image_classification_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel", "ssm:GetParameter"],
                resources=["*"],
            )
        )

        # Bedrock image classification task
        bedrock_image_classification_task = tasks.LambdaInvoke(
            self,
            "BedrockImageClassification",
            lambda_function=bedrock_image_classification_function,
            output_path="$.Payload",
        )

        bedrock_image_classification_task.add_retry(
            max_attempts=10,
            errors=[
                "Lambda.TooManyRequestsException",
                "ModelNotReadyException",
                "ModelTimeoutException",
                "ServiceQuotaExceededException",
                "ThrottlingException",
            ],
        )
        
        # Calls Bedrock to extract information off the image
        # Gets prompt from Systems Manager Parameter Store based on the classification output
        bedrock_image_extraction_function: lambda_.IFunction = lambda_.DockerImageFunction(  # type: ignore
            self,
            "BedrockImageExtractionFunction",
            code=lambda_.DockerImageCode.from_image_asset(
                os.path.join(script_location, "../lambda/bedrock_image")
            ),
            memory_size=512,
            timeout=Duration.seconds(900),
            architecture=lambda_.Architecture.X86_64,
            environment={
                "LOG_LEVEL": "DEBUG",
                "S3_OUTPUT_PREFIX": s3_bedrock_extraction_output_prefix,
                "S3_OUTPUT_BUCKET": document_bucket.bucket_name
            },
        )

        # Grant image extraction function permissions to Systems Manager and Bedrock
        document_bucket.grant_read_write(bedrock_image_extraction_function)
        bedrock_image_extraction_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel", "ssm:GetParameter"],
                resources=["*"],
            )
        )

        # Bedrock image extraction task
        bedrock_image_extraction_task = tasks.LambdaInvoke(
            self,
            "BedrockImageExtraction",
            lambda_function=bedrock_image_extraction_function,
            output_path="$.Payload",
        )

        bedrock_image_extraction_task.add_retry(
            max_attempts=10,
            errors=[
                "Lambda.TooManyRequestsException",
                "ModelNotReadyException",
                "ModelTimeoutException",
                "ServiceQuotaExceededException",
                "ThrottlingException",
            ],
        )
        
        '''
        Now that our Task states are defined, we will construct our state machine
        We will start with the chain for "complex" documents (2+ page PDFs)
        
        For this chain we will also create a Choice state (RouteDocType) to route documents based on classification, 
        a Parallel state for running both Bedrock and Textract (FORMS & TABLES) extraction, 
        and a Map state (Map State) to iterate over each page in the document
        
        The states are added to the chain from bottom (executed last) to top (executed first)
        '''
        
        # Determine if the document classification is supported, and route document pages based on their classification
        doc_type_choice = (
            sfn.Choice(self, "RouteDocType")
            .when(
                sfn.Condition.string_equals("$.classification.documentType", "INVOICE"),
                bedrock_doc_extraction_task
            )
            .otherwise(sfn.Pass(self, "No supported document classification"))
        )
        
        # Chain for Bedrock document extraction
        bedrock_document_extraction_chain = (
            sfn.Chain.start(generate_text)
            .next(bedrock_doc_classification_task)
            .next(doc_type_choice)
        )
        
        # Chain for Textract extraction (FORMS & TABLES)
        form_table_chain = (
            sfn.Chain.start(generate_csv)
        )
        
        # Call the Bedrock extraction chain and the Textract extraction chain in parallel
        parallel_tasks = (
            sfn.Parallel(self, "parallel")
            .branch(form_table_chain)
            .branch(bedrock_document_extraction_chain)
        )

        # Call the parallel state after the Textract synchronous call is finished
        textract_sync_task.next(parallel_tasks)

        # Define Map state to iterate over each page in the document
        map = sfn.Map(
            self,
            "Map State",
            items_path=sfn.JsonPath.string_at("$.pages"),
            parameters={
                "manifest": {
                    "s3Path": sfn.JsonPath.string_at(
                        "States.Format('s3://{}/{}/{}', \
                        $.documentSplitterS3OutputBucket, \
                        $.documentSplitterS3OutputPath, \
                        $$.Map.Item.Value)"
                    ),
                    "textractFeatures": [
                      "FORMS",
                      "TABLES",
                      "LAYOUT"
                    ]
                },
                "mime": sfn.JsonPath.string_at("$.mime"),
                "originFileURI": sfn.JsonPath.string_at("$.originFileURI"),
            },
        )

        map.iterator(textract_sync_task)
        
        # Define start of document chain
        doc_chain = (
            sfn.Chain.start(document_splitter_task).next(map)    
        )
        
        '''
        We will construct the image chain (1 page PDFs, JPEGs, PNGs)
        
        This chain will also have a Choice state (RouteImageType) to route images based on classification
        
        The states are added to the chain from bottom (executed last) to top (executed first)
        '''
        
        # Determine if the image classification is supported, and route images based on their classification
        image_type_router = (
            sfn.Choice(self, "RouteImageType")
            .when(
                sfn.Condition.string_equals("$.classification.imageType", "INVOICE"),
                bedrock_image_extraction_task
            )
            .otherwise(sfn.Pass(self, "No supported image classification"))
        )
        
        # Define start of image chain
        image_chain = (
            sfn.Chain.start(bedrock_image_classification_task).next(image_type_router)  
        )
        
        '''
        Finally, we will construct the top (first steps) of the state machine
        
        This determines the mime type of the uploaded file, converts 1 page PDFs to a JPEG,
        and routes 2+ page PDFs to the document chain and 1 page PDFs, JPEGs, and PNGs to the image chain
        '''
        
        # Determine if file is an image file that is supported by Claude 3 vision capabilities
        is_supported_image_type = sfn.Condition.or_(
            sfn.Condition.string_equals("$.mime", "image/jpeg"),
            sfn.Condition.string_equals("$.mime", "image/png")
        )
        
        # Route documents to document chain, and images to image chain
        doc_image_router = (
            sfn.Choice(self, "RouteDocsAndImages")
            .when(is_supported_image_type, image_chain)
            .otherwise(doc_chain)
        )
        
        # Define PDF converter chain
        pdf_converter_chain = (
            sfn.Chain.start(pdf_converter_task).next(doc_image_router)  
        )
        
        # Determines if the file is a 1 page PDF
        is_simple_pdf = sfn.Condition.and_(
            sfn.Condition.string_equals("$.mime", "application/pdf"),
            sfn.Condition.number_equals("$.numberOfPages", 1)
        )
        
        # Routes 1 page PDFs to the PDF converter chain (all other files will skip the PDF converter state)
        simple_pdf_checker = (
            sfn.Choice(self, "SimplePDFChecker")
            .when(is_simple_pdf, pdf_converter_chain)
            .otherwise(doc_image_router)
        )

        # Define start of state machine
        workflow_chain = (
            sfn.Chain.start(decider_task).next(simple_pdf_checker)
        )

        # GENERIC
        state_machine = sfn.StateMachine(self, workflow_name, definition=workflow_chain)

        '''
        With our state machine fully defined, we will trigger our state machine when files are put in the uploads folder of the S3 bucket
    
        This also handles all the complexity of making sure the limits or bottlenecks are not exceeded
        '''
        
        sf_executions_start_throttle = tcdk.SFExecutionsStartThrottle(
            self,
            "ExecutionThrottle",
            state_machine_arn=state_machine.state_machine_arn,
            s3_input_bucket=document_bucket.bucket_name,
            s3_input_prefix=s3_upload_prefix,
            executions_concurrency_threshold=550,
            sqs_batch=10,
            lambda_log_level="INFO",
            event_source=[s3_event_source],
        )
        queue_url_urlencoded = ""
        if sf_executions_start_throttle.document_queue:
            # urlencode the SQS Queue link, otherwise the deep linking does not work properly.
            queue_url_urlencoded = Fn.join(
                "%2F",
                Fn.split(
                    "/",
                    Fn.join(
                        "%3A",
                        Fn.split(
                            ":", sf_executions_start_throttle.document_queue.queue_url
                        ),
                    ),
                ),
            )
        
        '''
        Define stack outputs
        '''
        
        CfnOutput(
            self,
            "DocumentUploadLocation",
            value=f"s3://{document_bucket.bucket_name}/{s3_upload_prefix}/",
            export_name=f"{Aws.STACK_NAME}-DocumentUploadLocation",
        )
        CfnOutput(
            self,
            "StepFunctionFlowLink",
            value=f"https://{current_region}.console.aws.amazon.com/states/home?region={current_region}#/statemachines/view/{state_machine.state_machine_arn}",  # noqa: E501
        ),
        CfnOutput(
            self,
            "DocumentQueueLink",
            value=f"https://{current_region}.console.aws.amazon.com/sqs/v2/home?region={current_region}#/queues/{queue_url_urlencoded}",  # noqa: E501
        )