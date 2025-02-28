import argparse
import json

from constants import *
from model_config.models_registry import MODELS
from model_config.input_type import InputType
from exceptions.invalid_row_exception import InvalidRowException
from exceptions.missing_key_exception import MissingKeyException
from exceptions.invalid_type_exception import InvalidTypeException


def validate_system_prompt(row, index):
    """
    Validates the 'system' prompt of a given dataset row.

    Checks whether the 'system' key exists and its value contains exactly one element.

    Args:
        row (dict): The dataset row to validate.
        index (int): The index of the row in the dataset.

    Raises:
        InvalidRowException: If the 'system' array has more than one item.
        MissingKeyException: If the 'system' key or any necessary subkey is missing.
    """
    try:
        if Keys.SYSTEM in row and len(row[Keys.SYSTEM]) > 1:
            row[Keys.SYSTEM][0][Keys.TEXT]
            raise InvalidRowException(
                "The system array should not contain more than 1 element.", index
            )

    except KeyError as e:
        raise MissingKeyException(e, index)
    except TypeError:
        raise InvalidTypeException(index)


def validate_record_count(record_count, dataset_type):
    """
    Validates the record count of the dataset based on its type.

    Train datasets must contain less than or equal to 10k rows.
    Validation datasets must contain less than or equal to 1k rows.

    Args:
        record_count (int): The total number of records in the dataset.
        dataset_type (str): The type of the dataset, either TRAIN or VALIDATION.

    Raises:
        Exception: If the record count exceeds the maximum allowed for the specific dataset type.
    """
    if dataset_type == TRAIN and record_count > MAX_TRAIN_RECORDS:
        raise Exception(
            f"The {dataset_type} dataset contains {record_count} records, which exceeds the maximum allowed limit of {MAX_TRAIN_RECORDS}."
        )

    if dataset_type == VALIDATION and record_count > MAX_VALIDATION_RECORDS:
        raise Exception(
            f"The {dataset_type} dataset contains {record_count} records, which exceeds the maximum allowed limit of {MAX_VALIDATION_RECORDS}."
        )


def validate_converse(row, index):
    """
    Validates the 'messages' within a given dataset row.

    Checks for supported roles and ensures that each row's structure fits the expected pattern for a conversational input.

    Args:
        row (dict): The dataset row to validate.
        index (int): The index of the row in the dataset.

    Raises:
        InvalidRowException: If there are invalid roles, images where they shouldn't be, or multiple images in a single row.
        MissingKeyException: If required keys are missing in the data structure.
    """
    try:
        dialogue = row[Keys.MESSAGES]

        for message in dialogue:
            role = message[Keys.ROLE]
            supported_roles = [member.value for member in list(Roles)]
            if role not in supported_roles:
                raise InvalidRowException(
                    f"The role '{role}' is not supported. Supported roles are: {supported_roles}.",
                    index,
                )

            for content in message[Keys.CONTENT]:
                if Keys.IMAGE in content:
                    if role == Roles.ASSISTANT:
                        raise InvalidRowException(
                            f"A message with the role '{Roles.ASSISTANT}' should not contain any images.",
                            index,
                        )
                    content[Keys.IMAGE][Keys.SOURCE][Keys.S3_LOCATION][Keys.URI]
                else:
                    content[Keys.TEXT]

    except KeyError as e:
        raise MissingKeyException(e, index)
    except TypeError:
        raise InvalidTypeException(index)


def validate_prompt_completion(row, index):
    try:
        row[Keys.PROMPT]
        row[Keys.COMPLETION]
    except KeyError as e:
        raise MissingKeyException(e, index)
    except TypeError:
        raise InvalidTypeException(index)


def main():
    parser = argparse.ArgumentParser(description="A script for dataset validation.")
    parser.add_argument(
        "-d",
        "--dataset-type",
        type=str,
        choices=[TRAIN, VALIDATION],
        required=True,
        help="Specify the dataset type.",
    )
    parser.add_argument(
        "-f",
        "--file-path",
        type=str,
        required=True,
        help="Provide the local path to your JSONL file.",
    )
    parser.add_argument(
        "-m",
        "--model-name",
        type=str,
        choices=list(MODELS.keys()),
        required=True,
        help="Specify the model name.",
    )

    args = parser.parse_args()
    dataset_type, file_path, model_name = (
        args.dataset_type,
        args.file_path,
        args.model_name,
    )

    model = MODELS[model_name]

    with open(file_path, "r") as dataset:
        validate_record_count(sum(1 for _ in dataset), dataset_type)
        dataset.seek(0)
        for index, object in enumerate(dataset):
            row = json.loads(object)
            validate_system_prompt(row, index)
            if model.input_type == InputType.CONVERSE:
                validate_converse(row, index)
            if model.input_type == InputType.PROMPT_COMPLETION:
                validate_prompt_completion(row, index)

    print("Validation complete.")


if __name__ == "__main__":
    main()
