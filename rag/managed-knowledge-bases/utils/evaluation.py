"""
RAG Evaluation utility for Bedrock Managed Knowledge Bases using
Amazon Bedrock's built-in knowledge base evaluation job API.

Supports two evaluation approaches:
  1. Bedrock native evaluation (evaluate_with_bedrock) — uses the Bedrock
     evaluation job API with automatic dataset generation or a provided dataset.
  2. RAGAS-based evaluation (evaluate_with_ragas) — uses the open-source RAGAS
     framework with LangChain for retrieval + generation + scoring.

Usage:
    from utils.evaluation import BMKBEvaluator

    evaluator = BMKBEvaluator(
        kb_id="ABCDEF1234",
        generation_model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        region_name="us-west-2",
    )

    # Option 1: Bedrock native evaluation
    results = evaluator.evaluate_with_bedrock(
        eval_name="my-bmkb-eval",
        output_s3_uri="s3://my-bucket/eval-output/",
        role_arn="arn:aws:iam::123456789:role/BedrockEvalRole",
    )

    # Option 2: RAGAS evaluation
    df = evaluator.evaluate_with_ragas(
        questions=["What is Amazon Bedrock?", ...],
        ground_truths=["Amazon Bedrock is...", ...],
    )
"""

import json
import time
import boto3
import pprint
from botocore.client import Config

pp = pprint.PrettyPrinter(indent=2)

# ── Preview / GA toggle ──────────────────────────────────────────────────
# BMKB is now GA. Standard boto3 is used everywhere.
USE_PREVIEW_SDK = False


def _get_session(use_preview: bool):
    """Return a boto3 session — preview-aware or standard."""
    if use_preview:
        try:
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
            from preview_session import session as preview_sess
            return preview_sess
        except ImportError:
            print("⚠️  preview_session not found, falling back to standard boto3.")
            return boto3.Session()
    return boto3.Session()


class BMKBEvaluator:
    """Evaluate a Bedrock Managed Knowledge Base using Bedrock or RAGAS."""

    def __init__(
        self,
        kb_id: str,
        generation_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0",
        eval_model_id: str = None,
        embedding_model_id: str = "amazon.titan-embed-text-v2:0",
        region_name: str = None,
        num_results: int = 5,
        use_preview_session: bool = None,
    ):
        """
        Args:
            kb_id: Knowledge Base ID to evaluate.
            generation_model_id: Model for answer generation.
            eval_model_id: Model for evaluation scoring (defaults to generation_model_id).
            embedding_model_id: Embedding model for RAGAS semantic similarity.
            region_name: AWS region.
            num_results: Number of retrieval results per query.
            use_preview_session: Use preview SDK session. Defaults to module-level
                                 USE_PREVIEW_SDK flag. Set to False for GA.
        """
        self.kb_id = kb_id
        self.generation_model_id = generation_model_id
        self.eval_model_id = eval_model_id or generation_model_id
        self.embedding_model_id = embedding_model_id
        self.num_results = num_results

        boto3_session = boto3.Session()
        self.region_name = region_name or boto3_session.region_name
        self.account_id = boto3.client("sts").get_caller_identity()["Account"]

        bedrock_config = Config(connect_timeout=120, read_timeout=120, retries={"max_attempts": 3})

        # Runtime client — controlled by module-level USE_PREVIEW_SDK or per-instance override
        use_preview = use_preview_session if use_preview_session is not None else USE_PREVIEW_SDK
        session = _get_session(use_preview)
        self.bedrock_agent_runtime = session.client(
            "bedrock-agent-runtime", region_name=self.region_name, config=bedrock_config
        )

        self.bedrock_client = boto3.client(
            "bedrock-runtime", region_name=self.region_name, config=bedrock_config
        )
        self.bedrock_eval_client = boto3.client(
            "bedrock", region_name=self.region_name
        )

    # ── Bedrock Native Evaluation ─────────────────────────────────────────

    def evaluate_with_bedrock(
        self,
        eval_name: str,
        output_s3_uri: str,
        role_arn: str,
        dataset_s3_uri: str = None,
        eval_metrics: list = None,
    ):
        """
        Run a Bedrock evaluation job for the knowledge base.

        Args:
            eval_name: Name for the evaluation job.
            output_s3_uri: S3 URI for evaluation output (e.g. s3://bucket/prefix/).
            role_arn: IAM role ARN with Bedrock evaluation permissions.
            dataset_s3_uri: Optional S3 URI to a JSONL evaluation dataset.
                            If None, Bedrock auto-generates queries.
            eval_metrics: List of metric names. Defaults to standard RAG metrics.

        Returns:
            Evaluation job response dict.
        """
        if eval_metrics is None:
            eval_metrics = [
                "Builtin.Relevance",
                "Builtin.Completeness",
                "Builtin.Groundedness",
                "Builtin.Helpfulness",
            ]

        generation_model_arn = (
            f"arn:aws:bedrock:{self.region_name}::foundation-model/{self.generation_model_id}"
        )

        # Build evaluation config
        eval_config = {
            "automated": {
                "datasetMetricConfigs": [
                    {
                        "taskType": "RetrieveAndGenerate",
                        "metricNames": eval_metrics,
                        "dataset": {},
                    }
                ]
            }
        }

        if dataset_s3_uri:
            eval_config["automated"]["datasetMetricConfigs"][0]["dataset"] = {
                "datasetLocation": {"s3Uri": dataset_s3_uri}
            }

        # Inference config for KB RAG
        inference_config = {
            "ragConfigs": [
                {
                    "knowledgeBaseConfig": {
                        "retrieveAndGenerateConfig": {
                            "type": "KNOWLEDGE_BASE",
                            "knowledgeBaseConfiguration": {
                                "knowledgeBaseId": self.kb_id,
                                "modelArn": generation_model_arn,
                                "retrievalConfiguration": {
                                    "managedSearchConfiguration": {
                                        "numberOfResults": self.num_results
                                    }
                                },
                            },
                        }
                    }
                }
            ]
        }

        print(f"Starting Bedrock evaluation job: {eval_name}")
        resp = self.bedrock_eval_client.create_evaluation_job(
            jobName=eval_name,
            roleArn=role_arn,
            evaluationConfig=eval_config,
            inferenceConfig=inference_config,
            outputDataConfig={"s3Uri": output_s3_uri},
        )

        job_arn = resp["jobArn"]
        print(f"  Job ARN: {job_arn}")

        # Poll for completion
        return self._poll_eval_job(job_arn)

    def _poll_eval_job(self, job_arn, timeout=1800, interval=30):
        """Poll evaluation job until terminal state."""
        for _ in range(timeout // interval):
            resp = self.bedrock_eval_client.get_evaluation_job(jobIdentifier=job_arn)
            status = resp["status"]
            print(f"  Eval job status: {status}")
            if status in ("Completed", "Failed", "Stopped"):
                if status == "Completed":
                    print(f"  Output: {resp.get('outputDataConfig', {}).get('s3Uri', 'N/A')}")
                elif status == "Failed":
                    print(f"  Failure: {resp.get('failureMessages', ['Unknown'])}")
                return resp
            time.sleep(interval)
        print("  Evaluation job timed out")
        return None

    # ── RAGAS Evaluation ──────────────────────────────────────────────────

    def evaluate_with_ragas(self, questions: list, ground_truths: list, delay: int = 5):
        """
        Evaluate the KB using RAGAS framework.

        Requires: pip install ragas langchain-aws datasets

        Args:
            questions: List of evaluation questions.
            ground_truths: List of expected answers (same length as questions).
            delay: Seconds between queries to avoid throttling.

        Returns:
            pandas DataFrame with per-question scores.
        """
        try:
            from langchain_aws.chat_models.bedrock import ChatBedrock
            from langchain_aws.embeddings.bedrock import BedrockEmbeddings
            from datasets import Dataset
            from ragas import evaluate
            from ragas.metrics import (
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall,
            )
        except ImportError as e:
            raise ImportError(
                f"Missing dependency: {e}\n"
                "Install with: pip install ragas langchain-aws datasets"
            )

        assert len(questions) == len(ground_truths), "questions and ground_truths must be same length"

        llm_eval = ChatBedrock(model_id=self.eval_model_id, client=self.bedrock_client)
        embeddings = BedrockEmbeddings(
            model_id=self.embedding_model_id, client=self.bedrock_client
        )

        # Generate answers and retrieve contexts
        print(f"Generating answers for {len(questions)} questions...")
        answers = []
        contexts = []

        for i, question in enumerate(questions):
            try:
                # Retrieve chunks
                retrieve_resp = self.bedrock_agent_runtime.retrieve(
                    knowledgeBaseId=self.kb_id,
                    retrievalQuery={"text": question},
                    retrievalConfiguration={
                        "managedSearchConfiguration": {"numberOfResults": self.num_results}
                    },
                )
                ctx = [
                    r["content"]["text"]
                    for r in retrieve_resp.get("retrievalResults", [])
                ]
                contexts.append(ctx)

                # Generate answer using RetrieveAndGenerate
                gen_model_arn = (
                    f"arn:aws:bedrock:{self.region_name}::foundation-model/{self.generation_model_id}"
                )
                rag_resp = self.bedrock_agent_runtime.retrieve_and_generate(
                    input={"text": question},
                    retrieveAndGenerateConfiguration={
                        "type": "KNOWLEDGE_BASE",
                        "knowledgeBaseConfiguration": {
                            "knowledgeBaseId": self.kb_id,
                            "modelArn": gen_model_arn,
                            "retrievalConfiguration": {
                                "managedSearchConfiguration": {
                                    "numberOfResults": self.num_results
                                }
                            },
                        },
                    },
                )
                answers.append(rag_resp["output"]["text"])
                print(f"  [{i+1}/{len(questions)}] done")

            except Exception as e:
                print(f"  [{i+1}/{len(questions)}] error: {e}")
                answers.append("")
                contexts.append([])

            time.sleep(delay)

        # Build RAGAS dataset
        data = {
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths,
        }
        dataset = Dataset.from_dict(data)

        print("Running RAGAS evaluation...")
        results = evaluate(
            dataset=dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            llm=llm_eval,
            embeddings=embeddings,
        )

        df = results.to_pandas()
        print(f"Evaluation complete. Average scores:")
        for col in df.columns:
            if col not in ("question", "answer", "contexts", "ground_truth"):
                print(f"  {col}: {df[col].mean():.4f}")

        return df

    # ── Helpers ────────────────────────────────────────────────────────────

    def create_eval_dataset_jsonl(self, questions: list, ground_truths: list, output_path: str):
        """
        Create a JSONL evaluation dataset file for Bedrock evaluation jobs.

        Args:
            questions: List of questions.
            ground_truths: List of expected answers.
            output_path: Local file path to write the JSONL.
        """
        assert len(questions) == len(ground_truths)
        with open(output_path, "w") as f:
            for q, gt in zip(questions, ground_truths):
                f.write(json.dumps({"query": q, "expectedResponse": gt}) + "\n")
        print(f"Wrote {len(questions)} samples to {output_path}")

    def upload_eval_dataset(self, local_path: str, s3_uri: str):
        """Upload a local evaluation dataset to S3."""
        parts = s3_uri.replace("s3://", "").split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else local_path.split("/")[-1]
        s3 = boto3.client("s3", region_name=self.region_name)
        s3.upload_file(local_path, bucket, key)
        print(f"Uploaded {local_path} to {s3_uri}")
