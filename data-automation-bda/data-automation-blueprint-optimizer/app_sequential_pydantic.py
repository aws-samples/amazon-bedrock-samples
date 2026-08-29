"""
Sequential BDA optimization with field-by-field strategy selection.
Version: 3.0.0 (Pydantic-based with LLM instruction generation)
"""
import argparse
import sys
import os
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.optimizer import SequentialOptimizer

# Configure logging
def setup_logging():
    """
    Set up logging to both console and file.
    """
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Generate timestamp for log file
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    log_file = f'logs/optimizer-{timestamp}.log'
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_format)
    
    # Create file handler
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    
    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    return log_file


def main():
    """
    Main entry point for the sequential optimization application.
    """
    # Set up logging
    log_file = setup_logging()
    logger = logging.getLogger(__name__)
    
    parser = argparse.ArgumentParser(description='Sequential BDA Optimization')
    parser.add_argument('json_file', help='Path to JSON input file')
    parser.add_argument('--threshold', type=float, help='Threshold for field-level semantic similarity', default=0.8)
    parser.add_argument('--use-doc', action='store_true', help='Whether to use the input source document as a fallback strategy', dest='doc')
    parser.add_argument('--use-template', action='store_true', help='Whether to use template-based instruction generation (default is LLM-based)', dest='template')
    parser.add_argument('--model', type=str, help='LLM model to use for instruction generation', default='anthropic.claude-3-7-sonnet-20250219-v1:0')
    parser.add_argument('--max-iterations', type=int, help='Maximum number of iterations', default=5, dest='max_iterations')
    args = parser.parse_args()
    
    approach = "Template-Based" if args.template else "LLM-Based"
    logger.info(f"\n🔄 Sequential {approach} BDA Optimization (Pydantic Version)")
    logger.info("=" * 70)
    logger.info(f"Logs are being written to: {log_file}")
    
    try:
        # Create optimizer
        optimizer = SequentialOptimizer.from_config_file(
            config_file=args.json_file,
            threshold=args.threshold,
            use_doc=args.doc,
            use_template=args.template,
            model_choice=args.model,
            max_iterations=args.max_iterations
        )
        
        # Run optimization
        final_report_path = optimizer.run(max_iterations=args.max_iterations)
        
        if final_report_path:
            logger.info(f"\n✅ Optimization completed successfully. Final report: {final_report_path}")
            return 0
        else:
            logger.error("\n❌ Optimization failed.")
            return 1
            
    except Exception as e:
        logger.error(f"\n❌ Error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    exit(main())
