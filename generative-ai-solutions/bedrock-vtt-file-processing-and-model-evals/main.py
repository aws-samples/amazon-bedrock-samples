import os
import sys
import yaml
import json
import logging
import papermill as pm
from typing import Dict
from pathlib import Path
from datetime import datetime
from nbformat import NotebookNode

# Setup logging
logging.basicConfig(format='[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Function to get the config file path and use that to read it
def read_config(config_file_path: str) -> Dict:
    if config_file_path is not None:
        logger.info(f"executing the config file found in {config_file_path}...")
        try:
            logger.info(f"loading config from given relative path: {config_file_path}")
            config_content = yaml.safe_load(Path(config_file_path).read_text())
        except Exception as e:
            logger.error(f"error loading config from given path: {e}")
            raise
    else:
        logger.info(f"the provided config'{config_file_path}' is not a valid path or non existant")

    logger.info(f"loaded configuration: {json.dumps(config_content, indent=2)}")
    return config_content

# Function to handle cell outputs
def output_handler(cell: NotebookNode, _):
    if cell.cell_type == 'code':
        for output in cell.get('outputs', []):
            if output.output_type == 'stream':
                print(output.text, end='')


def run_notebooks(config_file: str) -> None:
    # Assume `read_config` function is defined elsewhere to load the config
    config = read_config(config_file)

    current_directory = Path(__file__).parent
    logging.info(f"Current directory is --> {current_directory}")

    output_directory = current_directory / "executed_notebooks"
    if not output_directory.exists():
        output_directory.mkdir()

    for step, execute in config['run_steps'].items():
        if execute:
            notebook_path = current_directory / step
            logging.info(f"Current step file --> {notebook_path.stem}")

            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            output_file = output_directory / f"{notebook_path.stem}_{timestamp}.ipynb"

            try:
                logging.info(f"Executing {notebook_path.name}...")
                logger.info(f"THE STEP BEING EXECUTED NOW: {step}")
                pm.execute_notebook(
                    input_path=str(notebook_path),
                    output_path=str(output_file),
                    kernel_name='python3',
                    parameters={},
                    report_mode=True,  
                    progress_bar=True,
                    stdout_file=None, 
                    stderr_file=None,
                    log_output=True,
                    output_handler=output_handler 
                )
                logger.info(f"STEP EXECUTION COMPLETED: {step}")
            except FileNotFoundError as e:
                logging.error(f"File not found: {e.filename}")
                sys.exit(1)
            except Exception as e:
                logging.error(f"Failed to execute {step}: {str(e)}")
                sys.exit(1)
        else:
            logging.info(f"Skipping {step} as it is not marked for execution")

    logger.info(f"Call transcripts have been chapterized. Titles generated from models can be viewed in the local {config['dir']['metrics']} directory.")


# main function to run all of the notebooks through a single file
def main():

    # config file path location
    current_directory = Path(__file__).parent
    config_file_path: str = os.path.join(current_directory, 'config.yml')

    # config file path being read for step execution
    run_notebooks(config_file_path)    

if __name__ == "__main__":
    main()
