<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Amazon Bedrock Cookbook</title>
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
            animation: moveBackground 2s linear infinite;
            z-index: 1;
        }
        @keyframes moveBackground {
            0% { transform: translate(0, 0); }
            100% { transform: translate(-50px, -50px); }
        }
        .hero-content img {
            max-width: 200px;
            margin-right: 1rem;
            vertical-align: middle;
        }
        .hero-content h1 {
            font-size: 3rem;
            font-weight: 700;
            color: #ffffff;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            display: inline-block;
            vertical-align: middle;
            margin: 0;
        }
        .hero p {
            font-size: 1.2rem;
            margin-bottom: 2rem;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
        }
        .btn {
            display: inline-block;
            padding: 12px 24px;
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
            gap: 2rem;
        }
        .card {
            background-color: #f7f7f7; /* Light Grey */
            border-radius: 8px;
            padding: 20px;
            transition: box-shadow 0.1s ease-in-out;
        }
        .card:hover {
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.3);
        }
        .card h3 {
            font-size: 1.2rem;
            margin-bottom: 1rem;
            color: #333333; /* Light Black */
        }
        .card p {
            margin-bottom: 1.5rem;
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
        gap: 20px;
        }
        .grid-item {
            background: #f5f5f5;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
    </style>
</head>
<body>
    <div class="hero">
        <div class="hero-content">
            <img src="bedrock_logo.png" alt="Amazon Bedrock Logo">
            <h1>Amazon Bedrock Cookbook</h1>
        </div>
        <p>A collection of resources to help builders use and learn about the features of Amazon Bedrock.</p>
        <a href="#getting-started" class="btn">Get Started</a>
    </div>

    <main>
        <section id="getting-started" class="features">
            <h2>Getting Started</h2>
            <div class="grid">
                <div class="card">
                    <h3>Clone Repository</h3>
                    <p>Clone the Amazon Bedrock Samples repository to get started:</p>
                    <pre><code>git clone git@github.com:aws-samples/amazon-bedrock-samples.git
cd amazon-bedrock-samples</code></pre>
                </div>
            </div>
        </section>

        <section class="features">
            <h2>Features</h2>
            <div class="grid">
                <div class="card">
                    <h3>Knowledge Bases</h3>
                    <p>With Amazon Bedrock Knowledge Bases, you can give FMs and agents contextual information from your company's private data sources for RAG to deliver more relevant, accurate, and customized responses.</p>
                    <a href="./general/about-knowledge-bases.md" target="_blank">Learn More</a>
                </div>
                <div class="card">
                    <h3>Agents</h3>
                    <p>With Amazon Bedrock Agents, you can enable generative AI applications to execute multistep tasks across your company's systems and data sources, streamlining workflows and automating repetitive tasks for increased productivity and cost reduction.</p>
                    <a href="./general/about-agents.md" target="_blank">Learn More</a>
                </div>
                <div class="card">
                    <h3>Open Source Framework</h3>
                    <p>Amazon Bedrock supports most commonly used open source frameworks like Langchain and Llama index</p>
                    <a href="./general/about-open-source.md" target="_blank">Learn More</a>
                </div>
                <div class="card">
                    <h3>Amazon Bedrock SDK</h3>
                    <pre><code>#Install python SDK<br>pip install boto3</code></pre>
                    <p><b>Learn about the Bedrock APIs</b></p>
                    <a href="https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock.html" target="_blank">Bedrock SDK</a>
                    <br>
                    <a href="https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime.html" target="_blank">Bedrock Runtime SDK</a>
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