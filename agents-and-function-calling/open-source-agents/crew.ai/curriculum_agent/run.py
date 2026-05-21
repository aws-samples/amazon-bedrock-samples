import sys
import json
from datetime import datetime, timezone
import crew_helpers
from info_collection_crew import InfoCollectionCrew
from curriculum_planning_crew import CurriculumPlanningCrew
import traceback

def load_student_info(json_file):
    try:
        with open(json_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find {json_file}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {json_file}")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: python run.py <json_file_path>")
        print("Example: python run.py examples/student_info.json")
        sys.exit(1)

    json_file_path = sys.argv[1]

    base_student_info = load_student_info(json_file_path)
    
    inputs = {
        **base_student_info,
        "current_date": datetime.now().strftime("%A, %B %d, %Y")
    }
    print("inputs", inputs)
    
    try:
        info_crew = InfoCollectionCrew().crew()
        info_crew_result = info_crew.kickoff(inputs=inputs)
        
        print("InfoCollectionCrew Results:")
        print(info_crew_result)

        # build dict for inputs to cirriculum planning
        collected_info = crew_helpers.task_summary(crew_output=info_crew_result)

        cirriculum_planning_crew = CurriculumPlanningCrew().crew()
        curriculum_planning_crew_result = cirriculum_planning_crew.kickoff(inputs={**inputs, "background": collected_info})

        print("CirriculumPlanningCrew Results:")
        print(curriculum_planning_crew_result)

    except Exception as e:
        print("\n=== Error Details ===")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print("\n=== Full Traceback ===")
        traceback.print_exc()
        print("\n=== Additional Context ===")
        print(f"Python Version: {sys.version}")
        print(f"Current File: {__file__}")
if __name__ == "__main__":
    main()