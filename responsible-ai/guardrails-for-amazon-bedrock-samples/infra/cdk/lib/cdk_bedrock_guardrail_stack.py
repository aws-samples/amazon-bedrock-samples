from aws_cdk import (
    Stack,
    aws_bedrock as bedrock,
    CfnTag,
    CfnOutput
)
from constructs import Construct

class CdkBedrockGuardrailStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        guardrail = bedrock.CfnGuardrail(self, "CustomerSupportChatbotGuardrail",
            name="CustomerSupportChatbotGuardrail",
            description="Guardrail to filter harmful content in customer support chatbot interactions",
            blocked_input_messaging=(
                "Your input contains inappropriate content and cannot be processed. "
                "Keep in mind that this chatbot cannot provide specific financial advice. "
                "Please ask a general question or contact a financial advisor for personalized advice."
            ),
            blocked_outputs_messaging="The response generated contains inappropriate content and has been blocked.",
            content_policy_config=bedrock.CfnGuardrail.ContentPolicyConfigProperty(
                filters_config=[
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(type="SEXUAL", input_strength="HIGH", output_strength="HIGH"),
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(type="VIOLENCE", input_strength="HIGH", output_strength="HIGH"),
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(type="HATE", input_strength="HIGH", output_strength="MEDIUM"),
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(type="INSULTS", input_strength="HIGH", output_strength="HIGH"),
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(type="MISCONDUCT", input_strength="HIGH", output_strength="HIGH"),
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(type="PROMPT_ATTACK", input_strength="HIGH", output_strength="NONE")
                ]
            ),
            sensitive_information_policy_config=bedrock.CfnGuardrail.SensitiveInformationPolicyConfigProperty(
                pii_entities_config=[
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(type="EMAIL", action="ANONYMIZE"),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(type="PHONE", action="ANONYMIZE"),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(type="NAME", action="ANONYMIZE"),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(type="US_SOCIAL_SECURITY_NUMBER", action="BLOCK"),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(type="US_BANK_ACCOUNT_NUMBER", action="BLOCK"),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(type="CREDIT_DEBIT_CARD_NUMBER", action="BLOCK")
                ],
                regexes_config=[
                    bedrock.CfnGuardrail.RegexConfigProperty(
                        name="AccountNumber",
                        description="Matches account numbers in the format XXXXXX1234",
                        pattern="\\b\\d{6}\\d{4}\\b",
                        action="ANONYMIZE"
                    )
                ]
            ),
            topic_policy_config=bedrock.CfnGuardrail.TopicPolicyConfigProperty(
                topics_config=[
                    bedrock.CfnGuardrail.TopicConfigProperty(
                        name="FiduciaryAdvice",
                        definition=(
                            "Avoid providing guidance on managing financial assets, investments, or trusts "
                            "to prevent fiduciary responsibility."
                        ),
                        examples=[
                            "What stocks should I invest in for my retirement?",
                            "Is it a good idea to put my money in a mutual fund?",
                            "How should I allocate my 401(k) investments?",
                            "What type of trust fund should I set up for my children?",
                            "Should I hire a financial advisor to manage my investments?"
                        ],
                        type="DENY"
                    )
                ]
            ),
            word_policy_config=bedrock.CfnGuardrail.WordPolicyConfigProperty(
                words_config=[
                    bedrock.CfnGuardrail.WordConfigProperty(text="fiduciary advice"),
                    bedrock.CfnGuardrail.WordConfigProperty(text="investment recommendations"),
                    bedrock.CfnGuardrail.WordConfigProperty(text="stock picks"),
                    bedrock.CfnGuardrail.WordConfigProperty(text="financial planning guidance"),
                    bedrock.CfnGuardrail.WordConfigProperty(text="portfolio allocation advice"),
                    bedrock.CfnGuardrail.WordConfigProperty(text="retirement fund suggestions"),
                    bedrock.CfnGuardrail.WordConfigProperty(text="wealth management tips"),
                    bedrock.CfnGuardrail.WordConfigProperty(text="trust fund setup"),
                    bedrock.CfnGuardrail.WordConfigProperty(text="investment strategy"),
                    bedrock.CfnGuardrail.WordConfigProperty(text="financial advisor recommendations")
                ],
                managed_word_lists_config=[
                    bedrock.CfnGuardrail.ManagedWordsConfigProperty(type="PROFANITY")
                ]
            ),
            tags=[
                CfnTag(key="Environment", value="Development"),
                CfnTag(key="Application", value="CustomerSupportChatbot")
            ]
        )

        # Output the Guardrail Identifier
        CfnOutput(self, "GuardrailIdentifier",
            value=guardrail.ref,
            description="The unique identifier of the guardrail",
            export_name="CustomerSupportChatbotGuardrailId"
        )
