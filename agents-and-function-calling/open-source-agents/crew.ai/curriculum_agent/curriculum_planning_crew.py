from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.memory import LongTermMemory, ShortTermMemory
from crewai.memory.entity.entity_memory import EntityMemory
import crew_helpers
from proj_tools import ProjectTools
from llm_config import MEMORY_EMBEDDER, LLMModels
from logger import CustomLogger

logger = CustomLogger("info_collection_crew").get_logger()
AGENTS_CONFIG_FILE = "config/collection/agents.yaml"
TASKS_CONFIG_FILE = "config/collection/tasks.yaml"
TOOLS = ProjectTools()

@CrewBase
class InfoCollectionCrew():
    crew_name = "information_collection_crew"
    data_dir = f"data_dir/{crew_name}"
    agents_config = AGENTS_CONFIG_FILE
    tasks_config = TASKS_CONFIG_FILE
    
    def __init__(self):
        logger.info(f"Initializing {self.crew_name}")
        logger.info(f"Tasks config file: {self.tasks_config}")
    
    @agent
    def student_demographics(self) -> Agent:
        config = self.agents_config['student_demographics']
        logger.info(f"Creating student_demographics agent with config: {config}")
        return Agent(
            config=config,
            verbose=True,
            llm=LLMModels.get_claude_haiku(),
            function_calling_llm=LLMModels.get_nova_pro(),
            tools=[TOOLS.google_search],
            memory=True
        )
    
    @agent 
    def classroom_environment_specialist(self) -> Agent:
        config = self.agents_config['classroom_environment_specialist']
        logger.info(f"Creating classroom_environment_specialist agent with config: {config}")
        return Agent(
            config=config,
            verbose=True,
            llm=LLMModels.get_claude_haiku(),
            function_calling_llm=LLMModels.get_nova_pro(),
            tools=[TOOLS.ask_questions]
            )
    
    @agent
    def community_liaison(self) -> Agent:
        config = self.agents_config['community_liaison']
        logger.info(f"Creating community_liaison agent with config: {config}")
        return Agent(
            config=config,
            verbose=True,
            llm=LLMModels.get_claude_haiku(),
            function_calling_llm=LLMModels.get_nova_pro(),
            tools=[TOOLS.google_search, TOOLS.google_news_search, TOOLS.ask_questions]
        )
    
    @task
    def research_local_demographics(self) -> Task:
        task_name = 'task_local_demographics_research'
        logger.info(f"Creating task: {task_name}")
        return Task(
            name=task_name,
            config=self.tasks_config[task_name]
        )

    @task
    def evaluate_reading_level(self) -> Task:
        task_name = 'task_reading_level'
        logger.info(f"Creating task: {task_name}")
        return Task(
            name=task_name,
            config=self.tasks_config[task_name]
        )

    @task
    def identify_special_needs(self) -> Task:
        task_name = 'task_special_needs'
        logger.info(f"Creating task: {task_name}")
        return Task(
            name=task_name,
            config=self.tasks_config[task_name]
        )

    @task
    def get_available_resources(self) -> Task:
        task_name = 'task_available_resources'
        logger.info(f"Creating task: {task_name}")
        return Task(
            name=task_name,
            config=self.tasks_config[task_name]
        )
    
    @task
    def get_room_layout(self) -> Task:
        task_name = 'task_room_layout'
        logger.info(f"Creating task: {task_name}")
        return Task(
            name=task_name,
            config=self.tasks_config[task_name]
        )

    @task
    def task_local_news(self) -> Task:
        task_name = 'task_local_news'
        logger.info(f"Creating task: {task_name}")
        return Task(
            name=task_name,
            config=self.tasks_config[task_name]
        )

    @task
    def task_school_news(self) -> Task:
        task_name = 'task_school_news'
        logger.info(f"Creating task: {task_name}")
        return Task(
            name=task_name,
            config=self.tasks_config[task_name]
        )

    @task
    def task_national_news(self) -> Task:
        task_name = 'task_national_news'
        logger.info(f"Creating task: {task_name}")
        return Task(
            name=task_name,
            config=self.tasks_config[task_name]
        )
    
    @crew
    def crew(self) -> Crew:
        logger.info(f"Creating crew: {self.crew_name}")
        crew = Crew(
            name=self.crew_name,
            agents=[
                self.student_demographics(),
                self.classroom_environment_specialist(),
                self.community_liaison(),
            ],
            tasks=[
                self.research_local_demographics(),
                self.evaluate_reading_level(),
                self.identify_special_needs(),
                self.get_available_resources(),
                self.get_room_layout(),
                self.task_local_news(),
                self.task_school_news(),
                self.task_national_news()
            ],
            process=Process.sequential,
            max_rpm=crew_helpers.AGENT_RPM,
            full_output=True,
            max_iter=2,
            cache=True,
            memory=True,
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
        logger.info("Crew created successfully")
        return crew