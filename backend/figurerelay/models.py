"""The bounded, public request schema.

Copyright 2026 Dhruba Poudel
SPDX-License-Identifier: Apache-2.0
"""

from pydantic import BaseModel, ConfigDict, Field


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


class ProjectCreate(RequestModel):
    name: str = Field(min_length=1, max_length=120)


class ReportSection(RequestModel):
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(max_length=4000)


class Slide(RequestModel):
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(max_length=1200)


class Template(RequestModel):
    title: str = Field(min_length=1, max_length=120)
    sections: list[ReportSection] = Field(min_length=1, max_length=20)
    slides: list[Slide] = Field(min_length=1, max_length=20)


class PreviewRequest(RequestModel):
    expected_revision: int = Field(ge=0)


class ApproveRequest(PreviewRequest):
    actor: str = Field(min_length=1, max_length=120)
    acknowledge_warnings: bool = False


class RejectRequest(RequestModel):
    actor: str = Field(min_length=1, max_length=120)
