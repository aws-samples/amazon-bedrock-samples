"""
Property-based tests for Flask API endpoints.
"""
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import Mock, patch
import json

from backend.flask_app import create_app
from backend.services.config_manager import Config
from backend.models.thread import Thread, ThreadStatus


@pytest.fixture
def test_app():
    """Create a test Flask application."""
    app = create_app({'TESTING': True})
    return app


@pytest.fixture
def client(test_app):
    """Create a test client for the Flask application."""
    return test_app.test_client()


# ============================================================================
# Property Test for Chat POST Endpoint
# ============================================================================

@given(prompt=st.text(min_size=1, max_size=1000))
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_chat_post_returns_thread_id(client, prompt):
    """
    Feature: ar-chatbot, Property 42: Chat POST returns thread ID
    
    For any chat message sent via POST endpoint, the system should return
    the thread identifier.
    
    Validates: Requirements 11.2
    """
    # Mock the config manager to have a valid configuration
    with patch('backend.flask_app.config_manager') as mock_config_manager:
        mock_config = Config(
            model_id="test-model",
            policy_arn="test-policy-arn",
            guardrail_id="test-guardrail-id",
            guardrail_version="DRAFT"
        )
        mock_config_manager.get_current_config.return_value = mock_config
        
        # Mock thread manager to avoid actual thread creation
        with patch('backend.flask_app.service_container.thread_manager') as mock_thread_manager:
            # Create a mock thread
            mock_thread = Mock(spec=Thread)
            mock_thread.thread_id = "test-thread-id"
            mock_thread_manager.create_thread.return_value = mock_thread
            
            # Mock the background processing to avoid actual AWS calls
            with patch('backend.flask_app.threading.Thread'):
                # Send POST request
                response = client.post(
                    '/api/chat',
                    data=json.dumps({'prompt': prompt}),
                    content_type='application/json'
                )
                
                # Verify response
                assert response.status_code == 200
                data = json.loads(response.data)
                
                # Property: Response must contain thread_id
                assert 'thread_id' in data
                assert isinstance(data['thread_id'], str)
                assert len(data['thread_id']) > 0


# ============================================================================
# Property Test for JSON Response Format
# ============================================================================

@given(
    endpoint=st.sampled_from([
        '/api/config/models',
        '/api/config/policies',
        '/api/threads'
    ])
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_all_endpoints_return_json(client, endpoint):
    """
    Feature: ar-chatbot, Property 45: All endpoints return JSON
    
    For any API endpoint response, it should be in JSON format.
    
    Validates: Requirements 11.5
    """
    # Mock the config manager for endpoints that need it
    with patch('backend.flask_app.config_manager') as mock_config_manager:
        mock_config_manager.get_available_models.return_value = ["model1", "model2"]
        mock_config_manager.get_available_policies.return_value = []
        
        # Mock thread manager for thread endpoints
        with patch('backend.flask_app.service_container.thread_manager') as mock_thread_manager:
            mock_thread_manager.list_threads.return_value = []
            
            # Send GET request
            response = client.get(endpoint)
            
            # Property: Response must be valid JSON
            assert response.content_type == 'application/json'
            
            # Verify we can parse the response as JSON
            try:
                data = json.loads(response.data)
                assert isinstance(data, dict)
            except json.JSONDecodeError:
                pytest.fail(f"Response from {endpoint} is not valid JSON")


@given(
    model_id=st.text(min_size=1, max_size=100),
    policy_arn=st.text(min_size=1, max_size=200)
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_config_post_returns_json(client, model_id, policy_arn):
    """
    Feature: ar-chatbot, Property 45: All endpoints return JSON (POST variant)
    
    For any configuration update via POST endpoint, the response should be in JSON format.
    
    Validates: Requirements 11.5
    """
    with patch('backend.flask_app.config_manager') as mock_config_manager:
        mock_config = Config(
            model_id=model_id,
            policy_arn=policy_arn,
            guardrail_id="test-guardrail",
            guardrail_version="DRAFT"
        )
        mock_config_manager.update_config.return_value = mock_config
        mock_config_manager.ensure_guardrail.return_value = ("test-guardrail", "DRAFT")
        
        response = client.post(
            '/api/config',
            data=json.dumps({
                'model_id': model_id,
                'policy_arn': policy_arn
            }),
            content_type='application/json'
        )
        
        # Property: Response must be valid JSON
        assert response.content_type == 'application/json'
        
        try:
            data = json.loads(response.data)
            assert isinstance(data, dict)
        except json.JSONDecodeError:
            pytest.fail("Response from /api/config POST is not valid JSON")


@given(thread_id=st.text(min_size=1, max_size=100))
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_thread_get_returns_json(client, thread_id):
    """
    Feature: ar-chatbot, Property 45: All endpoints return JSON (thread GET variant)
    
    For any thread retrieval request, the response should be in JSON format.
    
    Validates: Requirements 11.5
    """
    with patch('backend.flask_app.service_container.thread_manager') as mock_thread_manager:
        # Test both found and not found cases
        mock_thread_manager.get_thread.return_value = None
        
        response = client.get(f'/api/thread/{thread_id}')
        
        # Property: Response must be valid JSON (even for errors)
        assert response.content_type == 'application/json'
        
        try:
            data = json.loads(response.data)
            assert isinstance(data, dict)
        except json.JSONDecodeError:
            pytest.fail(f"Response from /api/thread/{thread_id} is not valid JSON")


# ============================================================================
# Unit Tests for Answer Submission Endpoint
# ============================================================================

def test_submit_answers_success(client):
    """
    Test successful answer submission.
    
    Validates: Requirements 4.4, 4.5
    """
    from backend.models.thread import QuestionAnswerExchange, Iteration
    
    thread_id = "test-thread-123"
    questions = ["Question 1?", "Question 2?"]
    answers = ["Answer 1", "Answer 2"]
    
    # Create mock thread with AWAITING_USER_INPUT status
    mock_thread = Mock(spec=Thread)
    mock_thread.thread_id = thread_id
    mock_thread.status = ThreadStatus.AWAITING_USER_INPUT
    mock_thread.user_prompt = "Test prompt"
    
    # Create mock iteration with questions
    mock_qa_exchange = QuestionAnswerExchange(
        questions=questions,
        answers=None,
        skipped=False
    )
    mock_iteration = Mock(spec=Iteration)
    mock_iteration.qa_exchange = mock_qa_exchange
    mock_thread.iterations = [mock_iteration]
    
    with patch('backend.flask_app.config_manager') as mock_config_manager:
        mock_config = Config(
            model_id="test-model",
            policy_arn="test-policy-arn",
            guardrail_id="test-guardrail-id",
            guardrail_version="DRAFT"
        )
        mock_config_manager.get_current_config.return_value = mock_config
        
        with patch('backend.flask_app.service_container.thread_manager') as mock_thread_manager:
            mock_thread_manager.get_thread.return_value = mock_thread
            
            with patch('backend.flask_app.threading.Thread'):
                response = client.post(
                    f'/api/thread/{thread_id}/answer',
                    data=json.dumps({
                        'answers': answers,
                        'skipped': False
                    }),
                    content_type='application/json'
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['status'] == 'success'
                assert data['thread_id'] == thread_id


def test_submit_answers_skip(client):
    """
    Test skip functionality.
    
    Validates: Requirements 4.5, 12.2
    """
    from backend.models.thread import QuestionAnswerExchange, Iteration
    
    thread_id = "test-thread-456"
    questions = ["Question 1?", "Question 2?"]
    
    # Create mock thread with AWAITING_USER_INPUT status
    mock_thread = Mock(spec=Thread)
    mock_thread.thread_id = thread_id
    mock_thread.status = ThreadStatus.AWAITING_USER_INPUT
    mock_thread.user_prompt = "Test prompt"
    
    # Create mock iteration with questions
    mock_qa_exchange = QuestionAnswerExchange(
        questions=questions,
        answers=None,
        skipped=False
    )
    mock_iteration = Mock(spec=Iteration)
    mock_iteration.qa_exchange = mock_qa_exchange
    mock_thread.iterations = [mock_iteration]
    
    with patch('backend.flask_app.config_manager') as mock_config_manager:
        mock_config = Config(
            model_id="test-model",
            policy_arn="test-policy-arn",
            guardrail_id="test-guardrail-id",
            guardrail_version="DRAFT"
        )
        mock_config_manager.get_current_config.return_value = mock_config
        
        with patch('backend.flask_app.service_container.thread_manager') as mock_thread_manager:
            mock_thread_manager.get_thread.return_value = mock_thread
            
            with patch('backend.flask_app.threading.Thread'):
                response = client.post(
                    f'/api/thread/{thread_id}/answer',
                    data=json.dumps({
                        'answers': [],
                        'skipped': True
                    }),
                    content_type='application/json'
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['status'] == 'success'
                assert data['thread_id'] == thread_id


def test_submit_answers_thread_not_found(client):
    """
    Test error handling when thread is not found.
    
    Validates: Requirements 4.4
    """
    thread_id = "nonexistent-thread"
    
    with patch('backend.flask_app.config_manager') as mock_config_manager:
        mock_config = Config(
            model_id="test-model",
            policy_arn="test-policy-arn",
            guardrail_id="test-guardrail-id",
            guardrail_version="DRAFT"
        )
        mock_config_manager.get_current_config.return_value = mock_config
        
        with patch('backend.flask_app.service_container.thread_manager') as mock_thread_manager:
            mock_thread_manager.get_thread.return_value = None
            
            response = client.post(
                f'/api/thread/{thread_id}/answer',
                data=json.dumps({
                    'answers': ["Answer 1"],
                    'skipped': False
                }),
                content_type='application/json'
            )
            
            assert response.status_code == 404
            data = json.loads(response.data)
            assert 'error' in data
            assert data['error']['code'] == 'NOT_FOUND'


def test_submit_answers_invalid_state(client):
    """
    Test error handling when thread is not awaiting input.
    
    Validates: Requirements 4.4
    """
    thread_id = "test-thread-789"
    
    # Create mock thread with PROCESSING status (not AWAITING_USER_INPUT)
    mock_thread = Mock(spec=Thread)
    mock_thread.thread_id = thread_id
    mock_thread.status = ThreadStatus.PROCESSING
    
    with patch('backend.flask_app.config_manager') as mock_config_manager:
        mock_config = Config(
            model_id="test-model",
            policy_arn="test-policy-arn",
            guardrail_id="test-guardrail-id",
            guardrail_version="DRAFT"
        )
        mock_config_manager.get_current_config.return_value = mock_config
        
        with patch('backend.flask_app.service_container.thread_manager') as mock_thread_manager:
            mock_thread_manager.get_thread.return_value = mock_thread
            
            response = client.post(
                f'/api/thread/{thread_id}/answer',
                data=json.dumps({
                    'answers': ["Answer 1"],
                    'skipped': False
                }),
                content_type='application/json'
            )
            
            assert response.status_code == 409
            data = json.loads(response.data)
            assert 'error' in data
            assert data['error']['code'] == 'INVALID_STATE'


def test_submit_answers_wrong_count(client):
    """
    Test error handling when answer count doesn't match question count.
    
    Validates: Requirements 9.5
    """
    from backend.models.thread import QuestionAnswerExchange, Iteration
    
    thread_id = "test-thread-999"
    questions = ["Question 1?", "Question 2?", "Question 3?"]
    answers = ["Answer 1"]  # Only 1 answer for 3 questions
    
    # Create mock thread with AWAITING_USER_INPUT status
    mock_thread = Mock(spec=Thread)
    mock_thread.thread_id = thread_id
    mock_thread.status = ThreadStatus.AWAITING_USER_INPUT
    mock_thread.user_prompt = "Test prompt"
    
    # Create mock iteration with questions
    mock_qa_exchange = QuestionAnswerExchange(
        questions=questions,
        answers=None,
        skipped=False
    )
    mock_iteration = Mock(spec=Iteration)
    mock_iteration.qa_exchange = mock_qa_exchange
    mock_thread.iterations = [mock_iteration]
    
    with patch('backend.flask_app.config_manager') as mock_config_manager:
        mock_config = Config(
            model_id="test-model",
            policy_arn="test-policy-arn",
            guardrail_id="test-guardrail-id",
            guardrail_version="DRAFT"
        )
        mock_config_manager.get_current_config.return_value = mock_config
        
        with patch('backend.flask_app.service_container.thread_manager') as mock_thread_manager:
            mock_thread_manager.get_thread.return_value = mock_thread
            
            response = client.post(
                f'/api/thread/{thread_id}/answer',
                data=json.dumps({
                    'answers': answers,
                    'skipped': False
                }),
                content_type='application/json'
            )
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert 'error' in data
            assert data['error']['code'] == 'INVALID_ANSWERS'
            assert data['error']['details']['expected'] == 3
            assert data['error']['details']['received'] == 1


def test_submit_answers_invalid_format(client):
    """
    Test error handling when request format is invalid.
    
    Validates: Requirements 4.4
    """
    thread_id = "test-thread-invalid"
    
    with patch('backend.flask_app.config_manager') as mock_config_manager:
        mock_config = Config(
            model_id="test-model",
            policy_arn="test-policy-arn",
            guardrail_id="test-guardrail-id",
            guardrail_version="DRAFT"
        )
        mock_config_manager.get_current_config.return_value = mock_config
        
        # Test with answers as string instead of array
        response = client.post(
            f'/api/thread/{thread_id}/answer',
            data=json.dumps({
                'answers': "not an array",
                'skipped': False
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error']['code'] == 'BAD_REQUEST'
