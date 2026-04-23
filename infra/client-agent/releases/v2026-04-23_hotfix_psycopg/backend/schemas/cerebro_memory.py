from datetime import datetime

from pydantic import BaseModel, Field


class ProjectContextSchema(BaseModel):
    name: str = ""
    objectives: list[str] = Field(default_factory=list)
    architecture: list[str] = Field(default_factory=list)


class StandardMemorySchema(BaseModel):
    project_context: ProjectContextSchema = Field(default_factory=ProjectContextSchema)
    technical_decisions: list[str] = Field(default_factory=list)
    completed_tasks: list[str] = Field(default_factory=list)
    user_preferences: list[str] = Field(default_factory=list)
    known_issues: list[str] = Field(default_factory=list)


class MemoryUpsertRequest(BaseModel):
    project_tag: str
    memory: StandardMemorySchema


class MemoryResponse(BaseModel):
    project_tag: str
    source_used: str
    memory: StandardMemorySchema
    updated_at: datetime

