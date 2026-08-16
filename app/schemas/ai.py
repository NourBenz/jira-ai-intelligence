from pydantic import BaseModel, Field


class ProjectQuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class AIAnswerContent(BaseModel):
    answer: str
    risks: list[str]
    recommendations: list[str]
    source_issue_keys: list[str]
    limitations: list[str]


class ProjectAIResponse(AIAnswerContent):
    project_key: str
    model: str
    grounded: bool = True
