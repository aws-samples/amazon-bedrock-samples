import pytest
from evaluation import KnowledgeBasesEvaluations
import sys
from config import MODEL_ID_EVAL, MODEL_ID_GEN, KB_ID
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_recall,
    answer_similarity)
import pytest_check as check
from pytest_cases import parametrize, parametrize_with_cases
from datetime import datetime
from pytest_metadata.plugin import metadata_key

@pytest.fixture(scope="session", autouse=True)
def log_global_env_facts(record_testsuite_property):
    record_testsuite_property("Model for eval", MODEL_ID_EVAL)
    record_testsuite_property("Model for generation", MODEL_ID_GEN)
    record_testsuite_property("Knowledge base ID", KB_ID)
    record_testsuite_property("Date and time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def pytest_html_report_title(report):
    report.title = "Evaluating RAG application built using Knowledge Bases"

def pytest_configure(config):
    config.stash[metadata_key]["Model for eval"] = MODEL_ID_EVAL
    config.stash[metadata_key]["Model for generation"] = MODEL_ID_GEN
    config.stash[metadata_key]["Knowledge base ID"] = KB_ID
    config.stash[metadata_key]["Date and time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class CasesRAG:
    eval_question_answer_pair = [("How does the Company determine if an arrangement qualifies as a lease?","The Company determines if an arrangement is a lease at inception."),
                                 ("What is the Company's policy regarding the recognition of right-of-use (ROU) assets and lease liabilities for short-term leases?","The Company has elected not to recognize ROU assets and lease liabilities for short-term leases that have a lease term of 12 months or less. The Company recognizes the lease payments associated with its short-term leases as an expense on a straight-line basis over the lease term."), 
                                 ("How are operating lease ROU assets and lease liabilities presented on the Company's consolidated balance sheets?", "Operating lease ROU assets are presented separately on the consolidated balance sheets. Operating lease liabilities are presented separately as current and non-current liabilities on the consolidated balance sheets.")
                                 ]
    
    @parametrize(**{"questions, ground_truths":eval_question_answer_pair})
    def case_faithfulness(self, questions,ground_truths):
        metrics = [faithfulness]
        kb_evaluate = KnowledgeBasesEvaluations(MODEL_ID_EVAL, MODEL_ID_GEN, metrics, [questions], [ground_truths], KB_ID)
        kb_evaluate.evaluate()
        print(kb_evaluate.evaluation_results)
        return kb_evaluate.evaluation_results
    
    @parametrize(**{"questions, ground_truths":eval_question_answer_pair})
    def case_context_recall(self, questions,ground_truths):
        metrics = [context_recall]
        kb_evaluate = KnowledgeBasesEvaluations(MODEL_ID_EVAL, MODEL_ID_GEN, metrics, [questions], [ground_truths], KB_ID)
        kb_evaluate.evaluate()
        print(kb_evaluate.evaluation_results)
        return kb_evaluate.evaluation_results
    
    @parametrize(**{"questions, ground_truths":eval_question_answer_pair})
    def case_answer_relevancy(self, questions,ground_truths):
        metrics = [answer_relevancy]
        kb_evaluate = KnowledgeBasesEvaluations(MODEL_ID_EVAL, MODEL_ID_GEN, metrics, [questions], [ground_truths], KB_ID)
        kb_evaluate.evaluate()
        print(kb_evaluate.evaluation_results)
        return kb_evaluate.evaluation_results
    
    @parametrize(**{"questions, ground_truths":eval_question_answer_pair})
    def case_answer_similarity(self, questions,ground_truths):
        metrics = [answer_similarity]
        kb_evaluate = KnowledgeBasesEvaluations(MODEL_ID_EVAL, MODEL_ID_GEN, metrics, [questions], [ground_truths], KB_ID)
        kb_evaluate.evaluate()
        print(kb_evaluate.evaluation_results)
        return kb_evaluate.evaluation_results


# content of test_class.py
class TestClass:

    @parametrize_with_cases("results", cases='.', glob="*faithfulness")
    def test_faithfulness(self, results):
        assert results["faithfulness"] >= 0.7

    @parametrize_with_cases("results", cases='.', glob="*context_recall")
    def test_context_recall(self, results):
        assert results["context_recall"] >= 0.7
    
    @parametrize_with_cases("results", cases='.', glob="*answer_similarity")
    def test_answer_similarity(self, results):
        assert results["answer_similarity"] >= 0.8
    
    @parametrize_with_cases("results", cases='.', glob="*answer_relevancy")
    def test_answer_relevancy(self, results):
        assert results["answer_relevancy"] >= 0.6