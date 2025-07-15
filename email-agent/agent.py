from google.adk import Agent
from pydantic import BaseModel, Field


class EmailContent(BaseModel):
    subject: str = Field(description="The subject of the email")
    body: str = Field(description="The body of the email")


root_agent = Agent(
    name="email_agent",
    model="gemini-2.0-flash",
    description="Generate Professional Emails with structured subject and body",
    instruction="""
            You are an Email Generation Assistant.
            Your task is to generate a professional email base on the user's request.

            GUIDELINES:
            - Create an appropriate subject line for the email.
            - Write a well-structured email body with:
                * Professional greeting.
                * Clear and concise main content.
                * Appropriate closing.
                * Your name as signature.
            - Suggest relevant attachments if applicable(empty list if none needed).
            - Email tone should match the purpose (formal for business, friendly for colleagues).
            - Keep emails concise but complete.

            IMPORTANT: Your response MUST be valid Json matching this structure:
            {
                "subject": "Subject of the email",
                "body": "Body of the email"
            }

            DO NOT include any explanations or additional text outside the JSON response.
""",
    output_schema=EmailContent,
    output_key="email",
)

