# Copyright 2021 Amazon.com and its affiliates; all rights reserved. 
# This file is AWS Content and may not be duplicated or distributed without permission
"""This module contains a helper class for building and using Agents for Amazon Bedrock. 
The AgentsForAmazonBedrock class provides a convenient interface for working with Agents.
It includes methods for creating, updating, and invoking Agents, as well as managing 
IAM roles and Lambda functions for action groups. Here is a quick example of using
the class:

    >>> from agent import AgentsForAmazonBedrock
    >>> agents = AgentsForAmazonBedrock()
    >>> name = "my_agent"
    >>> descr = "my agent description"
    >>> instructions = "you are an agent that ..."
    >>> model_id = "...haiku..."
    >>> agent_id = agents.create_agent(name, descr, instructions, model_id)
    >>>
    >>> action_group_name = "my_action_group"
    >>> action_group_descr = "my action group description"
    >>> lambda_code = "my_lambda.py"
    >>> function_defs = [{ ... }]
    >>> action_group_arn = agents.add_action_group_with_lambda(agent_id,
                                         lambda_function_name, lambda_code, 
                                         function_defs, action_group_name, action_group_descr)
    >>> agents.simple_agent_invoke("when's my next payment due?", agent_id)

Here is a summary of the most important methods:

- create_agent: Creates a new Agent.
- add_action_group_with_lambda: Creates a new Action Group for an Agent, backed by Lambda.
- simple_invoke_agent: Invokes an Agent with a given input.
"""

import boto3
import json 
import time
import uuid
import zipfile
from io import BytesIO
from typing import List, Dict
from boto3.session import Session

PYTHON_TIMEOUT = 180
PYTHON_RUNTIME = 'python3.12'
DEFAULT_ALIAS = "TSTALIASID"

# # setting logger
# logging.basicConfig(format='[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s', level=logging.INFO)
# logger = logging.getLogger(__name__)

class AgentsForAmazonBedrock:
    """Provides an easy to use wrapper for Agents for Amazon Bedrock.
    """

    def __init__(self):
        """Constructs an instance."""
        self._boto_session = Session() 
        self._region = self._boto_session.region_name
        self._account_id = boto3.client("sts").get_caller_identity()["Account"]
        
        self._bedrock_agent_client = boto3.client('bedrock-agent')
        self._bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')

        self._sts_client = boto3.client('sts')
        self._iam_client = boto3.client('iam')
        self._lambda_client = boto3.client('lambda')
        self._s3_client = boto3.client('s3', region_name=self._region)

        self._suffix = f"{self._region}-{self._account_id}"

    def get_region(self) -> str:
        """Returns the region for this instance."""
        return self._region
    
    def _create_lambda_iam_role(self, agent_name: str,
                                sub_agent_arns: List[str]=None, 
                                dynamodb_table_name: str=None) -> object:
        """Creates an IAM role for a Lambda function built to implement an Action Group for an Agent.
        
        Args:
            agent_name (str): Name of the agent for which this Lambda supports, will be used as part of the role name
            sub_agent_arns (List[str], optional): List of sub-agent ARNs to allow this Lambda to invoke. Defaults to [].
            dynamodb_table_name (str, optional): Name of the DynamoDB table to that can be accessed by this Lambda. Defaults to None.

        Returns:
            str: ARN of the new IAM role, to be used when creating a Lambda function
        """
        _lambda_function_role_name = f'{agent_name}-lambda-role-{self._suffix}'
        _dynamodb_access_policy_name = f'{agent_name}-dynamodb-policy'

        # Create IAM Role for the Lambda function
        try:
            _assume_role_policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": "bedrock:InvokeModel",
                        "Principal": {
                            "Service": "lambda.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            }

            _assume_role_policy_document_json = json.dumps(_assume_role_policy_document)

            _lambda_iam_role = self._iam_client.create_role(
                RoleName=_lambda_function_role_name,
                AssumeRolePolicyDocument=_assume_role_policy_document_json
            )

            # Pause to make sure role is created
            time.sleep(10)
        except:
            _lambda_iam_role = self._iam_client.get_role(RoleName=_lambda_function_role_name)

        # attach Lambda basic execution policy to the role
        self._iam_client.attach_role_policy(
            RoleName=_lambda_function_role_name,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        )

        # create a policy to allow Lambda to invoke sub-agents and look up info about each sub-agent.
        # include the ability to invoke the agent based on its ID, and allow use of any Agent Alias.
        if sub_agent_arns is not None:
            _tmp_resources = [_sub_agent_arn.replace(':agent/', ':agent*/') + '*' 
                              for _sub_agent_arn in sub_agent_arns]
            _sub_agent_policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "AmazonBedrockAgentInvokeSubAgentPolicy",
                        "Effect": "Allow",
                        "Action": "bedrock:InvokeAgent",
                        "Resource": _tmp_resources
                    },
                    {
                        "Sid": "AmazonBedrockAgentGetAgentPolicy",
                        "Effect": "Allow",
                        "Action": "bedrock:GetAgent",
                        "Resource": [_sub_agent_arn for _sub_agent_arn in sub_agent_arns]
                    }
                ]
            }
            # Attach the inline policy to the Lambda function's role
            sub_agent_policy_json = json.dumps(_sub_agent_policy_document)
            self._iam_client.put_role_policy(
                PolicyDocument=sub_agent_policy_json,
                PolicyName="sub_agent_policy",
                RoleName=_lambda_function_role_name
            )

        # Create a policy to grant access to the DynamoDB table
        if dynamodb_table_name:
            _dynamodb_access_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "dynamodb:GetItem",
                            "dynamodb:PutItem",
                            "dynamodb:DeleteItem"
                        ],
                        "Resource": "arn:aws:dynamodb:{}:{}:table/{}".format(
                            self._region, self._account_id, dynamodb_table_name
                        )
                    }
                ]
            }

            # Attach the inline policy to the Lambda function's role
            _dynamodb_access_policy_json = json.dumps(_dynamodb_access_policy)
            self._iam_client.put_role_policy(
                PolicyDocument=_dynamodb_access_policy_json,
                PolicyName=_dynamodb_access_policy_name,
                RoleName=_lambda_function_role_name
            )
        return _lambda_iam_role['Role']['Arn']
    
    def get_agent_id_by_name(self, agent_name: str) -> str:
        """Gets the Agent ID for the specified Agent.

        Args:
            agent_name (str): Name of the agent whose ID is to be returned

        Returns:
            str: Agent ID, or None if not found
        """
        _get_agents_resp = self._bedrock_agent_client.list_agents(maxResults=100) 
        _agents_json = _get_agents_resp['agentSummaries']
        _target_agent = next((agent for agent in _agents_json if agent["agentName"] == agent_name), None)
        if _target_agent is None:
            return None
        else:
            return _target_agent['agentId']
        
    def associate_kb_with_agent(self, agent_id, description, kb_id):
        """Associates a Knowledge Base with an Agent, and prepares the agent.

        Args:
            agent_id (str): Id of the agent
            description (str): Description of the KB
            kb_id (str): Id of the KB
        """
        _resp = self._bedrock_agent_client.associate_agent_knowledge_base(
            agentId=agent_id,
            agentVersion='DRAFT',
            description=description,
            knowledgeBaseId=kb_id,
            knowledgeBaseState='ENABLED'
        )
        _resp = self._bedrock_agent_client.prepare_agent(
            agentId=agent_id
        )

    def get_agent_arn_by_name(self, agent_name: str) -> str:
        """Gets the Agent ARN for the specified Agent.

        Args:
            agent_name (str): Name of the agent whose ARN is to be returned

        Returns:
            str: Agent ARN, or None if not found
        """
        _agent_id = self.get_agent_id_by_name(agent_name)
        if _agent_id is None:
            raise ValueError(f"Agent {agent_name} not found")
        _get_agent_resp = self._bedrock_agent_client.get_agent(agentId=_agent_id)
        return _get_agent_resp['agent']['agentArn']
            
    def get_agent_instructions_by_name(self, agent_name: str) -> str:
        """Gets the current Agent Instructions that are used by the specified Agent.

        Args:
            agent_name (str): Name of the agent whose Instructions are to be returned

        Returns:
            str: Agent ARN, or None if not found
        """
        _agent_id = self.get_agent_id_by_name(agent_name)
        if _agent_id is None:
            raise ValueError(f"Agent {agent_name} not found")
        _get_agent_resp = self._bedrock_agent_client.get_agent(agentId=_agent_id)

        # extract the instructions from the response
        _instructions = _get_agent_resp['agent']['instruction']
        return _instructions
    
    def _allow_agent_lambda(self, 
                           agent_id: str,
                           lambda_function_name: str) -> None:
        """Allows the specified Agent to invoke the specified Lambda function by adding the appropriate permission.

        Args:
            agent_id (str): Id of the agent
            lambda_function_name (str): Name of the Lambda function
        """
        # Create allow invoke permission on lambda
        _permission_resp = self._lambda_client.add_permission(
            FunctionName=lambda_function_name,
            StatementId=f'allow_bedrock_{agent_id}',
            Action='lambda:InvokeFunction',
            Principal='bedrock.amazonaws.com',
            SourceArn=f"arn:aws:bedrock:{self._region}:{self._account_id}:agent/{agent_id}",
        )

    def _make_agent_string(self,
                           agent_arns: List[str]=None) -> str:
        """Makes a comma separated string of agent ids from a list of agent ARNs.

        Args:
            agent_arns (List[str]): List of agent ARNs
        """
        if agent_arns is None:
            return ""
        else:
            _agent_string = ""
            for _agent_arn in agent_arns:
                _agent_string += _agent_arn.split("/")[1] + ","
            return _agent_string.strip()[:-1]

    def create_lambda(self, 
                      agent_name: str,
                      lambda_function_name: str, 
                      source_code_file: str,
                      sub_agent_arns: List[str]) -> str:
        """Creates a new Lambda function that implements a set of actions for an Agent Action Group.
        
        Args:
            agent_name (str): Name of the existing Agent that this Lambda will support.
            lambda_function_name (str): Name of the Lambda function to create.
            source_code_file (str): Name of the file containing the Lambda source code. 
            Must be a local file, and use underscores, not hyphens.
            sub_agent_arns (List[str]): List of ARNs of the sub-agents that this Lambda is allowed to invoke.
            
        Returns:
            str: ARN of the new Lambda function
        """

        _agent_id = self.get_agent_id_by_name(agent_name)
        if _agent_id is None:
            return "Agent not found"
        
        _base_filename = source_code_file.split('.py')[0]

        # Package up the lambda function code
        s = BytesIO()
        z = zipfile.ZipFile(s, 'w')
        z.write(f"{source_code_file}")
        z.close()
        zip_content = s.getvalue()

        # Create Lambda Function
        _lambda_function = self._lambda_client.create_function(
            FunctionName=lambda_function_name,
            Runtime=PYTHON_RUNTIME,
            Timeout=PYTHON_TIMEOUT,
            Role=self._create_lambda_iam_role(agent_name, sub_agent_arns),
            Code={'ZipFile': zip_content},
            Handler=f"{_base_filename}.lambda_handler",
            # TODO: make this an optional keyword arg. only supply it when sub-agent-arns are provided
            Environment={
                'Variables': {
                    'SUB_AGENT_IDS': self._make_agent_string(sub_agent_arns)
                }
            }
        )

        self._allow_agent_lambda(_agent_id, lambda_function_name)

        return _lambda_function['FunctionArn']
    
    def delete_lambda(self, 
                      lambda_function_name: str,
                      delete_role_flag: bool=True) -> None:
        """Deletes the specified Lambda function.
        Optionally, deletes the IAM role that was created for the Lambda function.
        Optionally, deletes the policy that was created for the Lambda function.

        Args:
            lambda_function_name (str): Name of the Lambda function to delete.
            delete_role_flag (bool, Optional): Flag indicating whether to delete the IAM role that was 
            created for the Lambda function. Defaults to True.
        """

        # Detach and delete the role
        if delete_role_flag:
            try:
                _function_resp = self._lambda_client.get_function(FunctionName=lambda_function_name)
                _role_arn = _function_resp['Configuration']['Role']
                _role_name = _role_arn.split('/')[1]
                self._iam_client.detach_role_policy(RoleName=_role_name, 
                                PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole')
                self._iam_client.delete_role(
                    RoleName=_role_name
                )
            except:
                pass

        # Delete Lambda function
        try:
            self._lambda_client.delete_function(
                FunctionName=lambda_function_name
            )
        except:
            pass

    def get_agent_role(self, agent_name: str) -> str:
        """Gets the ARN of the IAM role that is associated with the specified Agent.

        Args:
            agent_name (str): Name of the Agent

        Returns:
            str: ARN of the IAM role, or None if not found
        """
        _get_agents_resp = self._bedrock_agent_client.list_agents(maxResults=100) 
        _agents_json = _get_agents_resp['agentSummaries']
        _target_agent = next((agent for agent in _agents_json if agent["agentName"] == agent_name), None)
        if _target_agent is not None:
            # pprint.pp(_target_agent)
            _agent_id = _target_agent['agentId']

            _get_agent_resp = self._bedrock_agent_client.get_agent(agentId=_agent_id)
            return _get_agent_resp['agent']['agentResourceRoleArn']
        else:
            return "Agent not found"

    def delete_agent(self, agent_name: str,
                     delete_role_flag: bool=True) -> None:
        """Deletes an existing agent. Optionally, deletes the IAM role associated with the agent.
        
        Args:
            agent_name (str): Name of the agent to delete.
            delete_role_flag (bool, Optional): Flag indicating whether to delete the IAM role associated with the agent.
            Defaults to True.
        """

        # first find the agent ID from the agent Name
        _get_agents_resp = self._bedrock_agent_client.list_agents(maxResults=100)
        _agents_json = _get_agents_resp['agentSummaries']
        _target_agent = next((agent for agent in _agents_json if agent["agentName"] == agent_name), None)

        # TODO: add delete_lambda_flag parameter to optionall take care of
        # deleting the lambda function associated with the agent.

        # delete Agent IAM role if desired
        if delete_role_flag:
            _agent_role_name = f'AmazonBedrockExecutionRoleForAgents_{agent_name}'

            try:
                self._iam_client.delete_role_policy(
                    PolicyName="bedrock_gr_allow_policy", 
                    RoleName=_agent_role_name
                )
            except Exception as e:
                # print(f'Error when deleting bedrock_kb_allow_policy from role: {_agent_role_name}\n{e}')
                pass

            try:
                self._iam_client.delete_role_policy(
                    PolicyName="bedrock_allow_policy", 
                    RoleName=_agent_role_name
                )
            except Exception as e:
                print(f'Error when deleting bedrock_allow_policy from role: {_agent_role_name}\n{e}')
                pass

            try:
                self._iam_client.delete_role_policy(
                    PolicyName="bedrock_kb_allow_policy", 
                    RoleName=_agent_role_name
                )
            except Exception as e:
                # print(f'Error when deleting bedrock_kb_allow_policy from role: {_agent_role_name}\n{e}')
                pass

            try:
                self._iam_client.delete_role(
                    RoleName=_agent_role_name
                )
            except Exception as e:
                print(f'Error when deleting role: {_agent_role_name} from agent: {agent_name}\n{e}')
                pass

        # if the agent exists, delete the agent
        if _target_agent is not None:
            # pprint.pp(_target_agent)
            _agent_id = _target_agent['agentId']


            self._bedrock_agent_client.delete_agent(
                agentId=_agent_id
                )
        
    def _create_agent_role(self, 
                             agent_name: str,
                             agent_foundation_models: List[str],
                             kb_arns: List[str]=None) -> str:
        """Creates an IAM role for an agent.
        
        Args:
            agent_name (str): name of the agent for this new role
            agent_foundation_models (List[str]): List of IDs or Arn's of the Bedrock foundation model(s) this agent is allowed to use
            kb_arns (List[str], Optional): List of ARNs of the Knowledge Base(s) this agent is allowed to use
        
        Returns:
            str: the Arn for the new role
        """

        _agent_role_name = f'AmazonBedrockExecutionRoleForAgents_{agent_name}'
        _tmp_resources = [f"arn:aws:bedrock:{self._region}::foundation-model/{_model}" for _model in agent_foundation_models]

        # Create IAM policies for agent
        _bedrock_agent_bedrock_allow_policy_statement = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AmazonBedrockAgentBedrockFoundationModelPolicy",
                    "Effect": "Allow",
                    "Action": "bedrock:InvokeModel",
                    "Resource": _tmp_resources
                }
            ]
        }

        _bedrock_policy_json = json.dumps(_bedrock_agent_bedrock_allow_policy_statement)
        _assume_role_policy_document = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }]
        }

        _assume_role_policy_document_json = json.dumps(_assume_role_policy_document)
        _agent_role = self._iam_client.create_role(
            RoleName=_agent_role_name,
            AssumeRolePolicyDocument=_assume_role_policy_document_json
        )

        # add Knowledge Base retrieve and retrieve and generate permissions if agent has KB attached to it
        if kb_arns is not None:
            _kb_policy_doc = {
                "Version": "2012-10-17",
                "Statement": [{
                    "Sid": "QueryKB",
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:Retrieve",
                        "bedrock:RetrieveAndGenerate"
                    ],
                    "Resource": kb_arns
                }]
            }
            _kb_policy_json = json.dumps(_kb_policy_doc)
            self._iam_client.put_role_policy(
                PolicyDocument=_kb_policy_json,
                PolicyName="bedrock_kb_allow_policy",
                RoleName=_agent_role_name
            )

            # Support Guardrail access
            _gr_policy_doc = {
                "Version": "2012-10-17",
                "Statement": [{
                    "Sid": "AmazonBedrockAgentBedrockInvokeGuardrailModelPolicy",
                        "Effect": "Allow",
                        "Action": [
                            "bedrock:InvokeModel",
                            "bedrock:GetGuardrail",
                            "bedrock:ApplyGuardrail"
                        ],
                        "Resource": f"arn:aws:bedrock:*:{self._account_id}:guardrail/*"
                            # TODO: scope this down to a single GR passed as param
                    }]
            }
            _gr_policy_json = json.dumps(_gr_policy_doc)
            self._iam_client.put_role_policy(
                PolicyDocument=_gr_policy_json,
                PolicyName="bedrock_gr_allow_policy",
                RoleName=_agent_role_name
            )
        
        # Pause to make sure role is created
        time.sleep(5)
            
        self._iam_client.put_role_policy(
            PolicyDocument=_bedrock_policy_json,
            PolicyName="bedrock_allow_policy",
            RoleName=_agent_role_name
        )

        return _agent_role['Role']['Arn']

    def create_agent(self,
                     agent_name: str,
                     agent_description: str,
                     agent_instructions: str,
                     model_ids: List[str],
                     kb_arns: List[str]=None) -> str:
        """Creates an agent given a name, instructions, model, description, and optionally
        a set of knowledge bases. Action groups are added to the agent as a separate 
        step once you have created the agent itself.

        Args:
            agent_name (str): name of the agent
            agent_description (str): description of the agent
            agent_instructions (str): instructions for the agent
            model_ids (List[str]): IDs of the foundation models this agent is allowed to use, the first one will be used
            to create the agent, and the others will also be captured in the agent IAM role for future use
            kb_arns (List[str], Optional): ARNs of the Knowledge Base(s) this agent is allowed to use
        
        Returns:
            str: agent ID
        """
        
        _role_arn = self._create_agent_role(agent_name, model_ids, kb_arns)

        response = self._bedrock_agent_client.create_agent(
                        agentName=agent_name,
                        agentResourceRoleArn=_role_arn,
                        description=agent_description.replace('\n', ''), # console doesn't like newlines for subsequent editing
                        idleSessionTTLInSeconds=1800,
                        foundationModel=model_ids[0],
                        instruction=agent_instructions,
                    )
        time.sleep(5)
        return response['agent']['agentId']
    
    def add_action_group_with_lambda(self,
                                     agent_name: str,
                                     lambda_function_name: str, 
                                     source_code_file: str,
                                     agent_functions: List[Dict], 
                                     agent_action_group_name: str, 
                                     agent_action_group_description: str,
                                     sub_agent_arns: List[str]=None) -> None:
        """Adds an action group to an existing agent, creates a Lambda function to 
        implement that action group, and prepares the agent so it is ready to be
        invoked.
        
        Args:
            agent_name (str): name of the existing agent
            lambda_function_name (str): name of the Lambda function to create
            source_code_file (str): path to the source code file for the new Lambda function
            agent_functions (List[Dict]): list of agent function descriptions to implement in the action group
            agent_action_group_name (str): name of the agent action group
            agent_action_group_description (str): description of the agent action group
            sub_agent_arns (List[str], Optional): list of ARNs of sub-agents (if any) to permit the Lambda to invoke
        """
           
        _agent_id = self.get_agent_id_by_name(agent_name)
        if _agent_id is None:
            return "Agent not found"
        
        _lambda_arn = self.create_lambda(agent_name, 
                                         lambda_function_name, 
                                         source_code_file,
                                         sub_agent_arns)
        _agent_action_group_resp = self._bedrock_agent_client.create_agent_action_group(
                agentId=_agent_id,
                agentVersion='DRAFT',
                actionGroupExecutor={'lambda': _lambda_arn},
                actionGroupName=agent_action_group_name,
                functionSchema={'functions': agent_functions},
                description=agent_action_group_description
                )
        _resp = self._bedrock_agent_client.prepare_agent(
               agentId=_agent_id
            )
        time.sleep(5) # make sure agent is ready to be invoked as soon as we return
        return
        
    def add_action_group_with_roc(self,
            agent_id: str, 
            agent_functions: List[Dict], 
            agent_action_group_name: str, 
            agent_action_group_description: str=None) -> None:
        """Adds a return of control (ROD) action group to an existing agent, 
        and prepares the agent so it is ready to be invoked.

        Args:
            agent_id (str): ID of the existing agent
            agent_functions (List[Dict]): list of agent function descriptions to implement in the action group
            agent_action_group_name (str): name of the agent action group
            agent_action_group_description (str, Optional): description of the agent action group
        """
           
        _agent_action_group_resp = self._bedrock_agent_client.create_agent_action_group(
                agentId=agent_id,
                agentVersion='DRAFT',
                actionGroupExecutor={'customControl': 'RETURN_CONTROL'},
                actionGroupName=agent_action_group_name,
                functionSchema={'functions': agent_functions},
                description=agent_action_group_description
                )
        _resp = self._bedrock_agent_client.prepare_agent(
               agentId=agent_id
            )
        time.sleep(5) # make sure agent is ready to be invoked as soon as we return
        return
    
    def get_function_defs(self, agent_name: str) -> List[dict]:
        """Returns the function definitions for an agent.

        Args:
            agent_name (str): The name of the agent.

        Returns:
            List[dict]: A list of function definitions.
        """
        # "sub-agents-ag"
        _agent_id = self.get_agent_id_by_name(agent_name)
        if _agent_id is None:
            raise ValueError(f"Agent {agent_name} not found")
        _list_resp = self._bedrock_agent_client.list_agent_action_groups(agentId=_agent_id,
                                                                         agentVersion="DRAFT")
        # TODO: don't assume there's only a single action group, and
        # handle case where no action groups exist
        _action_group_id = _list_resp['actionGroupSummaries'][0]['actionGroupId']
        _get_ag_resp = self._bedrock_agent_client.get_agent_action_group(agentId=_agent_id,
                                                                         actionGroupId=_action_group_id,
                                                                         agentVersion="DRAFT")
        return _get_ag_resp['agentActionGroup']['functionSchema']

    def create_supervisor_agent(self, supervisor_agent_name: str, 
                      sub_agent_names: List[str], 
                      model_ids: List[str],
                      kb_arns: List[str]=None) -> tuple[List[dict], str]:
        """Creates a supervisor agent that takes in user input and delegates the work to one of its
        available sub-agents. For each sub-agent, the supervisor agent has a distinct action in its action group.
        A supervisor Lambda function implements the pass-through logic to invoke the chosen sub-agent.

        Args:
            supervisor_agent_name (str): The name of the new supervisor agent.
            sub_agent_names (List[str]): A list of named sub-agents that this supervisor agent uses to get its work done.
            model_ids (List[str]): IDs of the foundation models this supervisor agent is allowed to use, 
            the first one will be used to create the agent, and the others will also be captured in the 
            agent IAM role for future use in case you update the agent to switch LLMs.
            kb_arns (List[str], Optional): A list of knowledge base IDs that the supervisor can use, if any.

        Returns:
            tuple[List[dict], str]: A tuple containing a list of function definitions and the ARN of the new agent.
        """

        supervisor_instructions = """You are a Supervisor Agent that plans and executes multi step tasks based on user input.
        To accomplish those tasks, you delegate your work to a sub-agent, but you never reveal to the user that you are using sub-agents.
        Pretend that you are handling all the requests directly. 
        note that a sub-agent may be capable of asking for specific additional info, so don't feel obligated to ask the user for 
        input before you delegate work to a sub-agent. if a sub-agent is asking for additional information, 
        ask the user for that, but do not reveal that you are using a sub-agent. for example, if any sub-agent asks 
        for a customer id, just ask the user for the customer id without saying that the sub-agent asked for it.
        Here is your list of sub-agents: """ 
        supervisor_description = """You are a Supervisor Agent that plans and executes multi step tasks based on user input.
        To accomplish those tasks, you delegate your work to a sub-agent or knowledge base.""" 

        _agent_idx = 0
        _function_defs = []
        _sub_agent_arns = []

        for _agent_name in sub_agent_names:
            _agent_id = self.get_agent_id_by_name(_agent_name)
            _agent_details = self._bedrock_agent_client.get_agent(agentId = _agent_id)['agent']
            _sub_agent_arns.append(_agent_details['agentArn'])
            if 'description' in _agent_details:
                _descr = _agent_details['description']
            else:
                _descr = ""

            # create function definition for each sub agent, allowing the supervisor agent
            # to know what expert agents it has available.

            _function_defs.append({
                "name": f"invoke-{_agent_name}",
                "description": _descr,
                "parameters": {
                    "input_text": {
                        "description": "The text to be processed by the agent.",
                        "type": "string",
                        "required": True
                    }
                }})

            if _agent_idx != 0:
                supervisor_instructions += f", {_agent_name}"
            else:
                supervisor_instructions += f"{_agent_name}"
            _agent_idx += 1
            supervisor_instructions += "."

        if kb_arns is not None:
            supervisor_instructions += ". You also can take advantage of your available knowledge bases."

        _supervisor_role_arn = self._create_agent_role(supervisor_agent_name, model_ids, kb_arns)

        _response = self._bedrock_agent_client.create_agent(
            agentName=supervisor_agent_name,
            agentResourceRoleArn=_supervisor_role_arn,
            description=supervisor_description.replace('\n', ''), # console doesn't like newlines for subsequent editing
            idleSessionTTLInSeconds=1800,
            foundationModel=model_ids[0],
            instruction=supervisor_instructions
        )
        _agent_arn = _response['agent']['agentArn']
        time.sleep(5)

        self.add_action_group_with_lambda( supervisor_agent_name,
                                     f'{supervisor_agent_name}_lambda', 
                                     "supervisor_agent_function.py",
                                     _function_defs,
                                     "sub-agents-ag", 
                                     "set of actions that invoke sub-agents",
                                     _sub_agent_arns)
        return _function_defs, _agent_arn
    
    def invoke(self,
                input_text: str, 
                agent_id: str, 
                agent_alias_id: str="TSTALIASID", 
                session_id: str=str(uuid.uuid1()), 
                session_state: dict={},
                enable_trace: bool=False, 
                end_session: bool=False):
        """Invokes an agent with a given input text, while optional parameters
        also let you leverage an agent session, or target a specific agent alias.

        Args:
            input_text (str): The text to be processed by the agent.
            agent_id (str): The ID of the agent to invoke.
            agent_alias_id (str, optional): The alias ID of the agent to invoke. Defaults to "TSTALIASID".
            session_id (str, optional): The ID of the session. Defaults to a new UUID.
            session_state (dict, optional): The state of the session. Defaults to an empty dict.
            enable_trace (bool, optional): Whether to enable trace. Defaults to False.
            end_session (bool, optional): Whether to end the session. Defaults to False.

        Returns:
            str: The answer from the agent.
        """
        _agent_resp = self._bedrock_agent_runtime_client.invoke_agent(
            inputText=input_text,
            agentId=agent_id,
            agentAliasId=agent_alias_id, 
            sessionId=session_id,
            sessionState=session_state,
            enableTrace=enable_trace, 
            endSession= end_session
        )
        # logger.info(pprint.pprint(agentResponse))
    
        _agent_answer = ""
        _event_stream = _agent_resp['completion']
        try:
            for _event in _event_stream:        
                if 'chunk' in _event:
                    _data = _event['chunk']['bytes']
                    _agent_answer = _data.decode('utf8')
                    _end_event_received = True
                    # End event indicates that the request finished successfully
                elif 'trace' in _event and enable_trace:
                    print(json.dumps(_event['trace'], indent=2))
                elif 'preGuardrailTrace' in _event and enable_trace:
                    print(json.dumps(_event['preGuardrailTrace'], indent=2))
                else:
                    raise Exception("unexpected event.", _event)
            return _agent_answer
        except Exception as e:
            raise Exception("unexpected event.", e)
        
    def simple_agent_invoke_roc(self,
                            input_text: str, 
                            agent_id: str, 
                            agent_alias_id: str=DEFAULT_ALIAS, 
                            session_id: str=str(uuid.uuid1()), 
                            function_call: str=None,
                            function_call_result: str=None,
                            enable_trace: bool=False, 
                            end_session: bool=False):
        """Performs an invoke_agent() call for an agent with an ROC action group. Also used
        for subsequent processing of the function call result from a prior ROC agent call.
 
        Args:
            input_text (str): The text to be processed by the agent.
            agent_id (str): The ID of the agent to invoke.
            agent_alias_id (str, optional): The alias ID of the agent to invoke. Defaults to DEFAULT_ALIAS.
            session_id (str, optional): The ID of the session. Defaults to a new UUID.
            function_call (str, optional): The function call that was made previously. Defaults to None.
            function_call_result (str, optional): The result of the function call that was made previously. Defaults to None.
            enable_trace (bool, optional): Whether to enable trace. Defaults to False.
            end_session (bool, optional): Whether to end the session. Defaults to False.

        Returns:
            str: The answer from the agent.
        """
        if function_call is not None:
            _agent_resp = self._bedrock_agent_runtime_client.invoke_agent(
                inputText=input_text,
                agentId=agent_id,
                agentAliasId=agent_alias_id, 
                sessionId=session_id,
                sessionState={
                    'invocationId': function_call["invocationId"],
                    'returnControlInvocationResults': [{
                        'functionResult': {
                            'actionGroup': function_call["invocationInputs"][0]["functionInvocationInput"]["actionGroup"],
                            'function': function_call["invocationInputs"][0]["functionInvocationInput"]["function"],
                            'responseBody': {
                                "TEXT": {
                                    'body': function_call_result
                                }}}}]},
                enableTrace=enable_trace, 
                endSession= end_session
            )
        else:
            _agent_resp = self._bedrock_agent_runtime_client.invoke_agent(
                inputText=input_text,
                agentId=agent_id,
                agentAliasId=agent_alias_id, 
                sessionId=session_id,
                enableTrace=enable_trace, 
                endSession= end_session
            )

        # logger.info(pprint.pprint(agentResponse))
    
        _agent_answer = ""
        _event_stream = _agent_resp['completion']
        try:
            for _event in _event_stream:        
                if 'chunk' in _event:
                    _data = _event['chunk']['bytes']
                    _agent_answer = _data.decode('utf8')
                    _end_event_received = True
                    # End event indicates that the request finished successfully
                elif 'returnControl' in _event:
                    _agent_answer = _event['returnControl']
                elif 'trace' in _event:
                    print(json.dumps(_event['trace'], indent=2))
                else:
                    raise Exception("unexpected event.", _event)
            return _agent_answer
        except Exception as e:
            raise Exception("unexpected event.", e)
        
    def update_agent(self,
                     agent_name: str,
                     new_model_id: str=None,
                     new_instructions: str=None,
                     guardrail_id: str=None):
        """Updates an agent with new details.

        Args:
            agent_name (str): The name of the agent to update.
            new_model_id (str, optional): The new model ID to use. Defaults to None.
            new_instructions (str, optional): The new instructions to use. Defaults to None.
            guardrail_id (str, optional): ID of the new guardrail to use. Defaults to None.

        Returns:
            dict: UpdateAgent response.
        """
        _agent_id = self.get_agent_id_by_name(agent_name)

        # Get current agent details
        _get_agent_response = self._bedrock_agent_client.get_agent(
            agentId=_agent_id)

        _agent_details = _get_agent_response.get('agent')

        # Update model id.
        if new_model_id is not None:
            _agent_details['foundationModel'] = new_model_id

        # Update instructions.
        if new_instructions is not None:
            _agent_details['instruction'] = new_instructions

        # Update guardrail.
        if guardrail_id is not None:
            # print(_agent_details)
            _agent_details['guardrailConfiguration'] = {"guardrailIdentifier": guardrail_id,
                                                        "guardrailVersion": "DRAFT"}

        # Preserve prompt override configs 
        _promptOverrideConfigsList = _agent_details['promptOverrideConfiguration'].get('promptConfigurations')
        _filteredPromptOverrideConfigsList = list(filter(lambda x: (x['promptCreationMode'] == "OVERRIDDEN"), 
                                                         _promptOverrideConfigsList))
        _agent_details['promptOverrideConfiguration']['promptConfigurations'] = _filteredPromptOverrideConfigsList
        
        # Remove the fields that are not necessary for UpdateAgent API
        for key_to_remove in ['clientToken', 'createdAt', 'updatedAt', 'preparedAt', 'agentStatus', 'agentArn']:
            if key_to_remove in _agent_details:
                del(_agent_details[key_to_remove])
        
        # Update the agent.
        _update_agent_response = self._bedrock_agent_client.update_agent(**_agent_details)

        time.sleep(3)
        
        #Prepare Agent
        self._bedrock_agent_client.prepare_agent(agentId=_agent_id)

        return _update_agent_response