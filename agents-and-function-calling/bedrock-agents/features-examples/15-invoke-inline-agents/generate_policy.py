import os
import json
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

# Constants
config = Config(read_timeout=1000)
MODEL_ID = 'anthropic.claude-3-sonnet-20240229-v1:0'
INFERENCE_CONFIG = {
    "maxTokens": 4096,
    "temperature": 0,
    "topP": 0.99,
}

SYSTEM_PROMPTS = [
    {
        "text": "You are an expert HR policy writer. Your task is to create a comprehensive and professional policy document."
    }
]

HR_POLICY_PROMPT = """Create a comprehensive Human Resources policy document for Octank Inc, a fictitious company. The policy should be well-written, professional, and approximately 3000 words in length. The document should cover a wide range of HR topics and include the following sections:

1. Introduction
   - Company overview
   - Purpose of the HR policy
   - Scope and applicability

2. Employment Policies
   - Equal Employment Opportunity
   - Recruitment and selection process
   - Employment classifications (full-time, part-time, temporary, etc.)
   - Probationary period
   - Background checks and reference checks

3. Compensation and Benefits (No dollar or percentage numbers)
   - Salary structure and pay periods
   - Health insurance
   - Retirement plans
   - Paid time off (vacation, sick leave, personal days)
   - Other benefits (e.g., life insurance, disability insurance)

4. Work Hours and Attendance
   - Standard work hours
   - Flexible work arrangements
   - Overtime policy
   - Time tracking and reporting
   - Attendance and punctuality expectations

5. Leave Policies
   - Annual leave/vacation
   - Sick leave
   - Parental leave (maternity, paternity, adoption)
   - Bereavement leave
   - Jury duty
   - Military leave
   - Unpaid leave of absence

6. Performance Management
   - Performance review process
   - Goal setting and objectives
   - Performance improvement plans
   - Promotions and career development

7. Code of Conduct
   - Professional behavior expectations
   - Dress code
   - Conflict of interest
   - Confidentiality and data protection
   - Use of company resources and equipment

8. Anti-Discrimination and Harassment
   - Definition of discrimination and harassment
   - Reporting procedures
   - Investigation process
   - Consequences for policy violations

9. Health and Safety
   - Workplace safety guidelines
   - Accident reporting and investigation
   - Emergency procedures
   - Drug and alcohol policy

10. Technology and Communication
    - Acceptable use of company technology
    - Social media policy
    - Email and internet usage
    - Phone bill reimbursement policy (include detailed guidelines for submitting claims, eligible expenses, and reimbursement limits)

11. Travel and Expense Policy
    - Business travel guidelines
    - Expense reporting and reimbursement
    - Corporate credit card usage

12. Training and Development
    - Mandatory training programs
    - Professional development opportunities
    - Tuition reimbursement policy

13. Disciplinary Procedures
    - Progressive discipline policy
    - Grounds for immediate termination
    - Appeal process

14. Termination and Resignation
    - Notice periods
    - Exit interview process
    - Return of company property
    - Final paycheck and benefits information

15. Whistleblower Policy
    - Reporting mechanisms
    - Protection against retaliation
    - Investigation procedures

16. Remote Work Policy
    - Eligibility criteria
    - Equipment and technology requirements
    - Performance expectations
    - Communication guidelines

17. Employee Privacy
    - Collection and use of personal information
    - Monitoring of company resources and communications
    - Access to personnel files

18. Grievance Procedures
    - Steps for filing a grievance
    - Resolution process
    - Timeframes for addressing complaints

19. Company Culture and Employee Engagement
    - Company values and mission statement
    - Employee recognition programs
    - Team-building activities and social events

20. Policy Review and Updates
    - Frequency of policy reviews
    - Process for suggesting policy changes
    - Communication of policy updates to employees

Ensure that the policy is written in clear, concise language that is easy for employees to understand. Use appropriate headings, subheadings, and bullet points to organize the information effectively. Include specific examples and scenarios where applicable to illustrate policy implementation.

The phone bill reimbursement policy should be detailed and include information on:
- Eligibility criteria for reimbursement
- Types of calls and data usage covered
- Monthly reimbursement limits
- Required documentation for claims
- Submission process and deadlines
- Approval and payment procedures

Throughout the document, emphasize Octank Inc's commitment to creating a positive work environment, fostering employee growth, and maintaining compliance with relevant laws and regulations. Conclude the policy with a statement encouraging employees to familiarize themselves with the contents and to seek clarification from HR if they have any questions or concerns."""

MANAGEMENT_POLICY_PROMPT = """Create a comprehensive HR Policy document for Octank Inc, a fictitious company. This policy is intended to be accessed by managers and executives only and employees. The policy should be well-written, professional, and approximately 2000 words in length. The document should cover the following sections:

1. Introduction
   - Purpose of the management policy
   - Scope and applicability to management roles

2. Leadership Expectations
   - Core leadership competencies
   - Ethical decision-making
   - Leading by example

3. Compensation and Benefits for Employees and Management Roles
   - Salary structure both employee and management positions
   - Performance based bonuses, incentives, and include dollar amount of bonus and percentage pay raises
   - Stock options and equity compensation
   - Executive benefits package
   - include compensation bonus amount by performance tiers

4. Performance Management Information for Managers
   - Setting and cascading organizational goals
   - Conducting performance evaluations for direct reports
   - Addressing performance issues within teams
   - Succession planning and talent development

5. Budget and Resource Management
   - Annual budgeting process
   - Resource allocation and optimization
   - Cost control measures
   - Financial reporting responsibilities

6. Strategic Planning and Execution
   - Developing departmental and team strategies
   - Aligning team goals with company objectives
   - Project prioritization and management
   - Change management processes

7. Team Development and Engagement
   - Building and maintaining high-performing teams
   - Employee engagement strategies
   - Conflict resolution techniques
   - Promoting diversity, equity, and inclusion

8. Communication and Reporting
   - Upward and downward communication expectations
   - Conducting effective meetings
   - Stakeholder management
   - Crisis communication protocols

9. Risk Management and Compliance
   - Identifying and mitigating operational risks
   - Ensuring compliance with company policies and regulations
   - Data protection and confidentiality
   - Intellectual property safeguarding

10. Innovation and Continuous Improvement
    - Fostering a culture of innovation
    - Implementing process improvements
    - Encouraging and evaluating new ideas
    - Managing pilot projects and initiatives

11. Work-Life Balance for Managers
    - Managing workload and preventing burnout
    - Flexible work arrangements for management
    - Stress management and mental health support

12. Management Training and Development
    - Required leadership training programs
    - Executive coaching opportunities
    - Management conferences and networking events
    - Cross-functional exposure and job rotation

Ensure that the policy is written in clear, concise language that is appropriate for a management audience. Use appropriate headings, subheadings, and bullet points to organize the information effectively. Include specific examples and scenarios where applicable to illustrate policy implementation.

Throughout the document, emphasize Octank Inc's commitment to developing strong leaders, fostering innovation, and maintaining ethical business practices. Conclude the policy with a statement encouraging managers to embody the company's values and to seek guidance from senior leadership or HR when faced with challenging situations."""

ADDITIONAL_MODEL_FIELDS = {}

def generate_policy(bedrock_client, prompt, output_file):
    message = {
        "role": "user",
        "content": [{
            "text": prompt
        }]
    }
    
    try:
        response = bedrock_client.converse(
            modelId=MODEL_ID,
            messages=[message],
            system=SYSTEM_PROMPTS,
            inferenceConfig=INFERENCE_CONFIG,
            additionalModelRequestFields=ADDITIONAL_MODEL_FIELDS
        )        
        generated_policy = response['output']['message']['content'][0]['text']
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Save the generated text to a file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(generated_policy)
        
        print(f"Policy has been generated and saved to '{output_file}'")
        
    except ClientError as err:
        message = err.response['Error']['Message']
        print(f"An error occurred: {message}")
        raise
    except IOError as e:
        print(f"An I/O error occurred while writing to '{output_file}': {str(e)}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        raise

def create_kb_documents(path):
    # Initialize the Bedrock client
    bedrock = boto3.client('bedrock-runtime', config=config)
    
    # Ensure the path ends with a slash
    path = os.path.join(path, '')
    
    # Generate the HR policy
    generate_policy(bedrock, HR_POLICY_PROMPT, os.path.join(path, 'hrpolicy.txt'))
    
    # Generate the Management policy
    generate_policy(bedrock, MANAGEMENT_POLICY_PROMPT, os.path.join(path, 'manageronly_policy.txt'))
    print('Synthetic policies generation process is complete.')