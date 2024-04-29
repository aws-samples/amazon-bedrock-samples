"""
This python file contains the prompt used to create the
mock data. Copy and paste this prompt into Amazon Bedrock
playground, Anthropic Claude v2 model. 
"""

prompt = f"""
\n\nHuman: 
Can you create mock data for {2} tables in {"JSON"} format. The two tables are called {"CUSTOMER"} and {"INTERACTIONS"}. The data will be used for Customer Relations Management (CRM) project. 

1. CUSTOMER table has following fields:-
- customer_id(pk): customer_id needs to be 6 characters long and needs to start with C-
- company_name: use intuitive company names
- overview: overview needs to be 30 words long
- meetingType: meetingType can one of the  following values - ["InPerson", "Online"]
- dayOfWeek: dayOfWeek can have one of the following values ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
- timeofDay: timeOfDay can have one of the following value ["Morning", "Afternoon", "Evening"]


2. INTERACTIONS table has following fields:-
- customer_id(foreign key, composite key A)
- date (composite key B): date is in timestamp
- notes: notes field has the summary of what was discussed in the meeting, make sure to make the summary atleast 50 words


The data should consist ATLEAST 5 customers having ATLEAST 5 interactions per customer. 

Output the data inside <{"JSON"}> </{"JSON"}> XML tags.
 \n\nAssistant:
"""
