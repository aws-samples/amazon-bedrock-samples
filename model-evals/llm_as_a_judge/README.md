# Get Inferences and Model Evaluations using an _LLM as a judge_

This repo provides code samples for generating inferences from models using and provides a comprehensive _LLM as a judge_ evaluation solution. The dataset is provided by the user, which contains a `user question`, `system prompt` (optional), and a `pre existing response` (optional). This sample runs inferences against the models provided in the [config.yaml](config.yaml) file, and generates an output with a side by side view of responses from all the models. 

Next, these responses run through an evaluation solution. In this sample, a Large Language Model is used to act as an `LLM as a judge`, that goes through each user question and context, and gives the model response that best matches/answers the question in terms of _correctness_ and _relevancy_. You can use any model as an LLM as a judge by mentioning it in the `llm_as_a_judge_info` section in the `config.yaml` file (This example specifically uses the `Llama3-70b instruct model`). Once the LLM as a judge evaluation is completed, all the explanations and analysis that it provides runs through another final layer of analysis. A _final analysis summarizer_ (in this case `Claude 3`) ingests all the information from the LLM as a judge and gives a final analysis. This analysis contains overall patterns and trends as to why a particular model was selected more times than the other models for the given use case/dataset.

*All the parameters can be configured in the ['config.yaml'](config.yaml) file. The dataset used for this sample is synthetically generated, and the pre existing responses are standard definitions or human generated answers*

# Prerequisites
---

### Set up the environment

1. Run this code on an AWS platform so as to not include internet latency in the inference latency for the response.

1. Setup a Python3.11 `conda` environment for running this code.

    ```{.bash}
    conda create --name llm_as_a_judge_eval_py311 -y python=3.11 ipykernel
    source activate llm_as_a_judge_eval_py311;
    pip install -r requirements.txt
    ```

### Use your own custom dataset

1. Configure your parameters in the `config.yaml` file. 

    1. To use your own dataset, mention the dataset file name in the `pdf_dir_info` section next to `dataset_file_name` and manually place the file in this path: `data/source_data/`. Supported file formats are
    `.xlsx`/`.xls`/`.csv`. The dataset used in this example is an `.xlsx` containing about 10 questions on physics and chemistry concepts.

    ```{.yaml}
    dataset_file_name: data.xlsx
    ```

    2. Your dataset must be prepared for this sample. It should either have a `user query` column (that contains the **entire prompt payload**, including the context and the user question that can be sent for inference). For that, fill out the name of that column next to the `user_question_col` in the `dataset_info` section of the config file. If your dataset has a preexisting response you would like to evaluate as a part of this solution, mention the name of that column next to `pre_existing_response_col`.
    
    ```{.yaml}
    dataset_info:
      user_question_col: user_input
      pre_existing_response_col: model_1
    ```
    
    If your dataset has a `user_prompt` and a `system_prompt` column that you want to use instead and fit into the prompt, mention the names of both of those columns in the `user_question_col` and `system_prompt_col`. 

    ```{.yaml}
    dataset_info:
      user_question_col: user_input
      system_prompt_col: system_prompt
    ```
    *If there is no system prompt, and only a user prompt (which contains the entire prompt payload), leave the system_prompt_col empty*

# Steps to run

1. Setup the Python 3.11 `conda` environment, activate it as described in the [Prerequisites](#prerequisites) section.

1. There is a prompt template directory in this sample with prompts for different purposes as follows. Change them as preferred for your use case:

    1. `llama3_eval_prompt.txt`: This is the `LLM as a judge` prompt for the `Llama3-70b Instruct` model. This is used to parse through all the model responses, user questions, and inference results to give the best selected model for each question and a corresponding explanation as to why it chose that model.

    1. `claude_eval_prompt.txt`: This is the `LLM as a judge` prompt for `Claude 3` in case you would like to use Claude 3 as a judge.

    1. `claude_final_summary_prompt.txt`: This is the prompt template used by `Claude 3` to generate a final analysis summary of the evaluations and explanations from LLM as a judge.

    1. Change the LLM as a judge/final summarizer models and their respective prompt templates in the `config.yaml` file under the `llm_as_a_judge_info` and `final_analysis_summarizer` sections.

1. Open the `1_get_inference.ipynb` notebook, select the `llm_as_a_judge_eval_py311` kernel and do a `Run All` to run all the cells. This notebook runs inferences on models (specified in the config file) against your custom dataset. This creates the following files:
    1. `all_results.csv`: This file contains the results/responses from all the models that ran inferences, original question, target responses (if any) and their associated metrics.

1. Open the `2_get_llm_as_a_judge_eval.ipynb` notebook, select the `llm_as_a_judge_eval_py311` kernel and do a `Run All` to run all the cells. This notebook implements the evaluation solution using an LLM as a judge and a final analysis summarizer:
    1. The following output files are created in the `data` folder.
        1. `llm_as_a_judge_comparisons.csv`: This file contains the best_match_answer, selected_model and explanation in JSON format. It contains information on which model had an answer that best matched to the task that was provided, along with an explanation of why it was selected and why others weren’t.
        1. `llm_as_a_judge_comparisons.txt`: a text file to read all the comparison responses from the LLM as a judge.
        1. `inference_latency_summary.txt`: a text file that contains the `p50` and `p95` of the inference latency for each model.
        1. `llm_as_a_judge_pick_rate.csv`: Shows the LLM as a judge pick rate.
        1. `final_analysis.txt`: Shows the final analysis report generated by `Claude 3 Sonnet` based on all evaluations done by the `LLM as a judge`
        1. `all_explanations.csv`: All selected models and respective explanations generated by the `LLM as a judge` in a text file.

### Run the LLM as a judge solution via a single command
---

Another option to run this solution is to run the following commands on the terminal after completing the prerequisites:

#### Running
Run the following command which will run all the notebooks included in this repo in the correct order.

```
python main.py
```

***View the example final analysis that is generated on the evaluations done on the synthetic data by the LLM as a judge***

```
Based on the context provided, the model anthropic.claude-3-haiku-20240307-v1:0 was selected more frequently than the other models. The key reasons for its selection appear to be its ability to provide clear, concise, and comprehensive explanations on various scientific concepts and phenomena.

This model's responses were often praised for their clarity, directly addressing the questions and covering the essential points without extraneous information. For instance, its explanation of the Heisenberg uncertainty principle was described as 'complete and accurate,' while its description of the difference between nuclear fission and fusion was deemed 'clear and concise.'

Furthermore, the anthropic.claude-3-haiku-20240307-v1:0 model was commended for its ability to provide comprehensive overviews and explanations, such as its coverage of the development of atomic models and the significance of the photoelectric effect in the context of quantum mechanics.

In contrast, the other models were often criticized for providing incomplete, inaccurate, or vague responses, lacking the clarity and comprehensiveness of the anthropic.claude-3-haiku-20240307-v1:0 model. For example, model_1's answer on catalysts was deemed incomplete, while anthropic.claude-3-sonnet-20240229-v1:0's explanation on classical and quantum mechanics lacked clarity.

Overall, the anthropic.claude-3-haiku-20240307-v1:0 model was consistently praised for its ability to provide clear, concise, and comprehensive explanations on various scientific topics, making it the preferred choice for this specific dataset.
```

## License

This library is licensed under the MIT-0 License. See the [LICENSE](./LICENSE) file.
