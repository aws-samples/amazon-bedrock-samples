---
hide:
  - feedback
---
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Amazon Bedrock Recipes</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">
    <style>
        /* Reset and base styles */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Roboto', sans-serif;
            line-height: 1.6;
            color: #333333; /* Light Black */
            background-color: #ffffff; /* White */
        }
        /* Hero section */
        .hero {
            background: linear-gradient(135deg, #2c3e50, #34495e, #95a5a6);
            color: #ffffff; /* White */
            text-align: center;
            padding: 1rem 1rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            position: relative;
            overflow: hidden;
        }
        .hero::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.15) 10%, transparent 38%),
                        radial-gradient(circle, rgba(255,255,255,0.15) 10%, transparent 30%);
            background-position: 0 0, 50px 50px;
            background-size: 100px 100px;
            opacity: 0.3;
            animation: moveBackground 3s linear infinite;
            z-index: 1;
        }
        @keyframes moveBackground {
            0% { transform: translate(0, 0); }
            100% { transform: translate(-50px, -50px); }
        }
        .hero-content img {
            max-width: 155px; /* Reduced from 200px */
            margin-right: 1rem;
            vertical-align: middle;
        }
        .hero-content h1 {
            font-size: 3rem; /* Reduced from 3rem */
            font-weight: 700;
            color: #ffffff;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            display: inline-block;
            vertical-align: middle;
            margin: 0;
        }
        .hero p {
            font-size: 1.1rem; /* Reduced from 1.2rem */
            margin-bottom: 1.5rem; /* Reduced from 2rem */
            max-width: 500px; /* Reduced from 600px */
            margin-left: auto;
            margin-right: auto;
        }
        .btn {
            display: inline-block;
            padding: 10px 20px; /* Reduced from 12px 24px */
            background-color: #333333; /* Light Black */
            color: #ffffff; /* White */
            text-decoration: none;
            border-radius: 4px;
            transition: all 0.3s ease-in-out;
            font-weight: 500;
            position: relative;
            z-index: 2;
        }
        .btn:hover {
            background-color: #000000; /* Black */
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.2);
            transform: translateY(-2px);
        }
        .btn:link, .btn:visited, .btn:hover, .btn:active {
            color: #ffffff; /* White */
            text-decoration: none;
        }
        /* Main content */
        h2 {
            font-size: 2.5rem;
            margin-bottom: 1.5rem;
            color: #333333; /* Light Black */
        }
        /* Features section */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
        }
        .card {
            background-color: #f7f7f7; /* Light Grey */
            border-radius: 8px;
            padding: 10px;
            transition: box-shadow 0.2s ease-in-out;
        }
        .card:hover {
            box-shadow: 0 0 30px rgba(0, 0, 0, 0.3);
        }
        .card h3 {
            font-size: 1rem;
            margin-bottom: 1rem;
            color: #333333; /* Light Black */
        }
        .card p {
            margin-bottom: 1rem;
            color: #555555; /* Light Black */
        }
        .button {
            display: inline-block;
            background-color: #333333; /* Light Black */
            color: #ffffff; /* White */
            padding: 0.5rem 1rem;
            text-decoration: none;
            border-radius: 5px;
            transition: background-color 0.3s ease;
        }
        .button:hover {
            background-color: #000000; /* Black */
        }
        pre {
            background-color: #f2f2f2; /* Lightest Grey */
            padding: 1rem;
            border-radius: 5px;
            overflow-x: auto;
        }
        code {
            font-family: 'Roboto Mono', monospace;
        }
        .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 10px;
        }
        .grid-item {
            background: #f5f5f5;
            padding: 10px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
    </style>
</head>
<body>
    <div class="hero">
        <div class="hero-content">
            <img src="bedrock_logo.png" alt="Amazon Bedrock Logo">
            <h1>Amazon Bedrock Recipes</h1>
        </div>
        <p>A collection of resources to help builders use and learn about the features of Amazon Bedrock.</p>
    </div>

    <main>
        <section id="getting-started" class="features">
            <h2>Getting Started</h2>
                <div class="card">
                    <pre><code># Step 1: install python sdk
pip install boto3

# Step 2: clone the repository and use available notebooks
git clone https://github.com/aws-samples/amazon-bedrock-samples.git
cd amazon-bedrock-samples</code></pre>
                </div>
        </section>

        <section class="features">
            <h2>Features</h2>
            <div class="grid">
                <div class="card">
                    <h3>Agents</h3>
                    <p>Amazon Bedrock Agents enable generative AI applications to execute multi-step tasks across company systems and data sources. This streamlines workflows, automates repetitive tasks, and increases productivity while reducing costs.</p>
                    <a href="https://aws.amazon.com/bedrock/agents/" target="_blank">Learn More</a>
                </div>
                <div class="card">
                    <h3>Knowledge Bases</h3>
                    <p>Amazon Bedrock Knowledge Bases provide FMs and agents with contextual information from private data sources. This enables RAG to deliver more relevant, accurate, and customized responses tailored to your company's specific needs.</p>
                    <a href="https://aws.amazon.com/bedrock/knowledge-bases/" target="_blank">Learn More</a>
                </div>
                <div class="card">
                    <h3>Guardrails</h3>
                    <p>Amazon Bedrock Guardrails offer control mechanisms to ensure AI outputs align with organizational policies and ethical standards. This feature helps maintain consistency and safety in AI-generated content across various applications.</p>
                    <a href="https://aws.amazon.com/bedrock/guardrails/" target="_blank">Learn More</a>
                </div>
                <div class="card">
                    <h3>Model Evaluation</h3>
                    <p>Amazon Bedrock's Model Evaluation allows users to assess and compare different models' performance. This feature helps in selecting the most suitable model for specific tasks, ensuring optimal results for your AI applications.</p>
                    <a href="https://aws.amazon.com/blogs/aws/amazon-bedrock-model-evaluation-is-now-generally-available/" target="_blank">Learn More</a>
                </div>
                <div class="card">
                    <h3>Prompt Management</h3>
                    <p>Amazon Bedrock Prompt Management simplifies the creation, evaluation, versioning, and sharing of prompts to help developers and prompt engineers get the best responses from foundation models (FMs) for their use cases.</p>
                    <a href="https://aws.amazon.com/bedrock/prompt-management/" target="_blank">Learn More</a>
                </div>
                <div class="card">
                    <h3>Prompt Flow</h3>
                    <p>Amazon Bedrock Prompt Flows accelerates the creation, testing, and deployment of workflows through an intuitive visual builder. Prompt Flows allows you to seamlessly link foundation models (FMs), prompts, and many AWS services and tools together.</p>
                    <a href="https://aws.amazon.com/bedrock/prompt-flows/" target="_blank">Learn More</a>
                </div>
            </div>
        </section>

        <!-- <section class="features">
            <h2>Inference Options</h2>
            <div class="grid">
                <div class="card">
                    <h3>On-demand</h3>
                    <p>On-demand Inference in Amazon Bedrock offers pay-as-you-go pricing for model usage. This flexible option allows users to access foundation models without long-term commitments, ideal for variable or unpredictable workloads.</p>
                    <a href="./general/about-knowledge-bases.md" target="_blank">Learn More</a>
                </div>
                <div class="card">
                    <h3>Cross Region Inference</h3>
                    <p>Cross Region Inference enables the use of compute resources across different AWS Regions. This feature provides higher throughput limits and enhanced resilience, helping manage traffic bursts effectively.</p>
                    <a href="./general/about-knowledge-bases.md" target="_blank">Learn More</a>
                </div>
                <div class="card">
                    <h3>Batch Inference</h3>
                    <p>Batch Inference allows processing of multiple prompts simultaneously, outputting responses to an S3 bucket. This mode offers a 50% lower price compared to on-demand pricing for select foundation models.</p>
                    <a href="./general/about-knowledge-bases.md" target="_blank">Learn More</a>
                </div>
                <div class="card">
                    <h3>Provisioned Throughput</h3>
                    <p>Provisioned Throughput mode in Amazon Bedrock allows users to purchase model units for guaranteed performance. This option is ideal for large, consistent inference workloads requiring specific throughput levels.</p>
                    <a href="./general/about-knowledge-bases.md" target="_blank">Learn More</a>
                </div>
            </div>
        </section> -->

        <section class="features">
            <h2>Support for Open Source Frameworks</h2>
            <div class="grid">
                <div class="card">
                    <!-- <h3>Open Source Integrations</h3> -->
                    <ul>
                        <li><a href="https://python.langchain.com/docs/integrations/llms/bedrock/" target="_blank">LangChain</a></li>
                        <li><a href="https://www.langchain.com/langgraph" target="_blank">LangGraph</a></li>
                        <li><a href="https://docs.llamaindex.ai/en/stable/examples/llm/bedrock/" target="_blank">LlamaIndex</a></li>
                        <!-- <li><a href="https://www.crew.ai/" target="_blank">Crew.ai</a></li> -->
                    </ul>
                </div>
            </div>
        </section>
    </main>

    <script>
        // Smooth scrolling for anchor links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                document.querySelector(this.getAttribute('href')).scrollIntoView({
                    behavior: 'smooth'
                });
            });
        });
    </script>
</body>
</html>