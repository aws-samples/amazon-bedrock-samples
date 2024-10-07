from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import BedrockAgentResolver
from aws_lambda_powertools.event_handler.openapi.params import Body
from typing_extensions import Annotated

from .athena_sql_query import get_data_from_database
from .calendar_integration import find_meeting_timeslot, schedule_standard_meeting
from .email_integration import send_email
from .generate_image import generate_image
from .slack_integration import send_slack_message

logger = Logger()

app = BedrockAgentResolver()


@app.post("/execute_query", "Execute query on a database")
def call_sql_database() -> Annotated[dict, Body(description="Successful response with statement results")]:
    return get_data_from_database(app.current_event.json_body["query"])


@app.post("/send_email", "Send email to employee")
def send_email_endpoint(
        email_address: Annotated[str, Body(description="The email address to send the email to")],
        subject: Annotated[str, Body(description="The subject of the email")],
        body: Annotated[str, Body(description="The body of the email")],
) -> Annotated[dict, Body(description="Whether the email was sent successfully")]:
    return send_email(email_address, subject, body)


@app.post("/generate_image", "Generate an image")
def generate_image_endpoint(
        image_type: Annotated[str, Body(description="The task type is Emoji or Image")],
        image_description: Annotated[str, Body(description="The description of the image to generate")],
) -> Annotated[dict, Body(description="S3 location of the generated image")]:
    return generate_image(image_type, image_description)


@app.post("/send_slack_message", "Sends a slack message")
def send_slack_message_endpoint() -> Annotated[dict, Body(description="Whether the message was sent successfully")]:
    return send_slack_message(app.current_event.json_body["message"])


@app.post("/send_meeting", "Sends a meeting invite")
def schedule_meeting_endpoint(
        meeting_subject: Annotated[str, Body(description="the subject of the meeting invite")],
        meeting_body: Annotated[str, Body(description="the body of the meeting invite")],
        organizer: Annotated[
            str, Body(description="the email address of the employee who is scheduling the meeting")
        ],
        attendee: Annotated[
            str, Body(description="the email address of the employee who is attending the meeting")
        ],
        start_time: Annotated[
            str, Body(description="The start time of the meeting in the format yyyy-mm-ddThh:mm:ss")
        ],
        end_time: Annotated[
            str, Body(description="The end time of the meeting in the format yyyy-mm-ddThh:mm:ss")
        ],
) -> Annotated[dict, Body(description="Whether the meeting was scheduled successfully")]:
    return schedule_standard_meeting(
        meeting_subject, meeting_body, organizer, [attendee], start_time, end_time
    )


@app.post("/get_availability", "Gets the first available free meeting slot")
def get_availability_endpoint(
        email1: Annotated[str, Body(description="A list of emails to check availability for")],
        email2: Annotated[str, Body(description="A list of emails to check availability for")],
        duration: Annotated[int, Body(description="The duration of the meeting in minutes")],
        date: Annotated[str, Body(description="The date of the meeting in the format yyyy-mm-dd")],
) -> dict:
    emails = [email1, email2]
    return find_meeting_timeslot(emails, duration, date, "09:00", date, "17:00")


def handler(event, context):
    print(event)
    return app.resolve(event, context)
