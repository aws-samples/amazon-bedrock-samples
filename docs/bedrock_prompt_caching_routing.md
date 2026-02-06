# Amazon Bedrock Prompt Caching and Routing Workshop

[Open in GitHub](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/BedrockPromptCachingRoutingDemo)

**Tags:** bedrock, prompt-caching, prompt-routing, claude, optimization, cost-reduction, performance

<h2>Overview</h2>

This workshop demonstrates Amazon Bedrock's prompt caching and routing capabilities using the latest Claude models. You'll learn how to reduce latency and costs through intelligent prompt caching and how to route requests to optimal models based on your specific needs.

**Key Learning Outcomes:**
- Implement prompt caching to reduce costs and latency by up to 90%
- Use prompt routing for intelligent model selection based on query complexity
- Understand best practices for Bedrock API integration
- Monitor performance and usage statistics for optimization

<h2>Context or Details about feature/use case</h2>

### Prompt Caching
Prompt caching allows you to cache frequently used prompts, reducing both latency and costs for subsequent requests. This is particularly beneficial for:
- **Document analysis workflows** - Cache document context for multiple questions
- **Multi-turn conversations** - Maintain conversation history efficiently  
- **Repetitive query patterns** - Avoid re-processing similar requests
- **Cost optimization** - Reduce API calls by up to 90% for repeated content

### Prompt Routing
Prompt routing intelligently directs requests to the most appropriate model based on:
- **Query complexity** - Simple queries to fast models, complex ones to capable models
- **Cost optimization requirements** - Balance performance vs. cost based on business needs
- **Performance needs** - Route time-sensitive queries to fastest available models
- **Model capabilities** - Match query type to model strengths

### Supported Models
- **Claude Haiku 3**: Fast, cost-effective for simple tasks and quick responses
- **Claude Sonnet 3.5**: Balanced performance and cost for general use cases
- **Claude Opus 3**: Most capable for complex reasoning and analysis tasks
- **Amazon Nova Models**: Latest AWS-native models with optimized performance

<h2>Prerequisites</h2>

Before running this workshop, ensure you have:

1. **AWS Account** with appropriate permissions for Amazon Bedrock
2. **Amazon Bedrock access** with Claude models enabled in your region
3. **AWS CLI configured** with valid credentials
4. **Python 3.8+** installed on your system
5. **Jupyter Notebook** environment (JupyterLab, VS Code, or similar)

### Required AWS Permissions
Your AWS credentials need the following IAM permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:ListFoundationModels",
                "bedrock:GetModelInvocationLoggingConfiguration"
            ],
            "Resource": "*"
        }
    ]
}
```

### Model Access
Ensure you have enabled access to Claude models in the Amazon Bedrock console:
- Navigate to Amazon Bedrock → Model access
- Request access to Anthropic Claude models
- Wait for approval (usually immediate for Claude models)

<h2>Setup</h2>

### 1. Clone the Repository
```bash
git clone https://github.com/aws-samples/amazon-bedrock-samples.git
cd amazon-bedrock-samples/BedrockPromptCachingRoutingDemo
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure AWS Credentials
```bash
aws configure
# Enter your AWS Access Key ID, Secret Access Key, and preferred region
```

### 4. Verify Bedrock Access
```python
import boto3
client = boto3.client('bedrock-runtime', region_name='us-east-1')
print("✅ Bedrock client initialized successfully")
```

<h2>Your code with comments starts here</h2>

The workshop is implemented as an interactive Jupyter notebook that demonstrates:

### Core Components

1. **ModelManager Class** - Handles different Claude model configurations and selection
2. **BedrockService Class** - Manages Bedrock API interactions with intelligent caching
3. **PromptRouter Class** - Implements smart routing logic based on query analysis

### Key Features Demonstrated

#### Prompt Caching Implementation
```python
class BedrockService:
    def __init__(self, client):
        self.client = client
        self.cache = {}  # In-memory cache for demo
        self.cache_stats = {'hits': 0, 'misses': 0}
    
    def invoke_model_with_cache(self, model_id: str, prompt: str, use_cache: bool = True):
        cache_key = f"{model_id}:{hash(prompt)}"
        
        # Check cache first
        if use_cache and cache_key in self.cache:
            self.cache_stats['hits'] += 1
            return self.cache[cache_key]  # Cache hit!
        
        # Make API call and cache result
        response = self._make_api_call(model_id, prompt)
        if use_cache:
            self.cache[cache_key] = response
        
        return response
```

#### Intelligent Prompt Routing
```python
class PromptRouter:
    def route_prompt(self, prompt: str, priority: str = 'balanced'):
        complexity = self.analyze_query_complexity(prompt)
        
        if priority == 'cost':
            return 'haiku'  # Cheapest option
        elif priority == 'performance':
            return 'opus'   # Most capable
        else:  # balanced
            if complexity == 'simple':
                return 'haiku'
            elif complexity == 'complex':
                return 'opus'
            else:
                return 'sonnet'
```

### Interactive Demonstrations

The notebook includes three hands-on demonstrations:

1. **Prompt Caching Demo** - Shows cache hits vs misses with performance metrics
2. **Intelligent Routing Demo** - Demonstrates model selection for different query types  
3. **Performance Comparison** - Quantifies the benefits of caching and smart routing

<h2>Other Considerations or Advanced section or Best Practices</h2>

### Production Best Practices

#### Cache Management
- **Persistent Storage**: Use Redis or DynamoDB for distributed caching in production
- **TTL Policies**: Implement time-to-live for cache entries to ensure data freshness
- **Memory Management**: Monitor cache size and implement LRU eviction policies
- **Cache Warming**: Pre-populate cache with frequently used prompts during deployment

#### Routing Optimization
- **Machine Learning**: Develop ML models to predict optimal routing based on historical performance
- **Cost Tracking**: Implement real-time cost monitoring across different models
- **A/B Testing**: Continuously test routing strategies to optimize for your specific use cases
- **Fallback Strategies**: Ensure high availability with automatic failover to backup models

#### Security Considerations
- **Data Privacy**: Ensure sensitive information is not cached inappropriately
- **Access Control**: Implement proper IAM policies for Bedrock access
- **Audit Logging**: Log all API calls and routing decisions for compliance
- **Encryption**: Use encryption at rest and in transit for cached data

#### Monitoring and Observability
```python
# Example CloudWatch metrics integration
import boto3
cloudwatch = boto3.client('cloudwatch')

def publish_cache_metrics(cache_stats):
    cloudwatch.put_metric_data(
        Namespace='BedrockWorkshop/Cache',
        MetricData=[
            {
                'MetricName': 'CacheHitRate',
                'Value': cache_stats['hit_rate_percent'],
                'Unit': 'Percent'
            },
            {
                'MetricName': 'CacheSize',
                'Value': cache_stats['cached_items'],
                'Unit': 'Count'
            }
        ]
    )
```

### Advanced Features

#### Multi-Modal Routing
Extend routing logic to handle different content types:
- Text-only queries → Claude models
- Image analysis → Claude Vision models  
- Document processing → Specialized document models

#### Streaming with Caching
Implement streaming responses while maintaining cache benefits:
```python
def stream_with_cache(self, model_id, prompt):
    cache_key = self._generate_cache_key(model_id, prompt)
    
    if cache_key in self.cache:
        # Stream cached response
        for chunk in self._stream_cached_response(cache_key):
            yield chunk
    else:
        # Stream live response and cache
        full_response = ""
        for chunk in self._stream_live_response(model_id, prompt):
            full_response += chunk
            yield chunk
        self.cache[cache_key] = full_response
```

<h2>Next Steps</h2>

After completing this workshop, consider these advanced implementations:

### 1. Production Deployment
- **Containerization**: Package the solution using Docker for consistent deployment
- **Serverless Architecture**: Deploy using AWS Lambda for automatic scaling
- **API Gateway Integration**: Create REST APIs for external application integration
- **Infrastructure as Code**: Use CloudFormation or CDK for reproducible deployments

### 2. Enhanced Monitoring
- **Custom Dashboards**: Build CloudWatch dashboards for real-time monitoring
- **Alerting**: Set up alerts for cache performance degradation or routing failures
- **Cost Analysis**: Implement detailed cost tracking and optimization recommendations
- **Performance Benchmarking**: Establish baseline metrics and track improvements

### 3. Advanced Features
- **User Personalization**: Learn user preferences to improve routing decisions
- **Multi-Region Deployment**: Implement cross-region caching and routing
- **Custom Model Integration**: Add support for fine-tuned models
- **Batch Processing**: Optimize for high-volume batch processing scenarios

### 4. Integration Patterns
- **Microservices**: Integrate caching and routing as microservices in larger applications
- **Event-Driven Architecture**: Use EventBridge for asynchronous processing
- **Data Pipeline Integration**: Incorporate into ETL/ELT workflows
- **Real-Time Applications**: Build chat applications with optimized response times

### 5. Machine Learning Enhancements
- **Predictive Routing**: Use ML to predict optimal model selection
- **Anomaly Detection**: Identify unusual patterns in cache performance
- **Auto-Scaling**: Dynamically adjust cache size based on usage patterns
- **Quality Scoring**: Implement response quality metrics for routing optimization

<h2>Cleanup</h2>

### Resource Cleanup
The workshop uses minimal AWS resources, but follow these steps to ensure clean termination:

1. **Clear Cache Memory**
   ```python
   # Clear in-memory cache
   bedrock_service.cache.clear()
   bedrock_service.cache_stats = {'hits': 0, 'misses': 0}
   ```

2. **Close Bedrock Client**
   ```python
   # Properly close the Bedrock client
   bedrock_client.close()
   ```

3. **Review CloudWatch Logs** (if logging was enabled)
   - Check CloudWatch Logs for any error messages
   - Review API call patterns and costs in AWS Cost Explorer

### Cost Considerations
- **API Calls**: The workshop makes minimal API calls to Bedrock models
- **Caching Benefits**: Demonstrates significant cost savings through reduced API usage
- **Monitoring**: No additional charges for basic CloudWatch metrics

### Final Statistics
The notebook displays comprehensive statistics including:
- Total API calls made vs. cached responses
- Cache hit rate percentage and performance improvements  
- Model usage distribution across different query types
- Estimated cost savings from caching implementation

### Verification Steps
1. Confirm all notebook cells executed successfully
2. Review cache performance metrics (should show >50% hit rate)
3. Verify routing decisions match query complexity expectations
4. Check that cleanup completed without errors

**Workshop Complete!** 🎉

You've successfully learned how to implement prompt caching and intelligent routing with Amazon Bedrock, achieving significant performance improvements and cost optimizations for AI-powered applications.