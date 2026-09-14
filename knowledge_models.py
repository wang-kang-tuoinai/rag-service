"""知识查询请求与响应契约，全文和切片通过 content_mode 区分。"""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class KnowledgeSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=2000)
    doc_type: Literal["architecture", "runbook", "technology"] | None = None
    top_k: int = Field(default=3, ge=1, le=5, strict=True,
                       description="聚合后统一排序的结果条数，全文和技术切片各计一条")

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query 不能只包含空白")
        return value


class KnowledgeItemBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    doc_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source: str = Field(min_length=1)
    score: float = Field(allow_inf_nan=False, description="精排分数，不是概率或置信度")
    content: str = Field(min_length=1)


class KnowledgeFullItem(KnowledgeItemBase):
    content_mode: Literal["full"] = "full"
    doc_type: Literal["architecture", "runbook"]
    snapshot_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    matched_sections: list[str]


class KnowledgeChunkItem(KnowledgeItemBase):
    content_mode: Literal["chunk"] = "chunk"
    doc_type: Literal["technology"] = "technology"
    chunk_id: str = Field(min_length=1, description="Chroma 记录 ID")
    component: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    section: str = Field(min_length=1)
    chunk_index: int = Field(ge=0, strict=True)


KnowledgeItem = Annotated[KnowledgeFullItem | KnowledgeChunkItem, Field(discriminator="content_mode")]


class KnowledgeSearchResponse(BaseModel):
    items: list[KnowledgeItem]
    notices: list[str]
