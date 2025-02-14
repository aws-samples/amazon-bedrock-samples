from flask import Flask, request, jsonify, render_template, Response, stream_with_context
from flask_cors import CORS
import json
import uuid
import base64
import boto3
from datetime import datetime
from inlineagent import create_bedrock_client, prepare_request_params, invoke_bedrock_agent, save_interaction, get_available_tools
from config import AGENT_PERSONAS

# uncomment to see detailed application logs and agent traces 
# import logging
# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Initialize Bedrock client
bedrock_client = create_bedrock_client()

def decode_token(auth_header):
    try:
        token = auth_header.split(' ')[1]
        decoded_bytes = base64.b64decode(token)
        token_data = json.loads(decoded_bytes)
        return token_data
    except Exception as e:
        print(f"Error decoding token: {str(e)}")
        return None

def process_event_stream(query, session_id, session_state, selected_persona, selected_model):
    try:
        # Prepare request parameters with access level and selected tools
        request_params = prepare_request_params(
            input_text=query,
            persona_id=selected_persona,
            foundation_model=selected_model,
            session_id=session_id,
            enable_trace=True,
            access_level=session_state['sessionAttributes'].get('access_level', 'basic'),
            selected_tools=session_state['sessionAttributes'].get('selected_tools', [])
        )
        
        # Invoke the agent
        response = bedrock_client.invoke_inline_agent(**request_params)
        
        # First, yield session information
        yield json.dumps({
            'type': 'session',
            'sessionId': session_id
        }) + '\n'

        # Process the completion stream
        for event in response.get('completion', []):
            try:
                if isinstance(event, dict):
                    if 'chunk' in event:
                        chunk_content = event['chunk']['bytes'].decode('utf-8')
                        yield json.dumps({
                            'type': 'response',
                            'content': chunk_content
                        }) + '\n'
                    elif 'trace' in event:
                        yield json.dumps({
                            'type': 'trace',
                            'trace': event['trace']
                        }) + '\n'
            except Exception as e:
                print(f"Error processing event: {str(e)}")
                yield json.dumps({
                    'type': 'error',
                    'message': f'Error processing event: {str(e)}'
                }) + '\n'

    except Exception as e:
        print(f"Error in process_event_stream: {str(e)}")
        yield json.dumps({
            'type': 'error',
            'message': f'Error: {str(e)}'
        }) + '\n'

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

@app.route('/personas', methods=['GET'])
def get_personas():
    return jsonify({
        'personas': [
            {
                'id': persona_id,
                'name': persona_data['name']
            }
            for persona_id, persona_data in AGENT_PERSONAS.items()
        ]
    })

@app.route('/tools', methods=['GET'])
def get_tools():
    """Endpoint to get available tools based on user's access level"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'error': 'No authorization header provided'}), 401

    user_data = decode_token(auth_header)
    if not user_data:
        return jsonify({'error': 'Invalid token'}), 401

    access_level = user_data.get('access', 'basic')
    available_tools = get_available_tools()
    
    # Filter tools based on access level
    allowed_tools = {
        tool_id: {
            'name': tool['config']['actionGroupName'],
            'description': tool['config'].get('description', '')
        }
        for tool_id, tool in available_tools.items()
        if access_level.lower() in tool['access_level']
    }
    
    return jsonify(allowed_tools)

@app.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        session_id = request.headers.get('Session-ID', '')
        request_body = request.get_json()
        user_message = request_body.get('message')
        selected_persona = request_body.get('persona', 'peachy')
        selected_model = request_body.get('model')
        selected_tools = request_body.get('tools', [])
        session_id = request_body.get('session')

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'No authorization header provided'}), 401

        user_data = decode_token(auth_header)
        if not user_data:
            return jsonify({'error': 'Invalid token'}), 401

        if not session_id:
            session_id = str(uuid.uuid4())

        # Create session state with all necessary information
        session_state = {
            'sessionAttributes': {
                'employee_id': user_data.get('employeeId', ''),
                'employeeName': user_data.get('name', ''),
                'access_level': user_data.get('access', 'basic'),
                'selected_persona': selected_persona,
                'selected_tools': selected_tools,
                'selected_model': selected_model
            }
        }
                
        try:
            # Create streaming response
            response = Response(
                stream_with_context(process_event_stream(
                    query=user_message,
                    session_id=session_id,
                    session_state=session_state,
                    selected_persona=selected_persona,
                    selected_model=selected_model
                )),
                mimetype='text/event-stream'
            )
            response.headers['Session-ID'] = session_id
            return response

        except Exception as agent_error:
            print(f"Agent error: {str(agent_error)}")
            return jsonify({
                'error': 'Agent error',
                'message': str(agent_error)
            }), 500

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8008, debug=True)