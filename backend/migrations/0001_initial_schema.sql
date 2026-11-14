-- OPAL initial PostgreSQL schema
-- Decisions: aggregate respondent data only; replace current study data in place;
-- preserve original-language text alongside a separate English translation.

CREATE TABLE source_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_key TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    description TEXT,
    base_url TEXT,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE research_works (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_key TEXT UNIQUE,
    title_original TEXT NOT NULL,
    title_language TEXT NOT NULL DEFAULT 'und',
    title_english TEXT,
    abstract_original TEXT,
    abstract_language TEXT,
    abstract_english TEXT,
    publication_year SMALLINT CHECK (publication_year BETWEEN 1400 AND 2200),
    publication_type TEXT NOT NULL DEFAULT 'unknown',
    doi TEXT,
    identifiers JSONB NOT NULL DEFAULT '{}'::jsonb,
    authors JSONB NOT NULL DEFAULT '[]'::jsonb,
    identity_status TEXT NOT NULL DEFAULT 'unresolved'
        CHECK (identity_status IN ('verified', 'probable', 'unresolved')),
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX research_works_doi_unique
    ON research_works (lower(doi)) WHERE doi IS NOT NULL;

CREATE TABLE source_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    work_id UUID NOT NULL REFERENCES research_works(id) ON DELETE CASCADE,
    provider_id UUID NOT NULL REFERENCES source_providers(id),
    provider_record_id TEXT,
    source_url TEXT NOT NULL,
    retrieved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    record_status TEXT NOT NULL DEFAULT 'active'
        CHECK (record_status IN ('active', 'unavailable', 'superseded')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider_id, provider_record_id)
);
CREATE INDEX source_records_work_idx ON source_records(work_id);
CREATE INDEX source_records_provider_idx ON source_records(provider_id);

CREATE TABLE surveys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    work_id UUID NOT NULL REFERENCES research_works(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    organization TEXT,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX surveys_work_idx ON surveys(work_id);

CREATE TABLE survey_waves (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    survey_id UUID NOT NULL REFERENCES surveys(id) ON DELETE CASCADE,
    wave_key TEXT,
    wave_label TEXT,
    population_description TEXT NOT NULL,
    geography TEXT,
    fieldwork_start DATE,
    fieldwork_end DATE,
    sample_size INTEGER CHECK (sample_size IS NULL OR sample_size >= 0),
    sampling_method TEXT,
    weighting_description TEXT,
    margin_of_error NUMERIC(7,4) CHECK (margin_of_error IS NULL OR margin_of_error >= 0),
    confidence_level NUMERIC(5,2) CHECK (confidence_level IS NULL OR (confidence_level > 0 AND confidence_level < 100)),
    methodology_details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (fieldwork_end IS NULL OR fieldwork_start IS NULL OR fieldwork_end >= fieldwork_start),
    UNIQUE (survey_id, wave_key)
);
CREATE INDEX survey_waves_dates_idx ON survey_waves(fieldwork_start, fieldwork_end);
CREATE INDEX survey_waves_geography_idx ON survey_waves(geography);

CREATE TABLE survey_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wave_id UUID NOT NULL REFERENCES survey_waves(id) ON DELETE CASCADE,
    question_code TEXT,
    question_order INTEGER,
    question_text_original TEXT NOT NULL,
    question_language TEXT NOT NULL DEFAULT 'und',
    question_text_english TEXT,
    question_type TEXT NOT NULL DEFAULT 'single_choice',
    is_multiple_response BOOLEAN NOT NULL DEFAULT FALSE,
    routing_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX survey_questions_wave_idx ON survey_questions(wave_id);

CREATE TABLE stance_categories (
    id SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category_key TEXT NOT NULL UNIQUE
        CHECK (category_key IN ('support', 'oppose', 'neutral', 'mixed',
                                'undecided', 'dont_know', 'no_opinion',
                                'other', 'unclassified')),
    display_label TEXT NOT NULL,
    description TEXT
);

CREATE TABLE answer_options (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES survey_questions(id) ON DELETE CASCADE,
    option_order INTEGER,
    option_text_original TEXT NOT NULL,
    option_language TEXT NOT NULL DEFAULT 'und',
    option_text_english TEXT,
    stance_category_id SMALLINT REFERENCES stance_categories(id),
    is_exclusive BOOLEAN,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX answer_options_question_idx ON answer_options(question_id);

CREATE TABLE response_distributions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    answer_option_id UUID NOT NULL REFERENCES answer_options(id) ON DELETE CASCADE,
    response_count BIGINT CHECK (response_count IS NULL OR response_count >= 0),
    reported_percentage NUMERIC(8,5)
        CHECK (reported_percentage IS NULL OR (reported_percentage >= 0 AND reported_percentage <= 100)),
    calculated_percentage NUMERIC(8,5)
        CHECK (calculated_percentage IS NULL OR (calculated_percentage >= 0 AND calculated_percentage <= 100)),
    base_n INTEGER CHECK (base_n IS NULL OR base_n >= 0),
    missing_count INTEGER CHECK (missing_count IS NULL OR missing_count >= 0),
    refused_count INTEGER CHECK (refused_count IS NULL OR refused_count >= 0),
    percentage_basis TEXT NOT NULL DEFAULT 'unknown'
        CHECK (percentage_basis IN ('reported', 'calculated', 'unknown')),
    source_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (response_count IS NOT NULL OR reported_percentage IS NOT NULL)
);
CREATE INDEX response_distributions_option_idx ON response_distributions(answer_option_id);

CREATE TABLE qualitative_findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    work_id UUID REFERENCES research_works(id) ON DELETE SET NULL,
    source_record_id UUID REFERENCES source_records(id) ON DELETE SET NULL,
    evidence_type TEXT NOT NULL
        CHECK (evidence_type IN ('survey', 'discussion', 'supporting_research')),
    finding_kind TEXT NOT NULL DEFAULT 'theme'
        CHECK (finding_kind IN ('finding', 'argument', 'theme', 'excerpt', 'claim')),
    content_original TEXT NOT NULL,
    content_language TEXT NOT NULL DEFAULT 'und',
    content_english TEXT,
    population_description TEXT,
    geography TEXT,
    observed_from DATE,
    observed_to DATE,
    stance_category_id SMALLINT REFERENCES stance_categories(id),
    confidence NUMERIC(5,4) CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (observed_to IS NULL OR observed_from IS NULL OR observed_to >= observed_from)
);
CREATE INDEX qualitative_findings_work_idx ON qualitative_findings(work_id);
CREATE INDEX qualitative_findings_type_idx ON qualitative_findings(evidence_type);

CREATE TABLE argument_themes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    theme_key TEXT UNIQUE,
    name_original TEXT NOT NULL,
    name_language TEXT NOT NULL DEFAULT 'und',
    name_english TEXT,
    description_original TEXT,
    description_language TEXT,
    description_english TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE finding_argument_themes (
    finding_id UUID NOT NULL REFERENCES qualitative_findings(id) ON DELETE CASCADE,
    theme_id UUID NOT NULL REFERENCES argument_themes(id) ON DELETE CASCADE,
    relevance NUMERIC(5,4) CHECK (relevance IS NULL OR (relevance >= 0 AND relevance <= 1)),
    PRIMARY KEY (finding_id, theme_id)
);

CREATE TABLE extraction_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_type TEXT NOT NULL
        CHECK (run_type IN ('discovery', 'metadata_refresh', 'survey_extraction',
                            'qualitative_extraction', 'translation', 'quality_check')),
    provider_id UUID REFERENCES source_providers(id),
    software_version TEXT,
    model_name TEXT,
    model_version TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'succeeded', 'partial', 'failed')),
    summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_summary TEXT,
    CHECK (completed_at IS NULL OR completed_at >= started_at)
);

CREATE TABLE data_provenance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_record_id UUID NOT NULL REFERENCES source_records(id) ON DELETE CASCADE,
    extraction_run_id UUID REFERENCES extraction_runs(id) ON DELETE SET NULL,
    target_type TEXT NOT NULL
        CHECK (target_type IN ('research_work', 'survey_wave', 'survey_question',
                               'answer_option', 'response_distribution',
                               'qualitative_finding', 'argument_theme')),
    target_id UUID NOT NULL,
    source_locator TEXT,
    extraction_method TEXT NOT NULL
        CHECK (extraction_method IN ('directly_reported', 'calculated',
                                     'human_extracted', 'model_extracted',
                                     'translated', 'inferred')),
    confidence NUMERIC(5,4) CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    human_verified BOOLEAN NOT NULL DEFAULT FALSE,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX data_provenance_target_idx ON data_provenance(target_type, target_id);
CREATE INDEX data_provenance_source_idx ON data_provenance(source_record_id);

-- Seed the stance taxonomy. Labels can be localized by the application layer.
INSERT INTO stance_categories (category_key, display_label, description) VALUES
('support', 'Support', 'Expresses support for the proposition being measured.'),
('oppose', 'Oppose', 'Expresses opposition to the proposition being measured.'),
('neutral', 'Neutral', 'Explicitly neutral; not equivalent to uncertainty or no knowledge.'),
('mixed', 'Mixed', 'Contains both supportive and opposing views.'),
('undecided', 'Undecided', 'Respondent has not made a decision.'),
('dont_know', 'Don’t know', 'Respondent indicates insufficient knowledge.'),
('no_opinion', 'No opinion', 'Respondent reports having no opinion.'),
('other', 'Other', 'A source-provided response outside the standard categories.'),
('unclassified', 'Unclassified', 'Cannot be reliably mapped to another category.');
