from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.memory import LongTermMemory, ShortTermMemory
from crewai.memory.entity.entity_memory import EntityMemory
import crew_helpers
from proj_tools import ProjectTools
from llm_config import MEMORY_EMBEDDER, LLMModels
from logger import CustomLogger 

# variables
AGENTS_CONFIG_FILE = "config/planning/agents.yaml"
TASKS_CONFIG_FILE = "config/planning/tasks.yaml"
TOOLS = ProjectTools()
CREW_NAME = "Curriculum_planning_crew"

# initialize logger
logger = CustomLogger(CREW_NAME).get_logger()

@CrewBase
class CurriculumPlanningCrew():
    """Curriculum Planning Crew"""
    crew_name = CREW_NAME
    data_dir = f"data_dir/{crew_name}"
    agents_config = AGENTS_CONFIG_FILE
    tasks_config = TASKS_CONFIG_FILE

    def __init__(self):
        logger.info(f"Initializing {self.crew_name}")
        logger.info(f"Tasks config file: {self.tasks_config}")
    
    @agent
    def desired_results(self) -> Agent:
        config = self.agents_config['desired_results']
        return Agent(
            config=config,
            verbose=True,
            step_callback=crew_helpers._step_callback,
            llm=LLMModels.get_claude_sonnet(),
            function_calling_llm=LLMModels.get_nova_pro(),
            tools=[
                TOOLS.google_search, 
                ]
        )
    
    @agent
    def evidence_and_assessment(self) -> Agent:
        config = self.agents_config['evidence_and_assessment']
        return Agent(
            config=config,
            verbose=True,
            step_callback=crew_helpers._step_callback,
            llm=LLMModels.get_claude_sonnet(),
            function_calling_llm=LLMModels.get_nova_pro(),
            memory=True,
            full_output=True,
            tools=[
                TOOLS.google_search, 
                # TOOLS.student_demographics_search # doesn't support bedrock yet
                ]
            )
    
    @agent
    def learning_plan(self) -> Agent:
        config = self.agents_config['learning_plan']
        return Agent(
            config=config,
            verbose=True,
            step_callback=crew_helpers._step_callback,
            llm=LLMModels.get_claude_sonnet(),
            function_calling_llm=LLMModels.get_nova_pro(),
            memory=True,
            full_output=True,
            tools=[
                TOOLS.google_search, 
                # TOOLS.student_demographics_search # doesn't support bedrock yet
                ]
        )
    
    @task
    def task_transfer_learning(self) -> Task:
        task_name = 'task_transfer_learning'
        return Task(
            name=task_name,
            config=self.tasks_config[task_name]
        )

    @task
    def task_understandings(self) -> Task:
        task_name = 'task_understandings'
        return Task(
            name=task_name,
            config=self.tasks_config[task_name]
        )

    @task
    def task_essential_questions(self) -> Task:
        task_name = 'task_essential_questions'
        return Task(
            name=task_name,
            config=self.tasks_config[task_name]
        )

    @task
    def task_acquired_knowledge(self) -> Task:
        task_name = 'task_acquired_knowledge'
        return Task(
            name=task_name,
            config=self.tasks_config[task_name]
        )
    
    @task
    def task_acquired_skills(self) -> Task:
        task_name = 'task_acquired_skills'
        return Task(
            name=task_name,
            config=self.tasks_config[task_name]
        )

    @task
    def task_evaluative_criteria(self) -> Task:
        task_name = 'task_evaluative_criteria'
        return Task(
            name=task_name,
            config=self.tasks_config[task_name]
        )

    @task
    def task_performance_tasks(self) -> Task:
        task_name = 'task_performance_tasks'
        return Task(
            name=task_name,
            config=self.tasks_config[task_name]
        )

    @task
    def task_other_evidence(self) -> Task:
        task_name = 'task_other_evidence'
        return Task(
            name=task_name,
            config=self.tasks_config[task_name]
        )
    
    @task
    def task_learning_sequence(self) -> Task:
        task_name = 'task_learning_sequence'
        return Task(
            name=task_name,
            config=self.tasks_config[task_name]
        )

    @task
    def task_instructional_strategies(self) -> Task:
        task_name = 'task_instructional_strategies'
        return Task(
            name=task_name,
            config=self.tasks_config[task_name]
        )
    
    @crew
    def crew(self) -> Crew:
        crew = Crew(
            name=self.crew_name,
            agents=[
                self.desired_results(),
                self.evidence_and_assessment()
            ],
            tasks=[
                self.task_transfer_learning(),
                self.task_understandings(),
                self.task_essential_questions(),
                self.task_acquired_knowledge(),
                self.task_acquired_skills(),
                self.task_evaluative_criteria(),
                self.task_performance_tasks(),
                self.task_other_evidence()
            ],
            process=Process.sequential,
            # step_callback=crew_helpers._step_callback,
            max_rpm=crew_helpers.AGENT_RPM,
            max_iter=2,
            cache=True,
            # verbose=True,
            memory=True,
            full_output=True,
            long_term_memory=LongTermMemory(path=crew_helpers.ensure_dir_path(f"{self.data_dir}/long_term_memory_storage/") + "lts.db"),
            short_term_memory=ShortTermMemory(
                path=crew_helpers.ensure_dir_path(f"{self.data_dir}/short_term_memory_storage/"),
                embedder_config=MEMORY_EMBEDDER,
            ),
            entity_memory=EntityMemory(
                path=crew_helpers.ensure_dir_path(f"{self.data_dir}/entity_memory_storage/"),
                embedder_config=MEMORY_EMBEDDER,
            ),
        )
        logger.info(f"Successfully created crew: {self.crew_name}")
        return crew