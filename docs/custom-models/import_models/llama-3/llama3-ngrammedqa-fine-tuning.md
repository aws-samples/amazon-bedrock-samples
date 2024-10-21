<h1> Continuous Fine-Tuning of LlaMA 3 and Importing into Bedrock: A Step-by-Step Instructional Guide </h1>

<h2> Overview </h2>

In this notebook we will walk through how to _continuously_ fine-tune a Llama-3 LLM on Amazon SageMaker using PyTorch FSDP and Flash Attention 2 including Q-LORA and PEFT. This notebook also explains using PEFT and merging the adapters. To demonstrate continous fine tuning we will take a Llama-3 Base Model fine tune using English dataset and then fine tune again using a Portuguese language dataset. Each of the fine tuned model will be imported into Bedrock. This demonstrates the ability to iteratively fine tune a model as new data originates or when there is a need to expand out further (ex: language addition in this example).

<h2> Usecase </h2>

We will quantize the model as bf16 model. We use [Supervised Fine-tuning Trainer](https://huggingface.co/docs/trl/sft_trainer) (SFT) for fine tuning the model. We will use Anthropic/Vicuna like Chat Template with User: and Assistant: roles to fine tune the model. We will use [ngram/medchat-qa](https://huggingface.co/datasets/ngram/medchat-qa) dataset for fine tuning the model. This is a high-quality dataset of 10,000 instructions and demonstrations created by skilled human annotators. Using [FSDP](https://pytorch.org/docs/main/fsdp.html) and [Q-Lora](https://arxiv.org/abs/2305.14314) allows us to fine tune Llama-3 models on 2x consumer GPU's. FSDP enables sharding model parameters, optimizer states and gradients across data parallel workers. Q- LORA helps reduce the memmory usage for finetuning LLM while preserving full 16-bit task performance. For fine tuning in this notebook we use ml.g5.12xlarge as a SageMaker Training Job. 

[Amazon SageMaker](https://aws.amazon.com/sagemaker) provides a fully managed service that enables build, train and deploy ML models at scale using tools like notebooks, debuggers, profilers, pipelines, MLOps, and more – all in one integrated development environment (IDE). [SageMaker Model Training](https://aws.amazon.com/sagemaker/train/) reduces the time and cost to train and tune machine learning (ML) models at scale without the need to manage infrastructure.

In this notebook you will leverage the ability of SageMaker Training job to download training data to download the fine tuned Large Language Model for further fine tuning.

For detailed instructions please refer to [Importing a model with customer model import Bedrock Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-customization-import-model.html).

This notebook is inspired by Philipp Schmid Blog - https://www.philschmid.de/fsdp-qlora-llama3

<h3> Model License information </h3>

In this notebook we use the Meta Llama3 model from HuggingFace. This model is a gated model within HuggingFace repository. To use this model you have to agree to the license agreement (https://llama.meta.com/llama3/license) and request access to the model before it can be used in this notebook.

<h2> Notebook code with comments: </h2>

<h3> Install the Pre-Requisites </h3>

```python
### !rm -fR /opt/conda/lib/python3.10/site-packages # Run if you are getting conflicts with fsspec packages.
!pip3 uninstall autogluon autogluon-multimodal --y
!pip3 install transformers "sagemaker>=2.190.0" "huggingface_hub" "datasets[s3]==2.18.0" --upgrade --quiet
!pip3 install boto3 s3fs "aiobotocore==2.11.0" --upgrade --quiet
```

Logging into the HuggingFace Hub and requesting access to the meta-llama/Meta-Llama-3-8B is required to download the model and finetune the same. Please follow the [HuggingFace User Token Documentation](https://huggingface.co/docs/hub/en/security-tokens) to request tokens to be provided in the textbox appearning below after you run the cell.


```python
from huggingface_hub import notebook_login
notebook_login()
```

<h3> Setup </h3>
We will initialize the SageMaker Session required to finetune the model.


```python
import sagemaker
import boto3
sess = sagemaker.Session()
# sagemaker session bucket -> used for uploading data, models and logs
# sagemaker will automatically create this bucket if it not exists
sagemaker_session_bucket=None
if sagemaker_session_bucket is None and sess is not None:
    # set to default bucket if a bucket name is not given
    sagemaker_session_bucket = sess.default_bucket()
 
try:
    role = sagemaker.get_execution_role()
except ValueError:
    iam = boto3.client('iam')
    role = iam.get_role(RoleName='sagemaker_execution_role')['Role']['Arn']
 
sess = sagemaker.Session(default_bucket=sagemaker_session_bucket)
 
print(f"sagemaker role arn: {role}")
print(f"sagemaker bucket: {sess.default_bucket()}")
print(f"sagemaker session region: {sess.boto_region_name}")
```

<h3> Define the Parameters </h3>

```python
model_id = "meta-llama/Meta-Llama-3-8B"
# save train_dataset to s3 using our SageMaker session
training_input_base_path = f"s3://{sess.default_bucket()}/datasets/ngram/medchat-qa/"
training_input_path = f"{training_input_base_path}finetune_ip"
use_bf16 = True
```

<h3> Dataset Prepare </h3>
We will use [ngram/medchat-qa](https://huggingface.co/datasets/ngram/medchat-qa) dataset to finetune the Llama 3 model. Kindly refer to the [Licensing Information](https://huggingface.co/datasets/ngram/medchat-qa) regarding this dataset before proceeding further.

We will transform the messages to OAI format and split the data into Train and Test set. The Train and Test dataset will be uploaded into S3 - SageMaker Session Bucket for use during finetuning.


```python
from datasets import load_dataset, VerificationMode
from datasets import load_from_disk

import aiobotocore.session
s3_session = aiobotocore.session.AioSession()
storage_options = {"session": s3_session}

# Convert dataset to OAI messages
system_message = """You are Llama, a medical expert tasked with providing the most accurate and succinct answers to specific questions based on detailed medical data. Focus on precision and directness in your responses, ensuring that each answer is factual, concise, and to the point. Avoid unnecessary elaboration and prioritize accuracy over sounding confident."""
 
def create_conversation(row):
    row["messages"] = [{
        "role": "system",
        "content": system_message
    },{
        "role": "user",
        "content": row["question"]
    },{
        "role": "assistant",
        "content": row["answer"]
    }]
    return row

# Load dataset from the hub
dataset = load_dataset("ngram/medchat-qa", split="train[:100%]")
dataset = dataset.train_test_split(test_size=0.3)
print(f'Schema for dataset: {dataset}')

dataset.save_to_disk(f"{training_input_base_path}/en/", storage_options=storage_options)

# Load dataset from the hub
dataset = load_from_disk(f"s3://{sagemaker_session_bucket}/datasets/ngram/medchat-qa/en/"
                         , storage_options=storage_options)

print(f'Number of Rows: {dataset.num_rows}')

# dataset = dataset.train_test_split(test_size=0.3)
print(f'Schema for dataset: {dataset}')

# Add system message to each conversation
columns_to_remove = list(dataset["train"].features)
dataset = dataset.map(create_conversation, remove_columns=columns_to_remove, batched=False)

dataset["train"] = dataset["train"].filter(lambda x: len(x["messages"][1:]) % 2 == 0)
dataset["test"] = dataset["test"].filter(lambda x: len(x["messages"][1:]) % 2 == 0)
 
# save datasets to s3
dataset["train"].to_json(f"{training_input_path}/train_dataset.json", orient="records", force_ascii=False)
dataset["test"].to_json(f"{training_input_path}/test_dataset.json", orient="records", force_ascii=False)

print(f"Number of Rows: {dataset.num_rows}")
print(f"Training data uploaded to:")
print(f"{training_input_path}/train_dataset.json")
print(f"https://s3.console.aws.amazon.com/s3/buckets/{sess.default_bucket()}/?region={sess.boto_region_name}&prefix={training_input_path.split('/', 3)[-1]}/")
```

<h3> Training script and dependencies </h3>

Create the scripts directory to hold the training script and dependencies list. This directory will be provided to the trainer.


```python
import os
os.makedirs("scripts/trl", exist_ok=True)
```

Create the requirements file that will be used by the SageMaker Job container to initialize the dependencies.


```python
%%writefile scripts/trl/requirements.txt
torch==2.2.2
transformers==4.40.2
sagemaker>=2.190.0
datasets==2.18.0
accelerate==0.29.3
evaluate==0.4.1
bitsandbytes==0.43.1
trl==0.8.6
peft==0.10.0
```

Training Script that will use PyTorch FSDP, QLORA, PEFT and train the model using SFT Trainer. This script also includes prepping the data to Llama 3 chat template (Anthropic/Vicuna format). This training script is being written to the scripts folder along with the requirements file that will be used by the SageMaker Job.

The training script also uses either the HuggingFace Model Id or a local path (script_args.model_id_path) to load the Large Language Model for Fine Tuning the model.


```python
%%writefile scripts/trl/run_fsdp_qlora.py
import logging
from dataclasses import dataclass, field
import os
import warnings


try:
    os.system("pip install flash-attn --no-build-isolation --upgrade")
except:
    print("flash-attn failed to install")

import random
import torch
from datasets import load_dataset
from tqdm import tqdm
from trl.commands.cli_utils import  TrlParser
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    HfArgumentParser,
    BitsAndBytesConfig,
    set_seed,
    Conv1D
)
from transformers import logging as transf_logging
from trl import setup_chat_format
from peft import LoraConfig, prepare_model_for_kbit_training

from trl import (
   SFTTrainer)

# Comment in if you want to use the Llama 3 instruct template but make sure to add modules_to_save
# LLAMA_3_CHAT_TEMPLATE="{% set loop_messages = messages %}{% for message in loop_messages %}{% set content = '<|start_header_id|>' + message['role'] + '<|end_header_id|>\n\n'+ message['content'] | trim + '<|eot_id|>' %}{% if loop.index0 == 0 %}{% set content = bos_token + content %}{% endif %}{{ content }}{% endfor %}{% if add_generation_prompt %}{{ '<|start_header_id|>assistant<|end_header_id|>\n\n' }}{% endif %}"

# Anthropic/Vicuna like template without the need for special tokens
LLAMA_3_CHAT_TEMPLATE = (
    "{% for message in messages %}"
        "{% if message['role'] == 'system' %}"
            "{{ message['content'] }}"
        "{% elif message['role'] == 'user' %}"
            "{{ '\n\nHuman: ' + message['content'] +  eos_token }}"
        "{% elif message['role'] == 'assistant' %}"
            "{{ '\n\nAssistant: '  + message['content'] +  eos_token  }}"
        "{% endif %}"
    "{% endfor %}"
    "{% if add_generation_prompt %}"
    "{{ '\n\nAssistant: ' }}"
    "{% endif %}"
)

transf_logging.set_verbosity_error()
tqdm.pandas()

@dataclass
class ScriptArguments:
    dataset_path: str = field(
        default=None,
        metadata={
            "help": "Path to the dataset"
        },
    )
    model_id_path: str = field(
        default=None, metadata={"help": "Model S3 Path to use for SFT training"}
    )
    max_seq_length: int = field(
        default=512, metadata={"help": "The maximum sequence length for SFT Trainer"}
    )
    use_qlora: bool = field(default=False, metadata={"help": "Whether to use QLORA"})
    merge_adapters: bool = field(
        metadata={"help": "Wether to merge weights for LoRA."},
        default=False,
    )


def get_specific_layer_names(model):
    # Create a list to store the layer names
    layer_names = []
    
    # Recursively visit all modules and submodules
    for name, module in model.named_modules():
        # Check if the module is an instance of the specified layers
        if isinstance(module, (torch.nn.Linear, torch.nn.Embedding, torch.nn.Conv2d, Conv1D)):
            # model name parsing 
            layer_names.append('.'.join(name.split('.')[4:]).split('.')[0])
    
    return layer_names

def training_function(script_args, training_args):
    ################
    # Dataset
    ################
    
    train_dataset = load_dataset(
        "json",
        data_files=os.path.join(script_args.dataset_path, "train_dataset.json"),
        split="train",
    )
    test_dataset = load_dataset(
        "json",
        data_files=os.path.join(script_args.dataset_path, "test_dataset.json"),
        split="train",
    )

    torch.cuda.memory_summary(abbreviated=True) # Return a human-readable printout of the current memory allocator statistics for a given device.
    ################
    # Model & Tokenizer
    ################

    print(f"##################     Using model_id_path: {script_args.model_id_path}        ################")
    # Tokenizer        
    tokenizer = AutoTokenizer.from_pretrained(pretrained_model_name_or_path=script_args.model_id_path
                                              , use_fast=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.chat_template = LLAMA_3_CHAT_TEMPLATE
    
    # template dataset
    def template_dataset(examples):
        return{"text":  tokenizer.apply_chat_template(examples["messages"], tokenize=False)}
    
    train_dataset = train_dataset.map(template_dataset, remove_columns=["messages"])
    test_dataset = test_dataset.map(template_dataset, remove_columns=["messages"])
    
    # print random sample
    with training_args.main_process_first(
        desc="Log a few random samples from the processed training set"
    ):
        for index in random.sample(range(len(train_dataset)), 2):
            print(train_dataset[index]["text"])

    # Model    
    torch_dtype = torch.bfloat16 if training_args.bf16 else torch.float32
    quant_storage_dtype = torch.bfloat16

    if script_args.use_qlora:
        print(f"Using QLoRA - {torch_dtype}")
        quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch_dtype,
                bnb_4bit_quant_storage=quant_storage_dtype,
            )
        # For 8 bit quantization
        # quantization_config = BitsAndBytesConfig(load_in_8bit=True,
        #                                          llm_int8_threshold=200.0)
    else:
        quantization_config = None
        
    model = AutoModelForCausalLM.from_pretrained(
        pretrained_model_name_or_path=script_args.model_id_path,
        quantization_config=quantization_config,
        device_map={'':torch.cuda.current_device()},
        attn_implementation="flash_attention_2", # use sdpa, alternatively use "flash_attention_2"
        torch_dtype=quant_storage_dtype,
        use_cache=False if training_args.gradient_checkpointing else True,  # this is needed for gradient checkpointing
    )

    print(f"Model Layers: {list(set(get_specific_layer_names(model)))} ")
    
    if training_args.gradient_checkpointing:
        model.gradient_checkpointing_enable()

    ################
    # PEFT
    ################

    # LoRA config based on QLoRA paper & Sebastian Raschka experiment
    peft_config = LoraConfig(
        lora_alpha=8,
        lora_dropout=0.05,
        r=16,
        bias="none",
        #target_modules="all-linear",
        target_modules=['q_proj', 'v_proj'],
        task_type="CAUSAL_LM",
        # target_modules=['up_proj', 'down_proj', 'gate_proj', 'k_proj', 'q_proj', 'v_proj', 'o_proj']
        # modules_to_save = ["lm_head", "embed_tokens"] # add if you want to use the Llama 3 instruct template
    )

    ################
    # Training
    ################
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        dataset_text_field="text",
        eval_dataset=test_dataset,
        peft_config=peft_config,
        max_seq_length=script_args.max_seq_length,
        tokenizer=tokenizer,
        packing=True,
        dataset_kwargs={
            "add_special_tokens": False,  # We template with special tokens
            "append_concat_token": False,  # No need to add additional separator token
        },
    )
    if trainer.accelerator.is_main_process:
        print("###############     Printing Trainable Parameters     ###############")
        trainer.model.print_trainable_parameters()
        print("###############     Printing Trainable Parameters - Completed!!!     ###############")

    ##########################
    # Train model
    ##########################
    checkpoint = None
    if training_args.resume_from_checkpoint is not None:
        checkpoint = training_args.resume_from_checkpoint
    trainer.train(resume_from_checkpoint=checkpoint)

    ##########################
    # SAVE MODEL FOR SAGEMAKER
    ##########################
    sagemaker_save_dir = "/opt/ml/model"

    if trainer.is_fsdp_enabled:
        trainer.accelerator.state.fsdp_plugin.set_state_dict_type("FULL_STATE_DICT")

    if script_args.merge_adapters:
        # merge adapter weights with base model and save
        # save int 4 model
        print('########## Merging Adapters  ##########')
        trainer.model.save_pretrained(training_args.output_dir)
        trainer.tokenizer.save_pretrained(training_args.output_dir)
        trainer.tokenizer.save_pretrained(sagemaker_save_dir) 
        # clear memory
        del model
        del trainer
        torch.cuda.empty_cache()

        from peft import AutoPeftModelForCausalLM

        # list file in output_dir
        print(f" contents of {training_args.output_dir} : {os.listdir(training_args.output_dir)}")

        # list files in sagemaker_save_dir
        print(f" contents of {sagemaker_save_dir} : {os.listdir(sagemaker_save_dir)}")
        
        # load PEFT model
        model = AutoPeftModelForCausalLM.from_pretrained(
            training_args.output_dir,
            low_cpu_mem_usage=True,
            torch_dtype=torch.float16, # loading in other precision types gives errors.
            is_trainable=True, # Setting this to true only will allow further fine tuning.
            device_map={'':torch.cuda.current_device()}
        )
        # Merge LoRA and base model and save
        model = model.merge_and_unload()
        print(f"#########              Saving Merged Model to {sagemaker_save_dir}               #########")
        model.save_pretrained(
            sagemaker_save_dir, safe_serialization=True, max_shard_size="2GB"
        )
    else:
        trainer.model.save_pretrained(sagemaker_save_dir, safe_serialization=True)
        
    # list files in sagemaker_save_dir
    print(f" contents of {sagemaker_save_dir} : {os.listdir(sagemaker_save_dir)}")
    
if __name__ == "__main__":
    parser = HfArgumentParser((ScriptArguments, TrainingArguments))
    script_args, training_args = parser.parse_args_into_dataclasses()    
    
    # set use reentrant to False
    if training_args.gradient_checkpointing:
        training_args.gradient_checkpointing_kwargs = {"use_reentrant": True}
    # set seed
    set_seed(training_args.seed)
  
    # launch training
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        training_function(script_args, training_args)
```

<h3> First Iteration of fine tuning </h3>

In this iteration of training you will download the Llama-3 base model from HuggingFace repository and fine tune the model using English language version of the dataset.

Hyperparameters, which are passed into the training job


```python
hyperparameters = {
  ### SCRIPT PARAMETERS ###
  'dataset_path': '/opt/ml/input/data/training/',    # path where sagemaker will save training dataset
  'model_id_path': f"{model_id}",         # path where the safetensor model file is downloaded to
  'max_seq_len': 3072,                               # max sequence length for model and packing of the dataset
  'use_qlora': True,                                 # use QLoRA model
  ### TRAINING PARAMETERS ###
  'num_train_epochs': 3,                             # number of training epochs
  'per_device_train_batch_size': 1,                  # batch size per device during training
  'per_device_eval_batch_size': 1,                   # batch size for evaluation    
  'gradient_accumulation_steps': 4,                  # number of steps before performing a backward/update pass
  'gradient_checkpointing': True,                    # use gradient checkpointing to save memory
  'optim': "adamw_torch",                            # use fused adamw optimizer
  'logging_steps': 10,                               # log every 10 steps
  'save_strategy': "epoch",                          # save checkpoint every epoch
  'evaluation_strategy': "epoch",
  'learning_rate': 0.0002,                           # learning rate, based on QLoRA paper
  'bf16': use_bf16,                                  # use bfloat16 precision
  'tf32': True,                                      # use tf32 precision
  'max_grad_norm': 0.3,                              # max gradient norm based on QLoRA paper
  'warmup_ratio': 0.03,                              # warmup ratio based on QLoRA paper
  'lr_scheduler_type': "constant",                   # use constant learning rate scheduler
  'report_to': "tensorboard",                        # report metrics to tensorboard
  'output_dir': '/tmp/tun',                          # Temporary output directory for model checkpoints
  'merge_adapters': True,                            # merge LoRA adapters into model for easier deployment
  'fsdp': '"full_shard auto_wrap offload"',
}
```

Use the SageMaker HuggingFace Estimator to finetune the model passing in the hyperparameters and the scripts directory from above.


```python
from sagemaker.huggingface import HuggingFace
from huggingface_hub import HfFolder 
import time

# define Training Job Name
job_name = f'{model_id.replace("/", "-")}-{"bf16" if use_bf16 else "f32" }'

# create the Estimator
huggingface_estimator = HuggingFace(
    entry_point          = 'run_fsdp_qlora.py',    # train script
    source_dir           = 'scripts/trl/',      # directory which includes all the files needed for training
    instance_type        = 'ml.g5.24xlarge',   # instances type used for the training job
    instance_count       = 1,                 # the number of instances used for training
    max_run              = 2*24*60*60,        # maximum runtime in seconds (days * hours * minutes * seconds)
    base_job_name        = job_name,          # the name of the training job
    role                 = role,              # Iam role used in training job to access AWS ressources, e.g. S3
    volume_size          = 300,               # the size of the EBS volume in GB
    transformers_version = '4.36.0',            # the transformers version used in the training job
    pytorch_version      = '2.1.0',             # the pytorch_version version used in the training job
    py_version           = 'py310',           # the python version used in the training job
    hyperparameters      =  hyperparameters,  # the hyperparameters passed to the training job
    disable_output_compression = True,        # not compress output to save training time and cost
    distribution={"torch_distributed": {"enabled": True}},
    environment          = {
        "HUGGINGFACE_HUB_CACHE": "/tmp/.cache", # set env variable to cache models in /tmp
        "HF_TOKEN": HfFolder.get_token(),       # Retrieve HuggingFace Token to be used for downloading base models from
        "ACCELERATE_USE_FSDP":"1", 
        "FSDP_CPU_RAM_EFFICIENT_LOADING":"1"
    },
    #enable_remote_debug=True
)

# define a data input dictonary with our uploaded s3 uris
data = {'training': f"{training_input_path}"}
# starting the train job with our uploaded datasets as input
huggingface_estimator.fit(data, wait=True)
```


```python
en_pubmed_model_s3_path = huggingface_estimator.model_data["S3DataSource"]["S3Uri"]
print(f"EN PubMed Fine Tuned Model S3 Location: {en_pubmed_model_s3_path}")
```

<h3> Second Iteration of fine tuning </h3>

In this iteration of fine tuning we will take the English Language Fine Tuned model from above and fine tune with a Portuguese translated version of the dataset.

First you will translate the dataset into Portuguese using Amazon Translate. You will format the dataset into OAI format and uploaded to the SageMaker Session Bucket for Fine Tuning.

Please make sure the SageMaker Role has permission to access Amazon Translate.


```python
import boto3
import aiobotocore.session

s3_session = aiobotocore.session.AioSession()
storage_options = {"session": s3_session}

global trn_client 
trn_client = boto3.client('translate')

def translate2pt(txt):
    response = trn_client.translate_text(
        Text=txt,
        SourceLanguageCode='en',
        TargetLanguageCode='pt',
    )
    return response["TranslatedText"]

def add_pt_content_to_pubmed(row):
    row['question_pt'] = translate2pt(row['question'])
    row['answer_pt'] = translate2pt(row['answer'])
    return row

from datasets import load_dataset

# Load dataset from the hub
dataset = load_dataset("ngram/medchat-qa", split="train[:100%]")
dataset = dataset.train_test_split(test_size=0.3)
print(f'Schema for dataset: {dataset}')
dataset_pt = dataset.map(add_pt_content_to_pubmed, batched=False)

dataset_pt = dataset_pt.remove_columns(["question", "answer"])
dataset_pt = dataset_pt.rename_column("question_pt", "question")
dataset_pt = dataset_pt.rename_column("answer_pt", "answer")

dataset_pt.save_to_disk(f"{training_input_base_path}/pt/", storage_options=storage_options)
```


```python
from datasets import load_dataset, VerificationMode
from datasets import load_from_disk

import aiobotocore.session
s3_session = aiobotocore.session.AioSession()
storage_options = {"session": s3_session}

# Convert dataset to OAI messages
system_message = """Você é Llama, um especialista médico encarregado de fornecer as respostas mais precisas e sucintas a perguntas específicas com base em dados médicos detalhados. Concentre-se na precisão e na franqueza de suas respostas, garantindo que cada resposta seja factual, concisa e objetiva. Evite elaborações desnecessárias e priorize a precisão em vez de parecer confiante."""
 
def create_conversation(row):
    row["messages"] = [{
        "role": "system",
        "content": system_message
    },{
        "role": "user",
        "content": row["question"]
    },{
        "role": "assistant",
        "content": row["answer"]
    }]
    return row


# Load dataset from the hub
dataset = load_from_disk(f"s3://{sagemaker_session_bucket}/datasets/ngram/medchat-qa/pt/", storage_options=storage_options)
print(f'Number of Rows: {dataset.num_rows}')

# dataset = dataset.train_test_split(test_size=0.3)
print(f'Schema for dataset: {dataset}')

# Add system message to each conversation
columns_to_remove = list(dataset["train"].features)
dataset = dataset.map(create_conversation, remove_columns=columns_to_remove, batched=False)

dataset["train"] = dataset["train"].filter(lambda x: len(x["messages"][1:]) % 2 == 0)
dataset["test"] = dataset["test"].filter(lambda x: len(x["messages"][1:]) % 2 == 0)
 
# save datasets to s3
dataset["train"].to_json(f"{training_input_path}/train_dataset.json", orient="records", force_ascii=False)
dataset["test"].to_json(f"{training_input_path}/test_dataset.json", orient="records", force_ascii=False)
 
print(f"Training data uploaded to:")
print(f"{training_input_path}/train_dataset.json")
print(f"https://s3.console.aws.amazon.com/s3/buckets/{sess.default_bucket()}/?region={sess.boto_region_name}&prefix={training_input_path.split('/', 3)[-1]}/")
```

Hyperparameters for the Fine Tuning job.

Below you will notice that the location of the downloaded English model is provided as input to model_id_path variable instead of the HuggingFace model id as in the English dataset fine tuning. The training script will load the model from the Training job local disk which is automatically downloaded from S3 bucket by SageMaker.


```python
pt_hyperparameters = {
  ### SCRIPT PARAMETERS ###
  'dataset_path': '/opt/ml/input/data/training/',    # path where sagemaker will save training dataset
  'model_id_path': '/opt/ml/input/data/model/',      # path where the safetensor model file is downloaded to
  'max_seq_len': 3072,                               # max sequence length for model and packing of the dataset
  'use_qlora': True,                                 # use QLoRA model
  ### TRAINING PARAMETERS ###
  'num_train_epochs': 1,                             # number of training epochs
  'per_device_train_batch_size': 1,                  # batch size per device during training
  'per_device_eval_batch_size': 1,                   # batch size for evaluation    
  'gradient_accumulation_steps': 4,                  # number of steps before performing a backward/update pass
  'gradient_checkpointing': True,                    # use gradient checkpointing to save memory
  'optim': "adamw_torch",                            # use fused adamw optimizer
  'logging_steps': 10,                               # log every 10 steps
  'save_strategy': "epoch",                          # save checkpoint every epoch
  'evaluation_strategy': "epoch",
  'learning_rate': 0.0002,                           # learning rate, based on QLoRA paper
  'bf16': use_bf16,                                  # use bfloat16 precision
  'tf32': True,                                      # use tf32 precision
  'max_grad_norm': 0.3,                              # max gradient norm based on QLoRA paper
  'warmup_ratio': 0.03,                              # warmup ratio based on QLoRA paper
  'lr_scheduler_type': "constant",                   # use constant learning rate scheduler
  'report_to': "tensorboard",                        # report metrics to tensorboard
  'output_dir': '/tmp/tun',                          # Temporary output directory for model checkpoints
  'merge_adapters': True,                            # merge LoRA adapters into model for easier deployment
  'fsdp': '"full_shard auto_wrap offload"',
}
```

Below you will use the SageMaker Hugging Face model and estimator to Fine Tune the model using the Portguese Dataset. 

Kindly note that you will provide the S3 location of the English Language Fine Tuned model into the fit method. The S3 path is provided in the pt_data variable in the model attribute. SageMaker automatically downloads the files from the respective S3 bucket provided to the fit method of the estimator.


```python
from sagemaker.huggingface import HuggingFace
from huggingface_hub import HfFolder 
import time

# define Training Job Name
pt_job_name = f'{model_id.replace("/", "-")}-{"bf16" if use_bf16 else "f32" }'

# create the Estimator
pt_huggingface_estimator = HuggingFace(
    entry_point          = 'run_fsdp_qlora.py',    # train script
    source_dir           = 'scripts/trl/',      # directory which includes all the files needed for training
    instance_type        = 'ml.g5.24xlarge',   # instances type used for the training job
    instance_count       = 1,                 # the number of instances used for training
    max_run              = 2*24*60*60,        # maximum runtime in seconds (days * hours * minutes * seconds)
    base_job_name        = pt_job_name,          # the name of the training job
    role                 = role,              # Iam role used in training job to access AWS ressources, e.g. S3
    volume_size          = 300,               # the size of the EBS volume in GB
    transformers_version = '4.36.0',            # the transformers version used in the training job
    pytorch_version      = '2.1.0',             # the pytorch_version version used in the training job
    py_version           = 'py310',           # the python version used in the training job
    hyperparameters      =  pt_hyperparameters,  # the hyperparameters passed to the training job
    disable_output_compression = True,        # not compress output to save training time and cost
    distribution={"torch_distributed": {"enabled": True}},
    environment          = {
        "HUGGINGFACE_HUB_CACHE": "/tmp/.cache", # set env variable to cache models in /tmp
        "HF_TOKEN": HfFolder.get_token(),       # Retrieve HuggingFace Token to be used for downloading base models from
        "ACCELERATE_USE_FSDP":"1", 
        "FSDP_CPU_RAM_EFFICIENT_LOADING":"1"
    },
    # enable_remote_debug=True
)

# define a data input dictonary with our uploaded s3 uris
pt_data = {'training': training_input_path, 
        'model': f'{en_pubmed_model_s3_path}'}

# starting the train job with our uploaded datasets as input
pt_huggingface_estimator.fit(pt_data, wait=True)
```


```python
pt_pubmed_model_s3_path = pt_huggingface_estimator.model_data["S3DataSource"]["S3Uri"]
print(f"PT PubMed Fine Tuned Model S3 Location: {pt_pubmed_model_s3_path}")
```

<h3> Import the finetuned model into Bedrock: </h3>

Below works only after Bedrock Custom Model Import feature is Generally Available (GA)


```python
import boto3
import datetime
print(boto3.__version__)
```


```python
br_client = boto3.client('bedrock', region_name='us-west-2')
```


```python
pt_model_nm = "Meta-Llama-3-8B-bf16-MedChatQA-PT"
pt_imp_jb_nm = f"{pt_model_nm}-{datetime.datetime.now().strftime('%Y%m%d%M%H%S')}"
role_arn = "<<bedrock_role_with_custom_model_import_policy>>"
pt_model_src = {"s3DataSource": {"s3Uri": f"{pt_pubmed_model_s3_path}"}}

resp = br_client.create_model_import_job(jobName=pt_imp_jb_nm,
                                  importedModelName=pt_model_nm,
                                  roleArn=role_arn,
                                  modelDataSource=pt_model_src)
```


```python
en_model_nm = "Meta-Llama-3-8B-bf16-MedChatQA-EN"
en_imp_jb_nm = f"{en_model_nm}-{datetime.datetime.now().strftime('%Y%m%d%M%H%S')}"
role_arn = "<<bedrock_role_with_custom_model_import_policy>>"
en_model_src = {"s3DataSource": {"s3Uri": f"{en_pubmed_model_s3_path}"}}

resp = br_client.create_model_import_job(jobName=en_imp_jb_nm,
                                  importedModelName=en_model_nm,
                                  roleArn=role_arn,
                                  modelDataSource=en_model_src)
```

<h3> Invoke the imported model using Bedrock API's </h3>


```python
!pip install boto3 botocore --upgrade --quiet
```


```python
import boto3
import json
from botocore.exceptions import ClientError
```


```python
client = boto3.client("bedrock-runtime", region_name="<<region-name>>")

model_id = "<<bedrock-model-arn>>"
```


```python
def call_invoke_model_and_print(native_request):
    request = json.dumps(native_request)

    try:
        # Invoke the model with the request.
        response = client.invoke_model(modelId=model_id, body=request)
        model_response = json.loads(response["body"].read())

        response_text = model_response["outputs"][0]["text"]
        print(response_text)     
    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        exit(1)
```


```python
system_prompt = """[INST]You are a medical expert tasked with providing the most accurate and succinct answers to specific questions based on detailed medical data. Focus on precision and directness in your responses, ensuring that each answer is factual, concise, and to the point. Avoid unnecessary elaboration and prioritize accuracy over sounding confident. Here are some guidelines for your responses:

- Provide clear, direct answers without filler or extraneous details.
- Base your responses solely on the information available in the medical text provided.
- Ensure that your answers are straightforward and easy to understand, yet medically accurate.
- Avoid speculative or generalized statements that are not directly supported by the text.

Use these guidelines to formulate your answers to the questions presented [/INST]"""

prompt = """What is the recommended treatment for metformin overdosage?<|end_of_text|>

A:
"""
formatted_prompt = f"{system_prompt}\n\n{prompt}"

native_request = {
    "prompt": formatted_prompt,
    "top_p": 0.9,
    "temperature": 0.6,    
}

call_invoke_model_and_print(native_request)
```


```python
system_prompt = """[INST]You are a medical expert tasked with providing the most accurate and succinct answers to specific questions based on detailed medical data. Focus on precision and directness in your responses, ensuring that each answer is factual, concise, and to the point. Avoid unnecessary elaboration and prioritize accuracy over sounding confident. Here are some guidelines for your responses:

- Provide clear, direct answers without filler or extraneous details.
- Base your responses solely on the information available in the medical text provided.
- Ensure that your answers are straightforward and easy to understand, yet medically accurate.
- Avoid speculative or generalized statements that are not directly supported by the text.

Use these guidelines to formulate your answers to the questions presented [/INST]"""

prompt = """What is the recommended treatment for metformin overdosage?<|end_of_text|>

A:
"""
formatted_prompt = f"{system_prompt}\n\n{prompt}"

native_request = {
    "prompt": formatted_prompt,
    "max_tokens": 512,
    "top_p": 0.9,
    "temperature": 0.6,
}

# Convert the native request to JSON.
request = json.dumps(native_request)

try:
    # Invoke the model with the request.
    streaming_response = client.invoke_model_with_response_stream(
        modelId=model_id, body=request
    )

    # Extract and print the response text in real-time.
    for event in streaming_response["body"]:
        chunk = json.loads(event["chunk"]["bytes"])
        if "outputs" in chunk:
            print(chunk["outputs"][0].get("text"), end="")

except (ClientError, Exception) as e:
    print(f"ERROR: Can't invoke '{model_id}''. Reason: {e}")
    exit(1)
```

<h3> Clean up the Bedrock Imported Models </h3>


```python
resp = br_client.delete_imported_model(modelIdentifier=model_id)
```
