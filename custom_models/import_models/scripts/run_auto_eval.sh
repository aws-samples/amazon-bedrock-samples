#!/bin/bash

start=$(date +%s)

# Detect the number of NVIDIA GPUs and create a device string
gpu_count=$(nvidia-smi -L | wc -l)
if [ $gpu_count -eq 0 ]; then
    echo "No NVIDIA GPUs detected. Exiting."
    exit 1
fi

# Construct the CUDA device string
cuda_devices=""
for ((i=0; i<gpu_count; i++)); do
    if [ $i -gt 0 ]; then
        cuda_devices+=","
    fi
    cuda_devices+="$i"
done

# Install dependencies
sudo yum update -y
sudo yum install -y screen vim git-lfs
screen

# Install common libraries
pip install -q requests accelerate sentencepiece pytablewriter einops protobuf huggingface_hub==0.21.4
pip install -U transformers

# Check if HUGGINGFACE_TOKEN is set and log in to Hugging Face
if [ -n "$HUGGINGFACE_TOKEN" ]; then
    echo "HUGGINGFACE_TOKEN is defined. Logging in..."
    huggingface-cli login --token $HUGGINGFACE_TOKEN --add-to-git-credential
fi

if [ "$DEBUG" == "True" ]; then
    echo "Launch LLM AutoEval in debug mode"
fi

# Run evaluation
if [ "$BENCHMARK" == "nous" ]; then
    git clone -b add-agieval https://github.com/dmahan93/lm-evaluation-harness
    cd lm-evaluation-harness
    pip install -e .

    benchmark="agieval"
    echo "================== $(echo $benchmark | tr '[:lower:]' '[:upper:]') [1/4] =================="
    python main.py \
        --model hf-causal \
        --model_args pretrained=$MODEL_ID,trust_remote_code=$TRUST_REMOTE_CODE,dtype=float16 \
        --tasks agieval_aqua_rat,agieval_logiqa_en,agieval_lsat_ar,agieval_lsat_lr,agieval_lsat_rc,agieval_sat_en,agieval_sat_en_without_passage,agieval_sat_math \
        --device cuda:$cuda_devices \
        --batch_size auto \
        --output_path ./${benchmark}.json

    benchmark="gpt4all"
    echo "================== $(echo $benchmark | tr '[:lower:]' '[:upper:]') [2/4] =================="
    python main.py \
        --model hf-causal \
        --model_args pretrained=$MODEL_ID,trust_remote_code=$TRUST_REMOTE_CODE,dtype=float16 \
        --tasks hellaswag,openbookqa,winogrande,arc_easy,arc_challenge,boolq,piqa \
        --device cuda:$cuda_devices \
        --batch_size auto \
        --output_path ./${benchmark}.json

    benchmark="truthfulqa"
    echo "================== $(echo $benchmark | tr '[:lower:]' '[:upper:]') [3/4] =================="
    python main.py \
        --model hf-causal \
        --model_args pretrained=$MODEL_ID,trust_remote_code=$TRUST_REMOTE_CODE,dtype=float16 \
        --tasks truthfulqa_mc \
        --device cuda:$cuda_devices \
        --batch_size auto \
        --output_path ./${benchmark}.json

    benchmark="bigbench"
    echo "================== $(echo $benchmark | tr '[:lower:]' '[:upper:]') [4/4] =================="
    python main.py \
        --model hf-causal \
        --model_args pretrained=$MODEL_ID,trust_remote_code=$TRUST_REMOTE_CODE,dtype=float16 \
        --tasks bigbench_causal_judgement,bigbench_date_understanding,bigbench_disambiguation_qa,bigbench_geometric_shapes,bigbench_logical_deduction_five_objects,bigbench_logical_deduction_seven_objects,bigbench_logical_deduction_three_objects,bigbench_movie_recommendation,bigbench_navigate,bigbench_reasoning_about_colored_objects,bigbench_ruin_names,bigbench_salient_translation_error_detection,bigbench_snarks,bigbench_sports_understanding,bigbench_temporal_sequences,bigbench_tracking_shuffled_objects_five_objects,bigbench_tracking_shuffled_objects_seven_objects,bigbench_tracking_shuffled_objects_three_objects \
        --device cuda:$cuda_devices \
        --batch_size auto \
        --output_path ./${benchmark}.json

    end=$(date +%s)
    echo "Elapsed Time: $(($end-$start)) seconds"
    
    python ../llm-autoeval/main.py . $(($end-$start))

elif [ "$BENCHMARK" == "openllm" ]; then
    git clone https://github.com/EleutherAI/lm-evaluation-harness
    cd lm-evaluation-harness
    pip install -e .
    pip install accelerate

    benchmark="arc"
    echo "================== $(echo $benchmark | tr '[:lower:]' '[:upper:]') [1/6] =================="
    accelerate launch -m lm_eval \
        --model hf \
        --model_args pretrained=${MODEL_ID},dtype=auto,trust_remote_code=$TRUST_REMOTE_CODE \
        --tasks arc_challenge \
        --num_fewshot 25 \
        --batch_size auto \
        --output_path ./${benchmark}.json

    benchmark="hellaswag"
    echo "================== $(echo $benchmark | tr '[:lower:]' '[:upper:]') [2/6] =================="
    accelerate launch -m lm_eval \
        --model hf \
        --model_args pretrained=${MODEL_ID},dtype=auto,trust_remote_code=$TRUST_REMOTE_CODE \
        --tasks hellaswag \
        --num_fewshot 10 \
        --batch_size auto \
        --output_path ./${benchmark}.json

    benchmark="mmlu"
    echo "================== $(echo $benchmark | tr '[:lower:]' '[:upper:]') [3/6] =================="
    accelerate launch -m lm_eval \
        --model hf \
        --model_args pretrained=${MODEL_ID},dtype=auto,trust_remote_code=$TRUST_REMOTE_CODE \
        --tasks mmlu \
        --num_fewshot 5 \
        --batch_size auto \
        --verbosity DEBUG \
        --output_path ./${benchmark}.json
    
    benchmark="truthfulqa"
    echo "================== $(echo $benchmark | tr '[:lower:]' '[:upper:]') [4/6] =================="
    accelerate launch -m lm_eval \
        --model hf \
        --model_args pretrained=${MODEL_ID},dtype=auto,trust_remote_code=$TRUST_REMOTE_CODE \
        --tasks truthfulqa \
        --num_fewshot 0 \
        --batch_size auto \
        --output_path ./${benchmark}.json
    
    benchmark="winogrande"
    echo "================== $(echo $benchmark | tr '[:lower:]' '[:upper:]') [5/6] =================="
    accelerate launch -m lm_eval \
        --model hf \
        --model_args pretrained=${MODEL_ID},dtype=auto,trust_remote_code=$TRUST_REMOTE_CODE \
        --tasks winogrande \
        --num_fewshot 5 \
        --batch_size auto \
        --output_path ./${benchmark}.json
    
    benchmark="gsm8k"
    echo "================== $(echo $benchmark | tr '[:lower:]' '[:upper:]') [6/6] =================="
    accelerate launch -m lm_eval \
        --model hf \
        --model_args pretrained=${MODEL_ID},dtype=auto,trust_remote_code=$TRUST_REMOTE_CODE \
        --tasks gsm8k \
        --num_fewshot 5 \
        --batch_size auto \
        --output_path ./${benchmark}.json

    end=$(date +%s)
    echo "Elapsed Time: $(($end-$start)) seconds"
    
    python ../llm-autoeval/main.py . $(($end-$start))

elif [ "$BENCHMARK" == "lighteval" ]; then
    git clone https://github.com/huggingface/lighteval.git
    cd lighteval 
    pip install '.[accelerate,quantization,adapters]'
    num_gpus=$(nvidia-smi --query-gpu=count --format=csv,noheader | head -n 1)

    echo "Number of GPUs: $num_gpus"

    if [[ $num_gpus -eq 0 ]]; then
        echo "No GPUs detected. Exiting."
        exit 1

    elif [[ $num_gpus -gt 1 ]]; then
        echo "Multi-GPU mode enabled."
        accelerate launch --multi_gpu --num_processes=${num_gpus} run_evals_accelerate.py \
        --model_args "pretrained=${MODEL_ID}" \
        --use_chat_template \
        --tasks ${LIGHT_EVAL_TASK} \
        --output_dir="./evals/"

    elif [[ $num_gpus -eq 1 ]]; then
        echo "Single-GPU mode enabled."
        accelerate launch run_evals_accelerate.py \
        --model_args "pretrained=${MODEL_ID}" \
        --use_chat_template \
        --tasks ${LIGHT_EVAL_TASK} \
        --output_dir="./evals/"
    else
        echo "Error: Invalid number of GPUs detected. Exiting."
        exit 1
    fi

    end=$(date +%s)

    python ../llm-autoeval/main.py ./evals/results $(($end-$start))

elif [ "$BENCHMARK" == "eq-bench" ]; then
    git
