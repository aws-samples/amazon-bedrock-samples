"""
Flask API application for the AR Chatbot.

This module provides REST API endpoints for:
- Configuration management (models, policies)
- Chat operations (submit prompts, retrieve threads)
- Static file serving for the React frontend
"""
import logging
import os
import threading
import boto3
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from typing import Dict, Any

from backend.services.config_manager import ConfigManager
from backend.services.service_container import ServiceContainer
from backend.services.thread_processor import process_thread, resume_thread_with_answers
from backend.models.thread import IterationType, ClarificationIterationData
from backend.exceptions import (
    APIException, BadRequestError, NotFoundError, ConflictError,
    ConfigError, ServiceUnavailableError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize configuration and service container
config_manager = ConfigManager()
service_container = ServiceContainer(config_manager)


def register_error_handlers(app: Flask) -> None:
    """
    Register error handlers for common HTTP errors.
    
    Args:
        app: Flask application instance
    """
    
    @app.errorhandler(APIException)
    def handle_api_exception(error: APIException):
        """Handle custom API exceptions."""
        logger.warning(f"API exception: {error.code} - {error.message}")
        return jsonify({
            "error": {
                "code": error.code,
                "message": error.message,
                "details": error.details
            }
        }), error.status_code
    
    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 Bad Request errors."""
        logger.warning(f"Bad request: {error}")
        return jsonify({
            "error": {
                "code": "BAD_REQUEST",
                "message": "The request was invalid or malformed",
                "details": str(error)
            }
        }), 400
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 Not Found errors."""
        logger.warning(f"Resource not found: {error}")
        return jsonify({
            "error": {
                "code": "NOT_FOUND",
                "message": "The requested resource was not found",
                "details": str(error)
            }
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server Error."""
        logger.error(f"Internal server error: {error}", exc_info=True)
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal server error occurred",
                "details": "Please try again later"
            }
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle uncaught exceptions."""
        logger.error(f"Unhandled exception: {error}", exc_info=True)
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": str(error)
            }
        }), 500


def handle_timeout_resume(thread_id: str, answers: list, skipped: bool) -> None:
    """
    Handle resuming a thread after timeout.
    
    This function is called by the timeout handler to resume threads that
    have exceeded the timeout period.
    
    Args:
        thread_id: The thread identifier
        answers: Empty list (not used for timeout)
        skipped: Always True for timeout
    """
    logger.info(f"Handling timeout resume for thread {thread_id}")
    
    # Get current configuration
    current_config = config_manager.get_current_config()
    if not current_config:
        logger.error(f"Cannot resume thread {thread_id} - no configuration available")
        return
    
    # Spawn daemon thread since this is called from timeout handler, not a request context
    def resume_in_background():
        try:
            # Get services from container
            llm_service = service_container.get_llm_service()
            validation_service = service_container.get_validation_service()
            policy_service = service_container.get_policy_service()
            
            # Resume the thread with skipped=True
            resume_thread_with_answers(
                thread_id,
                answers,
                skipped,
                service_container.thread_manager,
                llm_service,
                validation_service,
                service_container.audit_logger,
                policy_service,
                config_manager
            )
            logger.info(f"Thread {thread_id} - Successfully resumed after timeout")
        except Exception as e:
            logger.error(f"Error resuming thread {thread_id} after timeout: {e}", exc_info=True)
            # Update thread with error status if possible
            try:
                from backend.models.thread import ThreadStatus
                service_container.thread_manager.update_thread_status(
                    thread_id,
                    ThreadStatus.ERROR,
                    final_response=f"An error occurred while resuming after timeout: {str(e)}"
                )
            except:
                pass
    
    background_thread = threading.Thread(target=resume_in_background, daemon=True)
    background_thread.start()


def register_routes(app: Flask) -> None:
    """
    Register all API routes.
    
    Args:
        app: Flask application instance
    """
    
    # ========================================================================
    # Configuration Endpoints
    # ========================================================================
    
    @app.route('/api/config/models', methods=['GET'])
    def get_models():
        """Get list of available Bedrock models."""
        try:
            model_ids = config_manager.get_available_models()
            # Format models with id and name for frontend
            models = [{"id": model_id, "name": model_id} for model_id in model_ids]
            return jsonify({"models": models}), 200
        except Exception as e:
            logger.error(f"Failed to retrieve models: {e}")
            raise ConfigError("Failed to retrieve available models", details=str(e))
    
    @app.route('/api/config/policies', methods=['GET'])
    def get_policies():
        """Get list of available AR policies."""
        try:
            policies = config_manager.get_available_policies()
            return jsonify({
                "policies": [
                    {
                        "arn": policy.arn,
                        "name": policy.name,
                        "description": policy.description
                    }
                    for policy in policies
                ]
            }), 200
        except Exception as e:
            logger.error(f"Failed to retrieve policies: {e}")
            raise ConfigError("Failed to retrieve available policies", details=str(e))
    
    @app.route('/api/config', methods=['GET'])
    def get_config():
        """Get current application configuration."""
        try:
            config = config_manager.get_current_config()
            
            if config is None:
                # Return default/empty config
                return jsonify({
                    "model_id": "",
                    "policy_arn": "",
                    "guardrail_id": None,
                    "guardrail_version": None,
                    "max_iterations": 5
                }), 200
            
            return jsonify({
                "model_id": config.model_id,
                "policy_arn": config.policy_arn,
                "guardrail_id": config.guardrail_id,
                "guardrail_version": config.guardrail_version,
                "max_iterations": config.max_iterations
            }), 200
            
        except Exception as e:
            logger.error(f"Failed to retrieve configuration: {e}")
            raise ConfigError("Failed to retrieve configuration", details=str(e))
    
    @app.route('/api/config', methods=['POST'])
    def update_config():
        """Update application configuration."""
        data = request.get_json()
        
        if not data:
            raise BadRequestError(
                "Request body is required",
                details="Expected JSON with model_id and policy_arn"
            )
        
        model_id = data.get('model_id')
        policy_arn = data.get('policy_arn')
        max_iterations = data.get('max_iterations', 5)  # Default to 5 if not provided
        
        if not model_id or not policy_arn:
            raise BadRequestError(
                "Missing required fields",
                details="Both model_id and policy_arn are required"
            )
        
        # Validate max_iterations
        if not isinstance(max_iterations, int) or max_iterations <= 0:
            raise BadRequestError(
                "Invalid max_iterations value",
                details="max_iterations must be a positive integer"
            )
        
        try:
            # Update configuration
            # Check if we should use mock policy for testing
            use_mock_policy = os.environ.get('USE_MOCK_POLICY', 'false').lower() == 'true'
            config = config_manager.update_config(model_id, policy_arn, use_mock_policy=use_mock_policy, max_iterations=max_iterations)
            
            # Reset services in container to pick up new configuration
            service_container.reset_services()
            logger.info("Service container reset with new configuration")
            
            # Ensure guardrail exists for the policy
            try:
                guardrail_id, guardrail_version = config_manager.ensure_guardrail(policy_arn)
                config.guardrail_id = guardrail_id
                config.guardrail_version = guardrail_version
            except Exception as e:
                logger.error(f"Failed to ensure guardrail: {e}")
                raise APIException(
                    "Failed to create or update guardrail",
                    code="GUARDRAIL_ERROR",
                    status_code=500,
                    details=str(e)
                )
            
            return jsonify({
                "config": {
                    "model_id": config.model_id,
                    "policy_arn": config.policy_arn,
                    "guardrail_id": config.guardrail_id,
                    "guardrail_version": config.guardrail_version,
                    "max_iterations": config.max_iterations
                }
            }), 200
            
        except APIException:
            raise  # Re-raise API exceptions
        except Exception as e:
            logger.error(f"Failed to update configuration: {e}")
            raise ConfigError("Failed to update configuration", details=str(e))
    
    # ========================================================================
    # Test Case Endpoints
    # ========================================================================
    
    @app.route('/api/policy/<path:policy_arn>/test-cases', methods=['GET'])
    def get_test_cases(policy_arn: str):
        """
        Get test cases for a specific policy.
        
        Args:
            policy_arn: The ARN of the policy (URL path parameter)
            
        Returns:
            JSON response with test cases or error
        """
        # Validate policy ARN is provided
        if not policy_arn:
            logger.warning("Test case request received with empty policy ARN")
            raise BadRequestError("Missing required parameter", details="policy_arn is required")
        
        logger.info(f"Fetching test cases for policy: {policy_arn}")
        
        try:
            # Fetch test cases using TestCaseService from container
            test_cases = service_container.test_case_service.list_test_cases(policy_arn)
            
            logger.info(f"Successfully retrieved {len(test_cases)} test cases for policy {policy_arn}")
            
            return jsonify({
                "test_cases": test_cases
            }), 200
            
        except ValueError as ve:
            # Handle validation errors (invalid ARN format, etc.)
            logger.warning(f"Validation error for policy {policy_arn}: {ve}")
            raise BadRequestError("Invalid policy ARN", details=str(ve))
            
        except Exception as e:
            # Handle all other errors (AWS API errors, network errors, etc.)
            error_message = str(e)
            logger.error(f"Failed to fetch test cases for policy {policy_arn}: {error_message}")
            
            # Determine appropriate exception based on error message
            if "credentials" in error_message.lower():
                raise APIException(
                    "Failed to fetch test cases",
                    code="AUTHENTICATION_ERROR",
                    status_code=500,
                    details=error_message
                )
            elif "unavailable" in error_message.lower() or "connection" in error_message.lower():
                raise ServiceUnavailableError("Failed to fetch test cases", details=error_message)
            else:
                raise APIException(
                    "Failed to fetch test cases",
                    code="INTERNAL_ERROR",
                    status_code=500,
                    details=error_message
                )
    
    # ========================================================================
    # Chat Endpoints
    # ========================================================================
    
    @app.route('/api/chat', methods=['POST'])
    def create_chat():
        """Submit a new chat prompt and create a thread."""
        data = request.get_json()
        
        if not data:
            raise BadRequestError(
                "Request body is required",
                details="Expected JSON with prompt field"
            )
        
        prompt = data.get('prompt')
        
        if not prompt:
            raise BadRequestError(
                "Missing required field",
                details="prompt field is required"
            )
        
        # Get current configuration
        current_config = config_manager.get_current_config()
        if not current_config:
            raise ConfigError(
                "Application not configured",
                details="Please configure the application before submitting prompts"
            )
        
        try:
            # Create thread
            thread = service_container.thread_manager.create_thread(prompt, current_config.model_id)
            thread_id = thread.thread_id
            
            # Spawn a daemon thread to allow immediate response to client.
            # Flask request threads are non-daemon and would block shutdown if long-running.
            def process_in_background():
                try:
                    # Get services from container
                    llm_service = service_container.get_llm_service()
                    validation_service = service_container.get_validation_service()
                    policy_service = service_container.get_policy_service()
                    
                    if policy_service:
                        logger.info("Using PolicyService for thread processing")
                    else:
                        logger.info("No PolicyService available - policy operations will be disabled")
                    
                    # Process the thread
                    process_thread(
                        thread_id,
                        service_container.thread_manager,
                        llm_service,
                        validation_service,
                        service_container.audit_logger,
                        policy_service,
                        config_manager
                    )
                except Exception as e:
                    logger.error(f"Error in background processing for thread {thread_id}: {e}", exc_info=True)
            
            background_thread = threading.Thread(target=process_in_background, daemon=True)
            background_thread.start()
            
            logger.info(f"Created thread {thread_id} and started processing")
            
            return jsonify({"thread_id": thread_id}), 200
            
        except Exception as e:
            logger.error(f"Failed to create chat thread: {e}")
            raise APIException(
                "Failed to create chat thread",
                code="CHAT_ERROR",
                status_code=500,
                details=str(e)
            )
    
    @app.route('/api/thread/<thread_id>', methods=['GET'])
    def get_thread(thread_id: str):
        """Get thread status and data."""
        try:
            thread = service_container.thread_manager.get_thread(thread_id)
            
            if thread is None:
                raise NotFoundError(
                    "Thread not found",
                    details=f"No thread found with ID: {thread_id}"
                )
            
            return jsonify({"thread": thread.to_dict()}), 200
            
        except NotFoundError:
            raise  # Re-raise NotFoundError
        except Exception as e:
            logger.error(f"Failed to retrieve thread {thread_id}: {e}")
            raise APIException(
                "Failed to retrieve thread",
                code="THREAD_ERROR",
                status_code=500,
                details=str(e)
            )
    
    @app.route('/api/threads', methods=['GET'])
    def list_threads():
        """List all threads."""
        try:
            threads = service_container.thread_manager.list_threads()
            return jsonify({"threads": [thread.to_dict() for thread in threads]}), 200
        except Exception as e:
            logger.error(f"Failed to list threads: {e}")
            raise APIException(
                "Failed to list threads",
                code="THREAD_ERROR",
                status_code=500,
                details=str(e)
            )
    
    @app.route('/api/thread/<thread_id>/answer', methods=['POST'])
    def submit_answers(thread_id: str):
        """
        Submit answers to follow-up questions.
        
        Request body:
        {
            "answers": ["answer1", "answer2", ...],
            "skipped": false
        }
        
        Returns:
        {
            "status": "success",
            "thread_id": "uuid"
        }
        """
        data = request.get_json()
        
        if not data:
            raise BadRequestError(
                "Request body is required",
                details="Expected JSON with answers array and skipped boolean"
            )
        
        # Extract answers and skipped flag
        answers = data.get('answers', [])
        skipped = data.get('skipped', False)
        
        # Validate request body format
        if not isinstance(answers, list):
            raise BadRequestError(
                "Invalid request format",
                details="answers must be an array"
            )
        
        if not isinstance(skipped, bool):
            raise BadRequestError(
                "Invalid request format",
                details="skipped must be a boolean"
            )
        
        # Get current configuration
        current_config = config_manager.get_current_config()
        if not current_config:
            raise ConfigError(
                "Application not configured",
                details="Please configure the application before submitting answers"
            )
        
        # Spawn daemon thread to return immediately while processing continues
        def resume_in_background():
            try:
                # Get services from container
                llm_service = service_container.get_llm_service()
                validation_service = service_container.get_validation_service()
                policy_service = service_container.get_policy_service()
                
                # Resume the thread with answers
                resume_thread_with_answers(
                    thread_id,
                    answers,
                    skipped,
                    service_container.thread_manager,
                    llm_service,
                    validation_service,
                    service_container.audit_logger,
                    policy_service,
                    config_manager
                )
            except ValueError as ve:
                # Handle validation errors (thread not found, wrong state, etc.)
                logger.error(f"Validation error resuming thread {thread_id}: {ve}")
                # Update thread with error status if possible
                try:
                    from backend.models.thread import ThreadStatus
                    service_container.thread_manager.update_thread_status(
                        thread_id,
                        ThreadStatus.ERROR,
                        final_response=str(ve)
                    )
                except:
                    pass
            except Exception as e:
                logger.error(f"Error in background processing for thread {thread_id}: {e}", exc_info=True)
                # Update thread with error status if possible
                try:
                    from backend.models.thread import ThreadStatus
                    service_container.thread_manager.update_thread_status(
                        thread_id,
                        ThreadStatus.ERROR,
                        final_response=f"An error occurred while processing your answers: {str(e)}"
                    )
                except:
                    pass
        
        # Validate thread exists and is in correct state before starting background thread
        thread = service_container.thread_manager.get_thread(thread_id)
        if thread is None:
            raise NotFoundError(
                "Thread not found",
                details=f"No thread found with ID: {thread_id}"
            )
        
        from backend.models.thread import ThreadStatus
        if thread.status != ThreadStatus.AWAITING_USER_INPUT:
            raise ConflictError(
                "Thread is not awaiting user input",
                details=f"Thread status is {thread.status.value}, expected AWAITING_USER_INPUT"
            )
        
        # Validate answer count matches question count (if not skipped)
        if not skipped:
            last_iteration = thread.iterations[-1] if thread.iterations else None
            if last_iteration:
                question_count = None
                
                # Handle new TypedIteration format
                if hasattr(last_iteration, 'iteration_type') and last_iteration.iteration_type == IterationType.USER_CLARIFICATION:
                    clar_data = last_iteration.type_specific_data
                    if isinstance(clar_data, ClarificationIterationData):
                        question_count = len(clar_data.qa_exchange.questions)
                # Handle old Iteration format (for backward compatibility during migration)
                elif hasattr(last_iteration, 'qa_exchange') and last_iteration.qa_exchange:
                    question_count = len(last_iteration.qa_exchange.questions)
                
                if question_count is not None:
                    answer_count = len(answers)
                    if answer_count != question_count:
                        raise APIException(
                            "Answer count does not match question count",
                            code="INVALID_ANSWERS",
                            status_code=400,
                            details={
                                "expected": question_count,
                                "received": answer_count,
                                "thread_id": thread_id
                            }
                        )
        
        try:
            background_thread = threading.Thread(target=resume_in_background, daemon=True)
            background_thread.start()
            
            logger.info(f"Resuming thread {thread_id} with user answers (skipped: {skipped})")
            
            return jsonify({
                "status": "success",
                "thread_id": thread_id
            }), 200
            
        except Exception as e:
            logger.error(f"Failed to submit answers for thread {thread_id}: {e}")
            raise APIException(
                "Failed to submit answers",
                code="ANSWER_SUBMISSION_ERROR",
                status_code=500,
                details=str(e)
            )
    
    # ========================================================================
    # Static File Serving
    # ========================================================================
    
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        """Serve React frontend static files."""
        if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        else:
            # Serve index.html for client-side routing
            return send_from_directory(app.static_folder, 'index.html')


def create_app(config: Dict[str, Any] = None) -> Flask:
    """
    Create and configure the Flask application.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__, static_folder='../frontend/build', static_url_path='')
    
    # Apply configuration if provided
    if config:
        app.config.update(config)
    
    # Configure CORS for frontend communication
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://localhost:5000"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Register error handlers and routes
    register_error_handlers(app)
    register_routes(app)
    
    # Initialize and start timeout handler
    service_container.timeout_handler.set_resume_callback(handle_timeout_resume)
    service_container.timeout_handler.start()
    logger.info("Timeout handler initialized and started")
    
    logger.info("Flask application created and configured")
    return app


def check_aws_credentials():
    try:
        session = boto3.Session()
        credentials = session.get_credentials()
        if credentials:
            try:
                sts_client = session.client("sts")
                identity = sts_client.get_caller_identity()
                return True
            except (ClientError, NoCredentialsError) as e:
                print(f"AWS credentials found, but validation failed (network or permissions error): {e}")
                return False
        else:
            print("No AWS credentials found in the environment.")
            return False

    except NoCredentialsError:
        print("No AWS credentials found in the environment.")
        return False


if not check_aws_credentials():
    print("Configure AWS credentials to run the application: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html")
    exit(1)

# Create the application instance
app = create_app()


if __name__ == '__main__':
    # Run the development server
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
