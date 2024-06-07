import json
import boto3
from boto3.dynamodb.conditions import Key
import os
import base64
import urllib
import datetime

url = 'https://' + os.environ["JIRA_URL"]
api_token = os.environ["JIRA_API_TOKEN"]
username = os.environ["JIRA_USERNAME"]
env_name = os.environ["EnvironmentName"]

dynamodb = boto3.resource("dynamodb")
customer_table = dynamodb.Table(f"customer-{env_name}")
interactions_table = dynamodb.Table(f"interactions-{env_name}")

credentials = base64.b64encode(f"{username}:{api_token}".encode("utf-8")).decode(
    "utf-8"
)
# Set up the authentication header
headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Basic {credentials}",
}


def get_customer_interactions(customerId, count):
    response = interactions_table.query(
        ScanIndexForward=False,  # Sort in descending order based on date
        Limit=count,  # Limit the result to the latest 5 items
        KeyConditionExpression=Key("customer_id").eq(
            customerId
        ),  # Ensure the 'date' attribute exists
        ProjectionExpression="#interaction_date,notes",
        ExpressionAttributeNames={"#interaction_date": "date"},
    )
    return response["Items"]


def get_customer(customerId, *args):

    response = customer_table.get_item(
        Key={"customer_id": customerId}, ProjectionExpression=",".join(map(str, args))
    )
    return response.get("Item", None)


def get_named_parameter(event, name):
    return next(item for item in event["parameters"] if item["name"] == name)["value"]


def get_named_property(event, name):
    return next(
        item
        for item in event["requestBody"]["content"]["application/json"]["properties"]
        if item["name"] == name
    )["value"]


def listRecentInteractions(event):
    customerId = get_named_parameter(event, "customerId")
    count = int(get_named_parameter(event, "count"))

    return get_customer_interactions(customerId, count)


def companyOverview(event):
    customerId = get_named_parameter(event, "customerId")

    response_obj = get_customer(customerId, "overview")
    if response_obj:
        return get_customer(customerId, "overview")["overview"]
    else:
        return {}


def getPreferences(event):
    customerId = get_named_parameter(event, "customerId")

    return get_customer(customerId, "meetingType", "timeofDay", "dayOfWeek")


def getOpenJiraIssues(event):
    search_url = f"{url}/search"

    project_id = get_named_parameter(event, "projectId")

    query_params = urllib.parse.urlencode(
        {
            "jql": f"project={project_id} AND issuetype=Task AND status='In Progress' OR status='To Do' order by duedate"
        }
    )

    full_url = f"{search_url}?{query_params}"

    try:
        req = urllib.request.Request(full_url, headers=headers, method="GET")
        with urllib.request.urlopen(req) as response:
            response_data = response.read().decode("utf-8")
            response_json = json.loads(response_data)
            open_tasks = []
            for issue in response_json["issues"]:
                task = {
                    "issueKey": issue["key"],
                    "summary": issue["fields"]["summary"],
                    "status": issue["fields"]["status"]["name"],
                    "project": issue["fields"]["project"]["name"],
                    "duedate": issue["fields"]["duedate"],
                    "assignee": (
                        issue["fields"]["assignee"]["displayName"]
                        if issue["fields"]["assignee"]
                        else "None"
                    ),
                }
                open_tasks.append(task)

            return open_tasks
    except urllib.error.HTTPError as e:
        print("Failed to get issues. HTTPError:", e.code, e.reason)
    except urllib.error.URLError as e:
        print("Failed to get issues. URLError:", e.reason)
    except json.JSONDecodeError:
        print("Failed to decode response as JSON:", response_data)
    except Exception:
        print("Invalid Jira Configuration")


def updateJiraIssue(event):
    print(event)

    issue_key = get_named_parameter(event, "issueKey")
    properties = event["requestBody"]["content"]["application/json"]["properties"]

    for prop in properties:
        if prop["name"] == "timelineInWeeks":
            timeline_in_weeks = int(prop["value"])
            break
    due_date = (
        datetime.datetime.now() + datetime.timedelta(weeks=timeline_in_weeks)
    ).strftime("%Y-%m-%d")
    update_url = f"{url}/issue/{issue_key}"
    update_payload = json.dumps({"fields": {"duedate": due_date}})

    try:
        update_req = urllib.request.Request(
            update_url, data=update_payload.encode(), headers=headers, method="PUT"
        )
        with urllib.request.urlopen(update_req) as update_response:
            update_data = update_response.read().decode("utf-8")
            return {"issueKey": issue_key, "newTimeline": timeline_in_weeks}
    except urllib.error.HTTPError as e:
        print(f"Failed to update task {issue_key}. HTTPError:", e.code, e.reason)
    except urllib.error.URLError as e:
        print(f"Failed to update task {issue_key}. URLError:", e.reason)
    except json.JSONDecodeError:
        print(f"Failed to decode response for task {issue_key}:", update_data)
    except Exception:
        print("Invalid Jira Configuration")


def lambda_handler(event, context):

    response_code = 200
    action_group = event["actionGroup"]
    api_path = event["apiPath"]

    if api_path == "/listRecentInteractions":
        result = listRecentInteractions(event)
    elif api_path == "/getPreferences":
        result = getPreferences(event)
    elif api_path == "/companyOverview":
        result = companyOverview(event)
    elif api_path == "/getOpenJiraIssues":
        result = getOpenJiraIssues(event)
    elif api_path == "/updateJiraIssue":
        result = updateJiraIssue(event)
    else:
        response_code = 404
        result = f"Unrecognized api path: {action_group}::{api_path}"

    response_body = {"application/json": {"body": result}}

    action_response = {
        "actionGroup": event["actionGroup"],
        "apiPath": event["apiPath"],
        "httpMethod": event["httpMethod"],
        "httpStatusCode": response_code,
        "responseBody": response_body,
    }

    api_response = {"messageVersion": "1.0", "response": action_response}
    print(api_response)
    return api_response
