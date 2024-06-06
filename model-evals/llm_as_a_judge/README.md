# Get Inferences and Model Evaluations using an `LLM as a judge pipeline`

This repo provides code samples for generating inferences from bedrock models (`Claude 3`) using `Litellm`, and provided an `LLM as a judge` evaluation pipeline. The dataset is provided by the user, which contains a `user question`, `context`, and a `target response` (if any). This sample runs inferences against the provided models in the [config.yaml](config.yaml) file, and generates an output with a side by side view of responses from all of the models. 

Next, these responses run through an evaluation pipeline. In this sample, `Llama3-70b Instruct` is used to act as an `LLM as a judge`, that goes through each user question and context, and gives the model response that best matches/answers the question in terms of *correctness* and *relevancy*. Once the `LLM as a judge` criteria is over, all of the explanations (and corresponding selected models) that it provides runs through another final layer of analysis. `Claude 3 Sonnet` ingests all of the information from the `LLM as a judge` and gives a final report. This report contains the `recommended model`, `trends` and `patterns` across the `LLM as a judge evaluation` and which model is preferred for the given use case/dataset.

*All of the parameters can be configured in the ['config.yaml'](config.yaml) file. The dataset used for this sample is synthetically generated, and the target responses are standard definitions and human answers*

# Prerequisites

1. Run this code on an AWS platform so as to not include internet latency in the inference latency for the response.

1. Setup a Python3.11 `conda` environment for running this code.

    ```{.bash}
    conda create --name llm_as_a_judge_eval_py311 -y python=3.11 ipykernel
    source activate llm_as_a_judge_eval_py311;
    pip install -r requirements.txt
    ```

1. Configure your parameters in the `config.yaml` file. 

    1. To use your own data, mention the dataset file name in the `pdf_dir_info` next to `dataset_file_name` and place the file in this path: `data/source_data/`. 

    ```{.yaml}
    pdf_dir_info:
    data_dir: data
    dataset_dir: source_data
    dataset_file_name: dummy_data.xlsx
    ```

    2. Mention the user query/question column name and the context column name from your dataset in the `dataset_info` section as follows:
    
    ```{.yaml}
    dataset_info:
    user_question_col: user_input
    context_col: context
    target_response_col: dummy_model_response
    ```
    
    If your dataset has a `user_prompt` and a `system_prompt` column that you want to use instead. Set the `is_system_and_user_role` parameter to `True` and mention the names of those columns in the section below:

    ```{.yaml}
    is_system_and_user_role: True  
    user_prompt: user_input
    system_prompt: system_prompt
    ```
    *Otherwise, let this be set to False*

# Steps to run

1. Setup the Python 3.11 `conda` environment, activate it as described in the [Prerequisites](#prerequisites) section, and insert your `xlsx` dataset.

1. There is a prompt template directory in this sample with prompts for different purposes as follows. Change them as preferred for your use case:

    1. `claude_inference_prompt_template.txt`: This is a simple `RAG` prompt for a question and answering task for `Claude` that it uses while getting inferences for the Anthropic models. You can bring your own prompt template for any other model.

    1. `llama3_eval_prompt`: This is the `LLM as a judge` prompt that in this case `Llama3-70b` uses to parse through all the model responses, user questions, and gives the best selected model for each question and a corresponding explanation as to why it chose that model.

    1. `claude_eval_prompt`: This is the `LLM as a judge` prompt for `Claude` in case you would like to use Claude as a judge.

    1. `claude_inference_prompt_template`: This is the prompt that `Claude Sonnet` uses to parse through evaluations from the `LLM as a judge`, and gives a final summarized analysis on which model to use and why, highlights trends and patterns for the given dataset.

1. Open the `get_llm_judge_evaluations.ipynb` notebook, select the `llm_as_a_judge_eval_py311` kernel and do a `Run All` to run all the cells.

1. The following output files are created in the `data` folder.

    1. `all_results.csv`: This file contains the results/responses from all the models that ran inferences, original question, target responses (if any) and their associated metrics.
    1. `llm_as_a_judge_comparisons.csv`: This file contains the best_match_answer, selected_model and explanation in JSON format. It contains information on which model had an answer that best matched to the task that was provided, along with an explanation of why it was selected and why others weren’t.
    1. `llm_as_a_judge_comparisons.txt`: a text file to read all the comparison responses from the LLM as a judge.
    1. `inference_latency_summary.txt`: a text file that contains the `p50` and `p95` of the inference latency for each model.
    1. `llm_as_a_judge_pick_rate.csv`: Shows the LLM as a judge pick rate.
    1. `final_analysis.csv`: Shows the final analysis report generated by `Claude Sonnet` based on all evaluations done by the `LLM as a judge`
    1. `all_explanations.csv`: All selected models and respective explanations generated by the `LLM as a judge` in a text file.

***View the example final analysis that `Claude Sonnet` generates on the evaluations done on the synthetic data***

```
The given data consists of a series of user questions related to various physics and chemistry concepts, along with generated answers from different models. For each question, the best model answer is selected, accompanied by an explanation justifying the selection over other models.

Upon analyzing the data, several trends and patterns emerge:

1. Common Types of Questions: The majority of questions revolve around fundamental physics concepts like thermodynamics, quantum mechanics, atomic models, and nuclear processes. Chemistry-related questions, such as those on chemical reactions and the greenhouse effect, are also present.

2. Frequently Selected Models: The model 'anthropic.claude-3-haiku-20240307-v1:0' is the most frequently selected as the best answer for various questions. It is chosen for its clear, concise, and accurate explanations across a range of topics.

3. Reasons for Model Selection: The primary factors influencing model selection are:
   - Completeness and accuracy of the answer
   - Clarity and conciseness of the explanation
   - Inclusion of relevant details and examples
   - Addressing the core concept or principle in the question

4. Reasons for Model Rejection: Models are typically rejected when they provide incomplete, inaccurate, or extraneous information, or fail to address the key aspects of the question adequately.

Based on the analysis, the following insights can be drawn regarding model suitability:

- The 'anthropic.claude-3-haiku-20240307-v1:0' model is well-suited for providing clear and comprehensive explanations of complex physics and chemistry concepts. It excels at addressing the core principles and presenting information concisely without sacrificing accuracy or relevant details.

- The 'anthropic.claude-3-sonnet-20240229-v1:0' model is also commendable for its detailed and structured answers, making it a viable choice for scenarios where more in-depth explanations are required.

- Models that provide partial or tangential information, or lack specificity, are generally less suitable for questions demanding precise and focused responses.

In summary, for this dataset focused on physics and chemistry concepts, the 'anthropic.claude-3-haiku-20240307-v1:0' model emerges as the most appropriate choice due to its ability to provide clear, concise, and accurate explanations across a wide range of topics. Its consistent selection and the explanations provided indicate its suitability for this use case.

Examples:

1. For the question on the Heisenberg uncertainty principle, 'anthropic.claude-3-haiku-20240307-v1:0' was selected for its 'complete and accurate description' and mentioning the principle's implications.

2. When explaining the difference between endothermic and exothermic reactions, this model was chosen for 'directly addressing the question' and providing a clear explanation of energy flow and temperature changes.

3. In the case of the photoelectric effect, 'anthropic.claude-3-haiku-20240307-v1:0' was preferred for its comprehensive answer, covering not only the definition but also its significance in the development of quantum mechanics.

While other models like 'anthropic.claude-3-sonnet-20240229-v1:0' and 'dummy_model' were occasionally selected for specific questions, the 'anthropic.claude-3-haiku-20240307-v1:0' model demonstrated a consistent ability to provide accurate, focused, and well-rounded explanations across various physics and chemistry topics, making it the most suitable choice for this dataset.

```


## License

This library is licensed under the MIT-0 License. See the [LICENSE](./LICENSE) file.
