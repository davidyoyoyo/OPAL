"""SQLAlchemy models for OPAL's canonical evidence database.

Respondent-level records are intentionally not represented here. Survey answers
are stored as aggregate distributions, and bilingual text keeps source wording.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index,
    Integer, Numeric, SmallInteger, String, Text, UniqueConstraint, func, text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid


JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SourceProvider(TimestampMixin, Base):
    __tablename__ = "source_providers"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    provider_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    base_url: Mapped[str | None] = mapped_column(Text)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ResearchWork(TimestampMixin, Base):
    __tablename__ = "research_works"
    __table_args__ = (
        CheckConstraint("identity_status IN ('verified', 'probable', 'unresolved')"),
        CheckConstraint("publication_year IS NULL OR publication_year BETWEEN 1400 AND 2200"),
        Index("research_works_doi_unique", text("lower(doi)"), unique=True, postgresql_where=text("doi IS NOT NULL")),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    canonical_key: Mapped[str | None] = mapped_column(String, unique=True)
    title_original: Mapped[str] = mapped_column(Text, nullable=False)
    title_language: Mapped[str] = mapped_column(String, default="und", nullable=False)
    title_english: Mapped[str | None] = mapped_column(Text)
    abstract_original: Mapped[str | None] = mapped_column(Text)
    abstract_language: Mapped[str | None] = mapped_column(String)
    abstract_english: Mapped[str | None] = mapped_column(Text)
    publication_year: Mapped[int | None] = mapped_column(SmallInteger)
    publication_type: Mapped[str] = mapped_column(String, default="unknown", nullable=False)
    doi: Mapped[str | None] = mapped_column(String)
    identifiers: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    authors: Mapped[list[Any]] = mapped_column(JSON_TYPE, default=list, nullable=False)
    identity_status: Mapped[str] = mapped_column(String, default="unresolved", nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SourceRecord(TimestampMixin, Base):
    __tablename__ = "source_records"
    __table_args__ = (
        UniqueConstraint("provider_id", "provider_record_id"),
        CheckConstraint("record_status IN ('active', 'unavailable', 'superseded')"),
        Index("source_records_work_idx", "work_id"),
        Index("source_records_provider_idx", "provider_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    work_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("research_works.id", ondelete="CASCADE"), nullable=False)
    provider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("source_providers.id"), nullable=False)
    provider_record_id: Mapped[str | None] = mapped_column(String)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    raw_metadata: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    record_status: Mapped[str] = mapped_column(String, default="active", nullable=False)


class Survey(TimestampMixin, Base):
    __tablename__ = "surveys"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    work_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("research_works.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    organization: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)


class SurveyWave(TimestampMixin, Base):
    __tablename__ = "survey_waves"
    __table_args__ = (
        UniqueConstraint("survey_id", "wave_key"),
        CheckConstraint("fieldwork_end IS NULL OR fieldwork_start IS NULL OR fieldwork_end >= fieldwork_start"),
        CheckConstraint("sample_size IS NULL OR sample_size >= 0"),
        CheckConstraint("margin_of_error IS NULL OR margin_of_error >= 0"),
        CheckConstraint("confidence_level IS NULL OR (confidence_level > 0 AND confidence_level < 100)"),
        Index("survey_waves_dates_idx", "fieldwork_start", "fieldwork_end"),
        Index("survey_waves_geography_idx", "geography"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    survey_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False)
    wave_key: Mapped[str | None] = mapped_column(String)
    wave_label: Mapped[str | None] = mapped_column(String)
    population_description: Mapped[str] = mapped_column(Text, nullable=False)
    geography: Mapped[str | None] = mapped_column(String)
    fieldwork_start: Mapped[date | None] = mapped_column(Date)
    fieldwork_end: Mapped[date | None] = mapped_column(Date)
    sample_size: Mapped[int | None] = mapped_column(Integer)
    sampling_method: Mapped[str | None] = mapped_column(Text)
    weighting_description: Mapped[str | None] = mapped_column(Text)
    margin_of_error: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
    confidence_level: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    methodology_details: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)


class SurveyQuestion(TimestampMixin, Base):
    __tablename__ = "survey_questions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    wave_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("survey_waves.id", ondelete="CASCADE"), nullable=False)
    question_code: Mapped[str | None] = mapped_column(String)
    question_order: Mapped[int | None] = mapped_column(Integer)
    question_text_original: Mapped[str] = mapped_column(Text, nullable=False)
    question_language: Mapped[str] = mapped_column(String, default="und", nullable=False)
    question_text_english: Mapped[str | None] = mapped_column(Text)
    question_type: Mapped[str] = mapped_column(String, default="single_choice", nullable=False)
    is_multiple_response: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    routing_note: Mapped[str | None] = mapped_column(Text)


class StanceCategory(Base):
    __tablename__ = "stance_categories"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    category_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    display_label: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class AnswerOption(TimestampMixin, Base):
    __tablename__ = "answer_options"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("survey_questions.id", ondelete="CASCADE"), nullable=False)
    option_order: Mapped[int | None] = mapped_column(Integer)
    option_text_original: Mapped[str] = mapped_column(Text, nullable=False)
    option_language: Mapped[str] = mapped_column(String, default="und", nullable=False)
    option_text_english: Mapped[str | None] = mapped_column(Text)
    stance_category_id: Mapped[int | None] = mapped_column(ForeignKey("stance_categories.id"))
    is_exclusive: Mapped[bool | None] = mapped_column(Boolean)


class ResponseDistribution(TimestampMixin, Base):
    __tablename__ = "response_distributions"
    __table_args__ = (
        CheckConstraint("response_count IS NULL OR response_count >= 0"),
        CheckConstraint("reported_percentage IS NULL OR (reported_percentage >= 0 AND reported_percentage <= 100)"),
        CheckConstraint("calculated_percentage IS NULL OR (calculated_percentage >= 0 AND calculated_percentage <= 100)"),
        CheckConstraint("base_n IS NULL OR base_n >= 0"),
        CheckConstraint("missing_count IS NULL OR missing_count >= 0"),
        CheckConstraint("refused_count IS NULL OR refused_count >= 0"),
        CheckConstraint("percentage_basis IN ('reported', 'calculated', 'unknown')"),
        CheckConstraint("response_count IS NOT NULL OR reported_percentage IS NOT NULL OR calculated_percentage IS NOT NULL"),
        CheckConstraint("percentage_basis <> 'reported' OR reported_percentage IS NOT NULL"),
        CheckConstraint("percentage_basis <> 'calculated' OR calculated_percentage IS NOT NULL"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    answer_option_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("answer_options.id", ondelete="CASCADE"), nullable=False)
    response_count: Mapped[int | None] = mapped_column(BigInteger)
    reported_percentage: Mapped[Decimal | None] = mapped_column(Numeric(8, 5))
    calculated_percentage: Mapped[Decimal | None] = mapped_column(Numeric(8, 5))
    base_n: Mapped[int | None] = mapped_column(Integer)
    missing_count: Mapped[int | None] = mapped_column(Integer)
    refused_count: Mapped[int | None] = mapped_column(Integer)
    percentage_basis: Mapped[str] = mapped_column(String, default="unknown", nullable=False)
    source_note: Mapped[str | None] = mapped_column(Text)


class QualitativeFinding(TimestampMixin, Base):
    __tablename__ = "qualitative_findings"
    __table_args__ = (
        CheckConstraint("evidence_type IN ('survey', 'discussion', 'supporting_research')"),
        CheckConstraint("finding_kind IN ('finding', 'argument', 'theme', 'excerpt', 'claim')"),
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)"),
        CheckConstraint("observed_to IS NULL OR observed_from IS NULL OR observed_to >= observed_from"),
        Index("qualitative_findings_work_idx", "work_id"),
        Index("qualitative_findings_type_idx", "evidence_type"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    work_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("research_works.id", ondelete="SET NULL"))
    source_record_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("source_records.id", ondelete="SET NULL"))
    evidence_type: Mapped[str] = mapped_column(String, nullable=False)
    finding_kind: Mapped[str] = mapped_column(String, default="theme", nullable=False)
    content_original: Mapped[str] = mapped_column(Text, nullable=False)
    content_language: Mapped[str] = mapped_column(String, default="und", nullable=False)
    content_english: Mapped[str | None] = mapped_column(Text)
    population_description: Mapped[str | None] = mapped_column(Text)
    geography: Mapped[str | None] = mapped_column(String)
    observed_from: Mapped[date | None] = mapped_column(Date)
    observed_to: Mapped[date | None] = mapped_column(Date)
    stance_category_id: Mapped[int | None] = mapped_column(ForeignKey("stance_categories.id"))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))


class ArgumentTheme(TimestampMixin, Base):
    __tablename__ = "argument_themes"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    theme_key: Mapped[str | None] = mapped_column(String, unique=True)
    name_original: Mapped[str] = mapped_column(Text, nullable=False)
    name_language: Mapped[str] = mapped_column(String, default="und", nullable=False)
    name_english: Mapped[str | None] = mapped_column(Text)
    description_original: Mapped[str | None] = mapped_column(Text)
    description_language: Mapped[str | None] = mapped_column(String)
    description_english: Mapped[str | None] = mapped_column(Text)


class FindingArgumentTheme(Base):
    __tablename__ = "finding_argument_themes"
    finding_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("qualitative_findings.id", ondelete="CASCADE"), primary_key=True)
    theme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("argument_themes.id", ondelete="CASCADE"), primary_key=True)
    relevance: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"
    __table_args__ = (
        CheckConstraint("run_type IN ('discovery', 'metadata_refresh', 'survey_extraction', 'qualitative_extraction', 'translation', 'quality_check')"),
        CheckConstraint("status IN ('running', 'succeeded', 'partial', 'failed')"),
        CheckConstraint("completed_at IS NULL OR completed_at >= started_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    run_type: Mapped[str] = mapped_column(String, nullable=False)
    provider_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("source_providers.id"))
    software_version: Mapped[str | None] = mapped_column(String)
    model_name: Mapped[str | None] = mapped_column(String)
    model_version: Mapped[str | None] = mapped_column(String)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String, default="running", nullable=False)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    error_summary: Mapped[str | None] = mapped_column(Text)


class DataProvenance(Base):
    __tablename__ = "data_provenance"
    __table_args__ = (
        CheckConstraint("target_type IN ('research_work', 'survey_wave', 'survey_question', 'answer_option', 'response_distribution', 'qualitative_finding', 'argument_theme')"),
        CheckConstraint("extraction_method IN ('directly_reported', 'calculated', 'human_extracted', 'model_extracted', 'translated', 'inferred')"),
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)"),
        Index("data_provenance_target_idx", "target_type", "target_id"),
        Index("data_provenance_source_idx", "source_record_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_record_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("source_records.id", ondelete="CASCADE"), nullable=False)
    extraction_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("extraction_runs.id", ondelete="SET NULL"))
    target_type: Mapped[str] = mapped_column(String, nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    source_locator: Mapped[str | None] = mapped_column(Text)
    extraction_method: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    human_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
