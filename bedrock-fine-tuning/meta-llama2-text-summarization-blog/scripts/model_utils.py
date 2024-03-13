from pathlib import Path

import boto3

import pandas as pd
import matplotlib.pyplot as plt

from scripts.utils import read_s3_file_as_dataframe

bedrock = boto3.client(service_name="bedrock")

###########################################
### Model Customization on Bedrock
###########################################

def get_model_training_process_metrics(training_job_name:str):
    """
    Get customization job training process metrics into training & validation dataframes.
    """
    response = bedrock.get_model_customization_job(jobIdentifier=training_job_name)

    if response["status"] == "Failed":
        print("Training job was failed, and there wasn't output generated.")
        return None, None

    output_uri = response["outputDataConfig"]["s3Uri"]
    job_arn = response["jobArn"]
    job_id = job_arn.split("/")[-1]
    job_output_uri = f"{output_uri}/model-customization-job-{job_id}"
    
    validation_metrics_output_uri = f"{job_output_uri}/validation_artifacts/post_fine_tuning_validation/validation/validation_metrics.csv"
    # print(f"{validation_metrics_output_uri=}")
    training_metrics_output_uri = f"{job_output_uri}/training_artifacts/step_wise_training_metrics.csv"
    # print(f"{training_metrics_output_uri=}")

    try:
        train_metrics_df = read_s3_file_as_dataframe(training_metrics_output_uri)
        validation_metrics_df = read_s3_file_as_dataframe(validation_metrics_output_uri)
    except FileNotFoundError as err:
        if response["status"] == 'InProgress':
            print("Training process is being initialized and output files are not ready, please re-try in few mins")
            return None, None
        elif response["status"] == 'Stopped':
            print("Training job was stopped, and there wasn't output generated.")
            return None, None
        else:
            raise err

    return train_metrics_df, validation_metrics_df, response["hyperParameters"], response["status"]


def plot_model_customization_training_metrics(training_job_name, train_metrics_df, validation_metrics_df, job_status:str, hyper_parameters:dict={}, include_metrics=['loss']):
    """
    Plot training process (which can be useful for tuning hyperparameters)
    """

    fig, axs = plt.subplots(len(include_metrics), 1, layout='constrained')
    fig.suptitle(f"Fine-tuning [{job_status}]{training_job_name}\n Training Process")
    # in case for only one metric, axs will be a single object
    axs = [axs] if len(include_metrics) == 1 else axs

    for index, metric_name in enumerate(include_metrics):

        training_col_name, training_label_name = f"training_{metric_name}", f"training {metric_name}"
        validation_col_name, validation_label_name = f"validation_{metric_name}", f"validation {metric_name}"
        axs[index].plot(train_metrics_df['step_number'], train_metrics_df[training_col_name], marker=".", label=training_label_name)
        axs[index].plot(validation_metrics_df['step_number'], validation_metrics_df[validation_col_name], label=validation_label_name, marker="o", color='g')

        for row in range(0, len(validation_metrics_df)):
            x = validation_metrics_df['step_number'][row]
            y = validation_metrics_df[validation_col_name][row]
            epoch = validation_metrics_df['epoch_number'][row]
            axs[index].text(x, y, f"({y:.2f},{epoch})", ha='center', va="bottom", fontsize=6)

        axs[index].legend(loc="upper right")
        axs[index].set_xlabel("Step #")
        axs[index].set_ylabel(f"{metric_name}")

    # list hyper parameters
    if hyper_parameters:
        params = [f"{k}={v}" for k, v in hyper_parameters.items()]  

        axs[-1].annotate("\n".join(params),
                xy = (1.0, -0.2),
                xycoords='axes fraction',
                ha='right',
                va="center",
                fontsize=9)


def plot_training_process(training_job_name:str, include_metrics=['loss']):
    train_metrics_df, validation_metrics_df, hyper_paramters, job_status = get_model_training_process_metrics(training_job_name)
    if train_metrics_df is not None:
        plot_model_customization_training_metrics(training_job_name, train_metrics_df, validation_metrics_df, job_status, hyper_paramters, include_metrics)