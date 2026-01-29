# Automated Reasoning checks rewriting chatbot
This application shows how you can use Automated Reasoning checks in Amazon Bedrock Guardrails alongside your LLM to iterate on and improve generated responses. This application also saves a mathematically verifiable audit log of the validity claim of each response.

## Prerequisites and dependencies
The first step is to configure the chatbot to use an Automated Reasoning policy from your AWS account. If you have not created an automated reasoning policy before, you can use the sample policy from [the AWS console](https://console.aws.amazon.com/bedrock/home#/automated-reasoning/policies).

To run the application, you will need the latest version of Python and Node JS. You will also need to [configure AWS credentials](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html).

## Installing dependencies and starting the application

```bash
# Install dependencies - we recommend using a virtual environment:
$ pip install -r backend/requirements.txt

# Install frontend dependencies
$ cd frontend && npm install

# Build the frontend to static files
$ cd frontend && npm run build

# Run the Flask application
$ python -m backend.flask_app 2>&1
```

The application should now be accessible *[on localhost port 8080](http://localhost:8080)*.

## Testing

### Backend Tests
```bash
$ pytest
```

### Frontend Tests
```bash
$ cd frontend && npm test -- --watchAll=false --passWithNoTests
```

## Project Structure

The backend APIs in charge of communicating with LLMs through Bedrock, calling Bedrock Guardrails through the `ApplyGuardrail` API, and iterating on Automated Reasoning checks feedback to ask for answer rewriting are written in Python as a Flask application. The frontend is written in React and built to static HTML files that Flask can host. 


```
.
├── backend/              # Python Flask backend
│   ├── app/             # Flask application
│   ├── models/          # Data models
│   ├── services/        # Business logic services
│   └── requirements.txt # Python dependencies
├── frontend/            # React TypeScript frontend
│   ├── api/            # API client code
│   ├── components/     # React components
│   ├── src/            # Source files
│   ├── public/         # Static assets
│   └── package.json    # Node dependencies
└── prompts/            # Rewriting prompt templates
```

An in-depth overview of the design is available in [`DESIGN.md`](DESIGN.md).

> [!NOTE]
> To easily support any Automated Reasoning policy without requiring document uploads, this project includes the policy content in the generation prompts to the LLMs. In a production deployment, you would use RAG content or feed the LLM the original, natural language document instead of the Automated Reasoning policy source code.

