"use client";

import { useEffect, useRef, useState } from "react";
import AttackGraphVisualizer from "@/components/AttackGraph3D";

interface IncidentEvent {
  event: string;
  source: string;
  severity?: string;
  details?: string;
}

function isSyntheticScenario(value: unknown): value is SyntheticScenario {
  if (!isRecord(value)) return false;
  return (
    typeof value.scenario_id === "string" &&
    typeof value.title === "string" &&
    typeof value.description === "string" &&
    Array.isArray(value.learning_objectives) &&
    value.learning_objectives.every((objective) => typeof objective === "string") &&
    typeof value.event_count === "number" &&
    value.data_classification === "SYNTHETIC" &&
    value.external_connections === false &&
    value.writes_case_data === false
  );
}

function isSyntheticScenarioCatalog(
  value: unknown,
): value is { status: "SYNTHETIC_DEMO_ONLY"; scenarios: SyntheticScenario[] } {
  return (
    isRecord(value) &&
    value.status === "SYNTHETIC_DEMO_ONLY" &&
    Array.isArray(value.scenarios) &&
    value.scenarios.every(isSyntheticScenario)
  );
}

function isSyntheticRun(value: unknown): value is {
  status: "SYNTHETIC_DEMO_ONLY";
  scenario: { scenario_id: string; title: string; description: string; learning_objectives: string[] };
  events: CorrelationInputEvent[];
  correlations: CorrelatedIncident[];
  persisted: false;
  external_connections: false;
  limitations: string;
} {
  if (!isRecord(value) || !isRecord(value.scenario)) return false;
  return (
    value.status === "SYNTHETIC_DEMO_ONLY" &&
    typeof value.scenario.scenario_id === "string" &&
    typeof value.scenario.title === "string" &&
    typeof value.scenario.description === "string" &&
    Array.isArray(value.scenario.learning_objectives) &&
    value.scenario.learning_objectives.every((objective) => typeof objective === "string") &&
    Array.isArray(value.events) &&
    value.events.every(
      (event) =>
        isRecord(event) &&
        typeof event.event_id === "string" &&
        typeof event.event_type === "string" &&
        typeof event.correlation_key === "string",
    ) &&
    value.persisted === false &&
    value.external_connections === false &&
    typeof value.limitations === "string" &&
    isCorrelationResult(value)
  );
}

interface CorrelationInputEvent {
  event_id: string;
  event_type: string;
  correlation_key: string;
  source?: string;
  observed_at?: string;
  severity?: string;
}

interface IncidentTimelineEntry {
  event_id: string;
  event_type: string;
  source: string | null;
  observed_at: string | null;
  reported_severity: string | null;
  detection_scenario_id?: string | null;
  detection_rule_id?: string | null;
}

interface CorrelatedIncident {
  correlation_id: string;
  event_count: number;
  priority: string;
  priority_reasons: string[];
  timeline: IncidentTimelineEntry[];
  synthetic?: boolean;
  scenario_id?: string;
  scenario_title?: string;
  synthetic_run_id?: string;
}

interface SyntheticScenario {
  scenario_id: string;
  title: string;
  description: string;
  learning_objectives: string[];
  event_count: number;
  data_classification: "SYNTHETIC";
  external_connections: false;
  writes_case_data: false;
}

interface IncidentCaseRecord {
  case_id: string;
  correlation_id: string | null;
  title: string;
  summary: string;
  priority: string;
  priority_reasons: string[];
  status: "open" | "in_progress" | "resolved" | "closed";
  assigned_to: string | null;
  event_count: number;
  created_at: string;
  updated_at: string;
  notes?: Array<{ note_id: string; author: string; body: string; created_at: string }>;
  evidence?: Array<{
    evidence_id: string;
    source: string;
    reference: string;
    sha256: string | null;
    added_by: string;
    created_at: string;
  }>;
  purple_team_replays?: PurpleTeamReplay[];
}

interface PurpleTeamReplay {
  replay_id: string;
  case_id: string;
  scenario_id: string;
  expected_rule_id: string;
  evaluated_by: string;
  result: {
    detection_verified: boolean;
    status: string;
    matched_alert: {
      event_id?: string;
      event_type?: string;
      source?: string;
    } | null;
    execution_mode: "OFFLINE_EVALUATION_ONLY";
  };
  created_at: string;
}

interface PlaybookStep {
  step_id: string;
  title: string;
  description: string;
  basis: string;
}

interface PlaybookDecision {
  decision_id: string;
  decision: "approve" | "reject";
  reviewer: string;
  rationale: string;
  created_at: string;
}

interface IncidentPlaybook {
  plan_id: string;
  case_id: string;
  status: "simulated" | "approved_for_manual_review" | "rejected";
  simulated_by: string;
  case_snapshot: Record<string, unknown>;
  steps: PlaybookStep[];
  decisions: PlaybookDecision[];
  execution_status: "NOT_EXECUTED";
  created_at: string;
  updated_at: string;
}

interface IncidentAuditRecord {
  audit_id: string;
  occurred_at: string;
  credential_fingerprint: string | null;
  action: string;
  outcome_code: number;
  record_type: "api_access" | "retention";
}

interface TelemetryConnectorCatalog {
  sources: Array<{
    source_id: string;
    modes: string[];
    credentials_configured: boolean;
  }>;
  file_formats: string[];
  pull_adapters: string[];
  pull_connector_contract_available: boolean;
  push_ingestion_enabled: boolean;
  event_retention_days: number | null;
  limitations: string;
}

interface NormalizedTelemetryEvent {
  event_id: string;
  source_id: string;
  event_type: string;
  observed_at: string;
  reported_severity: string | null;
  detection_scenario_id: string | null;
  detection_rule_id: string | null;
  ingested_at: string;
}

interface OnChainGraphNode {
  id: string;
  kind: string;
  label: string;
  provider: string;
  chain: string;
  block_hash: string;
  block_height: number;
  observed_at: string;
  confidence: string;
  provider_rating?: string;
  report_reference?: string;
  value_atomic?: string;
  unit?: string;
}

interface OnChainGraphEdge {
  source: string;
  target: string;
  relation: string;
  provider: string;
  chain: string;
  block_hash: string;
  block_height: number;
  observed_at: string;
  confidence: string;
  provider_rating?: string;
  category?: string;
  report_reference?: string;
  report_sha256?: string;
  assessed_at?: string;
  value_atomic?: string;
  unit?: string;
}

interface OnChainGraph {
  case_id: string;
  chain: string;
  block_hash: string;
  block_height: number;
  source: string;
  observed_at: string;
  nodes: OnChainGraphNode[];
  edges: OnChainGraphEdge[];
  limitations: string[];
  storage: {
    enabled: boolean;
    snapshot_id: string | null;
    inserted: boolean;
    reorg_fork_preserved: boolean;
    loaded_from_snapshot: boolean;
  };
}

interface OnChainSnapshot {
  snapshot_id: string;
  chain: "bitcoin" | "ethereum";
  height: number;
  block_hash: string;
  parent_hash: string | null;
  source: string;
  block_timestamp: string;
  fetched_at: string;
  stored_at: string;
  payload_bytes: number;
}

interface OnChainForensicsResult {
  case_id: string;
  block: {
    height: number;
    block_hash: string;
    source: string;
    observed_at: string;
  };
  logs: Array<{
    address: string;
    topics: string[];
    transaction_hash: string;
    log_index: number;
    removed: boolean;
  }>;
  transfer_observations: Array<{
    token_contract: string;
    transaction_hash: string;
    log_index: number;
    from_address: string;
    to_address: string;
    value_atomic: string | null;
    token_id: string | null;
    confidence: string;
  }>;
  provider_assessments: Array<{
    address: string;
    provider: string;
    provider_rating: string;
    verification_status: string;
  }>;
  regulatory_assessment: {
    status: string;
    frameworks: string[];
  };
  limitations: string[];
}

interface OnChainTraceResult {
  case_id: string;
  transaction_hash: string;
  block_hash: string;
  block_height: number;
  confidence: string;
  trace: {
    call_type: string;
    from_address: string;
    to_address: string | null;
    value_atomic: string;
    gas_used: string | null;
    input_selector: string | null;
    input_bytes: number;
    error: string | null;
    calls: unknown[];
  };
  regulatory_assessment: {
    status: string;
    frameworks: string[];
  };
  limitations: string[];
}

interface RegulatoryChecklistControl {
  control_id: string;
  framework: string;
  title: string;
  review_prompt: string;
  official_reference: string;
  source_url: string;
  applicability: "not_assessed" | "in_scope" | "out_of_scope" | "needs_legal_review";
  review_state: "not_assessed" | "evidence_recorded" | "needs_review";
  summary: string;
  updated_by: string | null;
  updated_at: string;
  evidence: Array<{
    evidence_id: string;
    source: string;
    reference: string;
    sha256: string;
    recorded_by: string;
    recorded_at: string;
  }>;
}

interface RegulatoryChecklist {
  case_id: string;
  profile: "EU_CASP";
  profile_version: string;
  overall_status: "NOT_ASSESSED";
  controls: RegulatoryChecklistControl[];
  limitations: string[];
}

interface ControlCoverageRow {
  mapping_id: string;
  catalog_version: string;
  control_id: string;
  framework: string;
  framework_version: string;
  source_reference: string;
  mapping_type: string;
  recorded_at: string;
  control_title: string;
  assessment_state: "verified" | "failed" | "needs_review" | "not_assessed" | "not_applicable";
  assessment_id: string | null;
  assessed_at: string | null;
  assessed_by: string | null;
  evidence_reference_count: number;
  assessment_catalog_version: string | null;
  mapping_interpretation: "RELATED_NOT_EQUIVALENT";
}

interface ControlCoverageReport {
  catalog_version: string;
  framework_filter: string | null;
  mapping_count: number;
  state_counts: Record<string, number>;
  mappings: ControlCoverageRow[];
  certification_status: "NOT_ASSESSED";
  limitations: string[];
  generated_at: string;
  report_sha256: string;
}

function isTelemetryConnectorCatalog(value: unknown): value is TelemetryConnectorCatalog {
  return (
    isRecord(value) &&
    Array.isArray(value.sources) &&
    value.sources.every(
      (source) =>
        isRecord(source) &&
        typeof source.source_id === "string" &&
        Array.isArray(source.modes) &&
        source.modes.every((mode) => typeof mode === "string") &&
        source.credentials_configured === true,
    ) &&
    Array.isArray(value.file_formats) &&
    value.file_formats.every((format) => typeof format === "string") &&
    Array.isArray(value.pull_adapters) &&
    value.pull_adapters.every((adapter) => typeof adapter === "string") &&
    typeof value.pull_connector_contract_available === "boolean" &&
    typeof value.push_ingestion_enabled === "boolean" &&
    (typeof value.event_retention_days === "number" || value.event_retention_days === null) &&
    typeof value.limitations === "string"
  );
}

function isOnChainGraph(value: unknown): value is OnChainGraph {
  if (!isRecord(value)) return false;
  return (
    typeof value.case_id === "string" &&
    (value.chain === "bitcoin" || value.chain === "ethereum") &&
    typeof value.block_hash === "string" &&
    typeof value.block_height === "number" &&
    typeof value.source === "string" &&
    typeof value.observed_at === "string" &&
    isRecord(value.storage) &&
    typeof value.storage.enabled === "boolean" &&
    (typeof value.storage.snapshot_id === "string" || value.storage.snapshot_id === null) &&
    typeof value.storage.inserted === "boolean" &&
    typeof value.storage.reorg_fork_preserved === "boolean" &&
    typeof value.storage.loaded_from_snapshot === "boolean" &&
    Array.isArray(value.nodes) &&
    value.nodes.every(
      (node) =>
        isRecord(node) &&
        typeof node.id === "string" &&
        typeof node.kind === "string" &&
        typeof node.label === "string" &&
        typeof node.provider === "string" &&
        typeof node.chain === "string" &&
        typeof node.block_hash === "string" &&
        typeof node.block_height === "number" &&
        typeof node.observed_at === "string" &&
        typeof node.confidence === "string" &&
        (node.provider_rating === undefined || typeof node.provider_rating === "string") &&
        (node.report_reference === undefined || typeof node.report_reference === "string") &&
        (node.value_atomic === undefined || typeof node.value_atomic === "string") &&
        (node.unit === undefined || typeof node.unit === "string"),
    ) &&
    Array.isArray(value.edges) &&
    value.edges.every(
      (edge) =>
        isRecord(edge) &&
        typeof edge.source === "string" &&
        typeof edge.provider === "string" &&
        typeof edge.target === "string" &&
        typeof edge.relation === "string" &&
        typeof edge.chain === "string" &&
        typeof edge.block_hash === "string" &&
        typeof edge.block_height === "number" &&
        typeof edge.observed_at === "string" &&
        typeof edge.confidence === "string" &&
        (edge.provider_rating === undefined || typeof edge.provider_rating === "string") &&
        (edge.category === undefined || typeof edge.category === "string") &&
        (edge.report_reference === undefined || typeof edge.report_reference === "string") &&
        (edge.report_sha256 === undefined || typeof edge.report_sha256 === "string") &&
        (edge.assessed_at === undefined || typeof edge.assessed_at === "string") &&
        (edge.value_atomic === undefined || typeof edge.value_atomic === "string") &&
        (edge.unit === undefined || typeof edge.unit === "string"),
    ) &&
    Array.isArray(value.limitations) &&
    value.limitations.every((limitation) => typeof limitation === "string")
  );
}

function isOnChainSnapshot(value: unknown): value is OnChainSnapshot {
  return (
    isRecord(value) &&
    typeof value.snapshot_id === "string" &&
    (value.chain === "bitcoin" || value.chain === "ethereum") &&
    typeof value.height === "number" &&
    typeof value.block_hash === "string" &&
    (typeof value.parent_hash === "string" || value.parent_hash === null) &&
    typeof value.source === "string" &&
    typeof value.block_timestamp === "string" &&
    typeof value.fetched_at === "string" &&
    typeof value.stored_at === "string" &&
    typeof value.payload_bytes === "number"
  );
}

function isOnChainForensicsResult(value: unknown): value is OnChainForensicsResult {
  return (
    isRecord(value) &&
    typeof value.case_id === "string" &&
    isRecord(value.block) &&
    typeof value.block.height === "number" &&
    typeof value.block.block_hash === "string" &&
    typeof value.block.source === "string" &&
    typeof value.block.observed_at === "string" &&
    Array.isArray(value.logs) &&
    value.logs.every(
      (log) =>
        isRecord(log) &&
        typeof log.address === "string" &&
        Array.isArray(log.topics) &&
        log.topics.every((topic) => typeof topic === "string") &&
        typeof log.transaction_hash === "string" &&
        typeof log.log_index === "number" &&
        typeof log.removed === "boolean",
    ) &&
    Array.isArray(value.transfer_observations) &&
    value.transfer_observations.every(
      (transfer) =>
        isRecord(transfer) &&
        typeof transfer.token_contract === "string" &&
        typeof transfer.transaction_hash === "string" &&
        typeof transfer.log_index === "number" &&
        typeof transfer.from_address === "string" &&
        typeof transfer.to_address === "string" &&
        (typeof transfer.value_atomic === "string" || transfer.value_atomic === null) &&
        (typeof transfer.token_id === "string" || transfer.token_id === null) &&
        typeof transfer.confidence === "string",
    ) &&
    Array.isArray(value.provider_assessments) &&
    value.provider_assessments.every(
      (assessment) =>
        isRecord(assessment) &&
        typeof assessment.address === "string" &&
        typeof assessment.provider === "string" &&
        typeof assessment.provider_rating === "string" &&
        typeof assessment.verification_status === "string",
    ) &&
    isRecord(value.regulatory_assessment) &&
    typeof value.regulatory_assessment.status === "string" &&
    Array.isArray(value.regulatory_assessment.frameworks) &&
    value.regulatory_assessment.frameworks.every((framework) => typeof framework === "string") &&
    Array.isArray(value.limitations) &&
    value.limitations.every((limitation) => typeof limitation === "string")
  );
}

function isOnChainTraceResult(value: unknown): value is OnChainTraceResult {
  return (
    isRecord(value) &&
    typeof value.case_id === "string" &&
    typeof value.transaction_hash === "string" &&
    typeof value.block_hash === "string" &&
    typeof value.block_height === "number" &&
    typeof value.confidence === "string" &&
    isRecord(value.trace) &&
    typeof value.trace.call_type === "string" &&
    typeof value.trace.from_address === "string" &&
    (typeof value.trace.to_address === "string" || value.trace.to_address === null) &&
    typeof value.trace.value_atomic === "string" &&
    (typeof value.trace.gas_used === "string" || value.trace.gas_used === null) &&
    (typeof value.trace.input_selector === "string" || value.trace.input_selector === null) &&
    typeof value.trace.input_bytes === "number" &&
    Array.isArray(value.trace.calls) &&
    isRecord(value.regulatory_assessment) &&
    typeof value.regulatory_assessment.status === "string" &&
    Array.isArray(value.limitations) &&
    value.limitations.every((limitation) => typeof limitation === "string")
  );
}

function isRegulatoryChecklist(value: unknown): value is RegulatoryChecklist {
  return (
    isRecord(value) &&
    typeof value.case_id === "string" &&
    value.profile === "EU_CASP" &&
    typeof value.profile_version === "string" &&
    value.overall_status === "NOT_ASSESSED" &&
    Array.isArray(value.controls) &&
    value.controls.every(
      (control) =>
        isRecord(control) &&
        typeof control.control_id === "string" &&
        typeof control.framework === "string" &&
        typeof control.title === "string" &&
        typeof control.review_prompt === "string" &&
        typeof control.official_reference === "string" &&
        typeof control.source_url === "string" &&
        ["not_assessed", "in_scope", "out_of_scope", "needs_legal_review"].includes(
          String(control.applicability),
        ) &&
        ["not_assessed", "evidence_recorded", "needs_review"].includes(
          String(control.review_state),
        ) &&
        typeof control.summary === "string" &&
        (typeof control.updated_by === "string" || control.updated_by === null) &&
        typeof control.updated_at === "string" &&
        Array.isArray(control.evidence) &&
        control.evidence.every(
          (entry) =>
            isRecord(entry) &&
            typeof entry.evidence_id === "string" &&
            typeof entry.source === "string" &&
            typeof entry.reference === "string" &&
            typeof entry.sha256 === "string" &&
            typeof entry.recorded_by === "string" &&
            typeof entry.recorded_at === "string",
        ),
    ) &&
    Array.isArray(value.limitations) &&
    value.limitations.every((limitation) => typeof limitation === "string")
  );
}

function isControlCoverageRow(value: unknown): value is ControlCoverageRow {
  if (!isRecord(value)) return false;
  return (
    typeof value.mapping_id === "string" &&
    typeof value.catalog_version === "string" &&
    typeof value.control_id === "string" &&
    typeof value.framework === "string" &&
    typeof value.framework_version === "string" &&
    typeof value.source_reference === "string" &&
    typeof value.mapping_type === "string" &&
    typeof value.recorded_at === "string" &&
    typeof value.control_title === "string" &&
    ["verified", "failed", "needs_review", "not_assessed", "not_applicable"].includes(
      String(value.assessment_state),
    ) &&
    (typeof value.assessment_id === "string" || value.assessment_id === null) &&
    (typeof value.assessed_at === "string" || value.assessed_at === null) &&
    (typeof value.assessed_by === "string" || value.assessed_by === null) &&
    typeof value.evidence_reference_count === "number" &&
    (typeof value.assessment_catalog_version === "string" ||
      value.assessment_catalog_version === null) &&
    value.mapping_interpretation === "RELATED_NOT_EQUIVALENT"
  );
}

function isControlCoverageReport(value: unknown): value is ControlCoverageReport {
  return (
    isRecord(value) &&
    typeof value.catalog_version === "string" &&
    (typeof value.framework_filter === "string" || value.framework_filter === null) &&
    typeof value.mapping_count === "number" &&
    isRecord(value.state_counts) &&
    Object.values(value.state_counts).every((count) => typeof count === "number") &&
    Array.isArray(value.mappings) &&
    value.mappings.every(isControlCoverageRow) &&
    value.certification_status === "NOT_ASSESSED" &&
    Array.isArray(value.limitations) &&
    value.limitations.every((item) => typeof item === "string") &&
    typeof value.generated_at === "string" &&
    typeof value.report_sha256 === "string" &&
    /^[0-9a-f]{64}$/.test(value.report_sha256)
  );
}

function isNormalizedTelemetryEvent(value: unknown): value is NormalizedTelemetryEvent {
  return (
    isRecord(value) &&
    typeof value.event_id === "string" &&
    typeof value.source_id === "string" &&
    typeof value.event_type === "string" &&
    typeof value.observed_at === "string" &&
    (typeof value.reported_severity === "string" || value.reported_severity === null) &&
    (typeof value.detection_scenario_id === "string" || value.detection_scenario_id === null) &&
    (typeof value.detection_rule_id === "string" || value.detection_rule_id === null) &&
    typeof value.ingested_at === "string"
  );
}

type WorkbenchIncident = IncidentEvent | CorrelatedIncident;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isIncidentCase(value: unknown): value is IncidentCaseRecord {
  if (!isRecord(value)) return false;
  return (
    typeof value.case_id === "string" &&
    (typeof value.correlation_id === "string" || value.correlation_id === null) &&
    typeof value.title === "string" &&
    typeof value.summary === "string" &&
    typeof value.priority === "string" &&
    Array.isArray(value.priority_reasons) &&
    value.priority_reasons.every((reason) => typeof reason === "string") &&
    (value.status === "open" ||
      value.status === "in_progress" ||
      value.status === "resolved" ||
      value.status === "closed") &&
    (typeof value.assigned_to === "string" || value.assigned_to === null) &&
    typeof value.event_count === "number" &&
    typeof value.created_at === "string" &&
    typeof value.updated_at === "string" &&
    (value.notes === undefined || Array.isArray(value.notes)) &&
    (value.evidence === undefined || Array.isArray(value.evidence)) &&
    (value.purple_team_replays === undefined ||
      (Array.isArray(value.purple_team_replays) &&
        value.purple_team_replays.every(isPurpleTeamReplay)))
  );
}

function isPurpleTeamReplay(value: unknown): value is PurpleTeamReplay {
  if (!isRecord(value) || !isRecord(value.result)) return false;
  return (
    typeof value.replay_id === "string" &&
    typeof value.case_id === "string" &&
    typeof value.scenario_id === "string" &&
    typeof value.expected_rule_id === "string" &&
    typeof value.evaluated_by === "string" &&
    typeof value.created_at === "string" &&
    typeof value.result.detection_verified === "boolean" &&
    typeof value.result.status === "string" &&
    (isRecord(value.result.matched_alert) || value.result.matched_alert === null) &&
    value.result.execution_mode === "OFFLINE_EVALUATION_ONLY"
  );
}

async function sendCaseRequest(credential: string, path: string, init: RequestInit = {}): Promise<unknown> {
  const apiUrl = process.env.NEXT_PUBLIC_SANCTUM_API_URL ??
    `${window.location.protocol === "https:" ? "https:" : "http:"}//${window.location.hostname}:8000`;
  const isBearerToken = credential.startsWith("Bearer ");
  const response = await fetch(`${apiUrl.replace(/\/$/, "")}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(isBearerToken
        ? { Authorization: credential }
        : { "X-API-Key": credential }),
      ...init.headers,
    },
  });
  if (!response.ok) {
    const body = await response.text();
    let detail = body;
    try {
      const parsed: unknown = JSON.parse(body);
      if (isRecord(parsed) && typeof parsed.detail === "string") detail = parsed.detail;
    } catch {
      detail = body || response.statusText;
    }
    throw new Error(`API ${response.status}: ${detail}`);
  }
  return response.json();
}

function isCorrelatedIncident(value: unknown): value is CorrelatedIncident {
  if (!isRecord(value)) return false;
  return (
    typeof value.correlation_id === "string" &&
    typeof value.event_count === "number" &&
    typeof value.priority === "string" &&
    Array.isArray(value.priority_reasons) &&
    value.priority_reasons.every((reason) => typeof reason === "string") &&
    Array.isArray(value.timeline) &&
    value.timeline.every(
      (entry) =>
        isRecord(entry) &&
        typeof entry.event_id === "string" &&
        typeof entry.event_type === "string" &&
        (typeof entry.source === "string" || entry.source === null) &&
        (typeof entry.observed_at === "string" || entry.observed_at === null) &&
        (typeof entry.reported_severity === "string" || entry.reported_severity === null) &&
        (entry.detection_scenario_id === undefined ||
          typeof entry.detection_scenario_id === "string" ||
          entry.detection_scenario_id === null) &&
        (entry.detection_rule_id === undefined ||
          typeof entry.detection_rule_id === "string" ||
          entry.detection_rule_id === null),
    )
  );
}

function isCorrelationResult(value: unknown): value is { correlations: CorrelatedIncident[] } {
  return (
    isRecord(value) &&
    Array.isArray(value.correlations) &&
    value.correlations.every(isCorrelatedIncident)
  );
}

function isIncidentPlaybook(value: unknown): value is IncidentPlaybook {
  if (!isRecord(value)) return false;
  return (
    typeof value.plan_id === "string" &&
    typeof value.case_id === "string" &&
    (value.status === "simulated" ||
      value.status === "approved_for_manual_review" ||
      value.status === "rejected") &&
    typeof value.simulated_by === "string" &&
    isRecord(value.case_snapshot) &&
    Array.isArray(value.steps) &&
    value.steps.every(
      (step) =>
        isRecord(step) &&
        typeof step.step_id === "string" &&
        typeof step.title === "string" &&
        typeof step.description === "string" &&
        typeof step.basis === "string",
    ) &&
    Array.isArray(value.decisions) &&
    value.decisions.every(
      (decision) =>
        isRecord(decision) &&
        typeof decision.decision_id === "string" &&
        (decision.decision === "approve" || decision.decision === "reject") &&
        typeof decision.reviewer === "string" &&
        typeof decision.rationale === "string" &&
        typeof decision.created_at === "string",
    ) &&
    value.execution_status === "NOT_EXECUTED" &&
    typeof value.created_at === "string" &&
    typeof value.updated_at === "string"
  );
}

function isIncidentAuditRecord(value: unknown): value is IncidentAuditRecord {
  if (!isRecord(value)) return false;
  return (
    typeof value.audit_id === "string" &&
    typeof value.occurred_at === "string" &&
    (typeof value.credential_fingerprint === "string" ||
      value.credential_fingerprint === null) &&
    typeof value.action === "string" &&
    typeof value.outcome_code === "number" &&
    (value.record_type === "api_access" || value.record_type === "retention")
  );
}

function isPlaybookList(value: unknown): value is { playbooks: IncidentPlaybook[] } {
  return (
    isRecord(value) &&
    Array.isArray(value.playbooks) &&
    value.playbooks.every(isIncidentPlaybook)
  );
}

export default function WorkbenchPage() {
  const [incidents, setIncidents] = useState<WorkbenchIncident[]>([]);
  const [status, setStatus] = useState("CONNECTING");
  const [apiKey, setApiKey] = useState("");
  const [createdBy, setCreatedBy] = useState("");
  const [caseRecords, setCaseRecords] = useState<IncidentCaseRecord[]>([]);
  const [onchainGraphs, setOnchainGraphs] = useState<Record<string, OnChainGraph>>({});
  const [onchainQueryDrafts, setOnchainQueryDrafts] = useState<
    Record<string, { chain: "bitcoin" | "ethereum"; height: string }>
  >({});
  const [onchainSnapshots, setOnchainSnapshots] = useState<Record<string, OnChainSnapshot[]>>({});
  const [onchainSnapshotSelections, setOnchainSnapshotSelections] = useState<Record<string, string>>({});
  const [onchainForensics, setOnchainForensics] = useState<Record<string, OnChainForensicsResult>>({});
  const [onchainTraceDrafts, setOnchainTraceDrafts] = useState<Record<string, string>>({});
  const [onchainTraces, setOnchainTraces] = useState<Record<string, OnChainTraceResult>>({});
  const [regulatoryChecklists, setRegulatoryChecklists] = useState<Record<string, RegulatoryChecklist>>({});
  const [regulatoryDrafts, setRegulatoryDrafts] = useState<
    Record<string, {
      applicability: RegulatoryChecklistControl["applicability"];
      review_state: RegulatoryChecklistControl["review_state"];
      summary: string;
      evidence_source: string;
      evidence_reference: string;
      evidence_sha256: string;
    }>
  >({});
  const [onchainRiskReportDrafts, setOnchainRiskReportDrafts] = useState<Record<string, string>>({});
  const [caseMessage, setCaseMessage] = useState("");
  const [caseBusy, setCaseBusy] = useState(false);
  const [assigneeDrafts, setAssigneeDrafts] = useState<Record<string, string>>({});
  const [noteDrafts, setNoteDrafts] = useState<Record<string, string>>({});
  const [evidenceDrafts, setEvidenceDrafts] = useState<Record<string, string>>({});
  const [correlationEvents, setCorrelationEvents] = useState<CorrelationInputEvent[]>([]);
  const [eventDraft, setEventDraft] = useState({
    event_id: "",
    event_type: "",
    correlation_key: "",
    source: "",
    observed_at: "",
    severity: "",
  });
  const [playbooksByCase, setPlaybooksByCase] = useState<Record<string, IncidentPlaybook[]>>({});
  const [decisionDrafts, setDecisionDrafts] = useState<Record<string, string>>({});
  const [accessAuditRecords, setAccessAuditRecords] = useState<IncidentAuditRecord[]>([]);
  const [auditLimitations, setAuditLimitations] = useState("");
  const [syntheticScenarios, setSyntheticScenarios] = useState<SyntheticScenario[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState("");
  const [syntheticLimitations, setSyntheticLimitations] = useState("");
  const [telemetryCatalog, setTelemetryCatalog] = useState<TelemetryConnectorCatalog | null>(null);
  const [telemetryEvents, setTelemetryEvents] = useState<NormalizedTelemetryEvent[]>([]);
  const [telemetrySourceId, setTelemetrySourceId] = useState("");
  const [telemetryFormat, setTelemetryFormat] = useState("json");
  const [telemetryFileName, setTelemetryFileName] = useState("");
  const [telemetryFileContent, setTelemetryFileContent] = useState("");
  const [telemetryMessage, setTelemetryMessage] = useState("");
  const [purpleScenarioId, setPurpleScenarioId] = useState("");
  const [purpleExpectedRuleId, setPurpleExpectedRuleId] = useState("");
  const [controlCoverage, setControlCoverage] = useState<ControlCoverageReport | null>(null);
  const [coverageFramework, setCoverageFramework] = useState("");
  const [controlAssessmentDraft, setControlAssessmentDraft] = useState({
    control_id: "",
    state: "needs_review" as ControlCoverageRow["assessment_state"],
    summary: "",
    evidence_source: "",
    evidence_reference: "",
    evidence_sha256: "",
  });
  const telemetryFileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const configuredUrl = process.env.NEXT_PUBLIC_SANCTUM_WS_URL;
    const url = configuredUrl ?? `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.hostname}:8000/ws/incidents`;
    let socket: WebSocket;

    try {
      socket = new WebSocket(url);
    } catch {
      const errorTimer = window.setTimeout(() => setStatus("INVALID CONFIGURATION"), 0);
      return () => window.clearTimeout(errorTimer);
    }

    socket.onopen = () => setStatus("CONNECTED");
    socket.onclose = () => setStatus("DISCONNECTED");
    socket.onerror = () => setStatus("CONNECTION ERROR");
    socket.onmessage = (event: MessageEvent<string>) => {
      try {
        const data: unknown = JSON.parse(event.data);
        if (!isRecord(data)) return;
        let incident: WorkbenchIncident;
        if (isCorrelatedIncident(data)) {
          incident = data;
        } else if (typeof data.event === "string" && typeof data.source === "string") {
          incident = {
            event: data.event,
            source: data.source,
            severity: typeof data.severity === "string" ? data.severity : undefined,
            details: typeof data.details === "string" ? data.details : undefined,
          };
        } else {
          return;
        }
        setIncidents((previous) => [incident, ...previous].slice(0, 10));
      } catch {
        setStatus("INVALID EVENT");
      }
    };

    return () => socket.close();
  }, []);

  const connected = status === "CONNECTED";

  async function loadCases() {
    setCaseBusy(true);
    setCaseMessage("");
    try {
      const result: unknown = await sendCaseRequest(apiKey, "/api/v1/cases?limit=50");
      if (!isRecord(result) || !Array.isArray(result.cases) || !result.cases.every(isIncidentCase)) {
        throw new Error("The API returned an invalid case list.");
      }
      setCaseRecords(result.cases);
      setAssigneeDrafts(Object.fromEntries(result.cases.map((item) => [item.case_id, item.assigned_to ?? ""])));
      setCaseMessage(`Loaded ${result.cases.length} cases.`);
    } catch (error) {
      setCaseMessage(error instanceof Error ? error.message : "Unable to load cases.");
    } finally {
      setCaseBusy(false);
    }
  }

  async function createCase(incident: CorrelatedIncident) {
    if (!createdBy.trim()) {
      setCaseMessage("Enter your analyst name before creating a case.");
      return;
    }
    setCaseBusy(true);
    setCaseMessage("");
    try {
      const result: unknown = await sendCaseRequest(apiKey, "/api/v1/cases", {
        method: "POST",
        body: JSON.stringify({
          title: `${incident.priority} correlated incident`,
          ...(incident.synthetic
            ? {
                summary: `[SYNTHETIC DEMO · ${incident.scenario_title ?? incident.scenario_id ?? "scenario"}] ${incident.priority_reasons.join(" ")}`,
              }
            : {}),
          ...(!incident.synthetic
            ? { summary: incident.priority_reasons.join(" ") }
            : {}),
          created_by: createdBy,
          priority: incident.priority,
          correlation_id: incident.correlation_id,
          priority_reasons: incident.priority_reasons,
          timeline: incident.timeline,
        }),
      });
      if (!isIncidentCase(result)) throw new Error("The API returned an invalid case.");
      setCaseRecords((previous) => [result, ...previous.filter((item) => item.case_id !== result.case_id)]);
      setAssigneeDrafts((previous) => ({ ...previous, [result.case_id]: result.assigned_to ?? "" }));
      setCaseMessage(`Created case ${result.case_id}.`);
    } catch (error) {
      setCaseMessage(error instanceof Error ? error.message : "Unable to create case.");
    } finally {
      setCaseBusy(false);
    }
  }

  function addCorrelationEvent() {
    if (!eventDraft.event_id.trim() || !eventDraft.event_type.trim() || !eventDraft.correlation_key.trim()) {
      setCaseMessage("Event ID, event type, and correlation key are required.");
      return;
    }
    setCorrelationEvents((previous) => [
      ...previous,
      {
        event_id: eventDraft.event_id.trim(),
        event_type: eventDraft.event_type.trim(),
        correlation_key: eventDraft.correlation_key.trim(),
        ...(eventDraft.source.trim() ? { source: eventDraft.source.trim() } : {}),
        ...(eventDraft.observed_at
          ? { observed_at: new Date(eventDraft.observed_at).toISOString() }
          : {}),
        ...(eventDraft.severity ? { severity: eventDraft.severity } : {}),
      },
    ]);
    setEventDraft({
      event_id: "",
      event_type: "",
      correlation_key: "",
      source: "",
      observed_at: "",
      severity: "",
    });
    setCaseMessage("");
  }

  async function correlateEventBatch() {
    if (!apiKey || correlationEvents.length === 0) {
      setCaseMessage("Enter an API key and add at least one event.");
      return;
    }
    setCaseBusy(true);
    setCaseMessage("");
    try {
      const result: unknown = await sendCaseRequest(apiKey, "/api/v1/events/correlate", {
        method: "POST",
        body: JSON.stringify({ events: correlationEvents }),
      });
      if (!isCorrelationResult(result)) throw new Error("The API returned an invalid correlation result.");
      setIncidents((previous) => [...result.correlations, ...previous].slice(0, 10));
      setCaseMessage(
        result.correlations.length > 0
          ? `Created ${result.correlations.length} local correlation group(s).`
          : "No groups found. Add multiple events with the same exact correlation key.",
      );
    } catch (error) {
      setCaseMessage(error instanceof Error ? error.message : "Unable to correlate events.");
    } finally {
      setCaseBusy(false);
    }
  }

  async function updateCase(caseId: string, patch: { status?: IncidentCaseRecord["status"]; assigned_to?: string | null }) {
    setCaseBusy(true);
    setCaseMessage("");
    try {
      const result: unknown = await sendCaseRequest(apiKey, `/api/v1/cases/${encodeURIComponent(caseId)}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      });
      if (!isIncidentCase(result)) throw new Error("The API returned an invalid case.");
      setCaseRecords((previous) => previous.map((item) => item.case_id === caseId ? result : item));
      setCaseMessage(`Updated case ${caseId}.`);
    } catch (error) {
      setCaseMessage(error instanceof Error ? error.message : "Unable to update case.");
    } finally {
      setCaseBusy(false);
    }
  }

  async function loadCaseDetails(caseId: string) {
    setCaseBusy(true);
    setCaseMessage("");
    try {
      const result: unknown = await sendCaseRequest(apiKey, `/api/v1/cases/${encodeURIComponent(caseId)}`);
      if (!isIncidentCase(result)) throw new Error("The API returned an invalid case.");
      setCaseRecords((previous) => previous.map((item) => item.case_id === caseId ? result : item));
    } catch (error) {
      setCaseMessage(error instanceof Error ? error.message : "Unable to load case details.");
    } finally {
      setCaseBusy(false);
    }
  }

  async function loadOnChainGraph(
    caseId: string,
    query: { chain: "bitcoin" | "ethereum"; height: string },
    savedBlockHash?: string,
  ) {
    if (!query.height.trim() || !/^\d+$/.test(query.height.trim())) {
      setCaseMessage("Enter a non-negative block height.");
      return;
    }
    setCaseBusy(true);
    setCaseMessage("");
    try {
      const parameters = new URLSearchParams({
        chain: query.chain,
        height: query.height.trim(),
      });
      if (savedBlockHash) parameters.set("block_hash", savedBlockHash);
      const result: unknown = await sendCaseRequest(
        apiKey,
        `/api/v1/cases/${encodeURIComponent(caseId)}/onchain-graph?${parameters}`,
      );
      if (!isOnChainGraph(result) || result.case_id !== caseId) {
        throw new Error("The API returned an invalid on-chain graph.");
      }
      setOnchainGraphs((previous) => ({ ...previous, [caseId]: result }));
      setCaseMessage(
        result.storage.loaded_from_snapshot
          ? `Loaded saved ${result.chain} block ${result.block_height} for case ${caseId}.`
          : result.storage.inserted
            ? `Loaded and saved ${result.chain} block ${result.block_height} for case ${caseId}.`
            : `Loaded ${result.chain} block ${result.block_height} for case ${caseId}.`,
      );
    } catch (error) {
      setCaseMessage(error instanceof Error ? error.message : "Unable to load on-chain graph.");
    } finally {
      setCaseBusy(false);
    }
  }

  async function loadOnChainSnapshots(caseId: string) {
    setCaseBusy(true);
    setCaseMessage("");
    try {
      const result: unknown = await sendCaseRequest(
        apiKey,
        `/api/v1/cases/${encodeURIComponent(caseId)}/onchain-blocks?limit=100`,
      );
      const rawSnapshots =
        isRecord(result) && Array.isArray(result.snapshots)
          ? result.snapshots
          : null;
      const snapshots = rawSnapshots?.filter(isOnChainSnapshot) ?? null;
      if (
        !isRecord(result) ||
        rawSnapshots === null ||
        snapshots === null ||
        snapshots.length !== rawSnapshots.length
      ) {
        throw new Error("The API returned an invalid on-chain snapshot list.");
      }
      setOnchainSnapshots((previous) => ({
        ...previous,
        [caseId]: snapshots,
      }));
      setCaseMessage(`Loaded saved block list for case ${caseId}.`);
    } catch (error) {
      setCaseMessage(error instanceof Error ? error.message : "Unable to load saved on-chain snapshots.");
    } finally {
      setCaseBusy(false);
    }
  }

  async function loadOnChainForensics(caseId: string, height: string) {
    const normalizedHeight = height.trim();
    if (!/^\d+$/.test(normalizedHeight)) {
      setCaseMessage("Enter a non-negative Ethereum block height for forensic logs.");
      return;
    }
    setCaseBusy(true);
    setCaseMessage("");
    try {
      const parameters = new URLSearchParams({ height: normalizedHeight });
      const result: unknown = await sendCaseRequest(
        apiKey,
        `/api/v1/cases/${encodeURIComponent(caseId)}/onchain-forensics?${parameters}`,
      );
      if (!isOnChainForensicsResult(result) || result.case_id !== caseId) {
        throw new Error("The API returned an invalid Ethereum forensics result.");
      }
      setOnchainForensics((previous) => ({ ...previous, [caseId]: result }));
      setCaseMessage(
        `Loaded ${result.logs.length} Ethereum log(s) and ${result.transfer_observations.length} transfer-shaped observation(s).`,
      );
    } catch (error) {
      setCaseMessage(error instanceof Error ? error.message : "Unable to load Ethereum forensic logs.");
    } finally {
      setCaseBusy(false);
    }
  }

  async function loadOnChainTrace(caseId: string) {
    const transactionHash = onchainTraceDrafts[caseId]?.trim() ?? "";
    if (!/^0x[0-9a-fA-F]{64}$/.test(transactionHash)) {
      setCaseMessage("Enter a 32-byte Ethereum transaction hash.");
      return;
    }
    setCaseBusy(true);
    setCaseMessage("");
    try {
      const result: unknown = await sendCaseRequest(
        apiKey,
        `/api/v1/cases/${encodeURIComponent(caseId)}/onchain-traces/${encodeURIComponent(transactionHash)}`,
      );
      if (!isOnChainTraceResult(result) || result.case_id !== caseId) {
        throw new Error("The API returned an invalid Ethereum trace result.");
      }
      setOnchainTraces((previous) => ({ ...previous, [caseId]: result }));
      setCaseMessage(`Loaded bounded call trace for transaction ${transactionHash}.`);
    } catch (error) {
      setCaseMessage(error instanceof Error ? error.message : "Unable to load Ethereum trace.");
    } finally {
      setCaseBusy(false);
    }
  }

  async function loadRegulatoryChecklist(caseId: string) {
    setCaseBusy(true);
    setCaseMessage("");
    try {
      const result: unknown = await sendCaseRequest(
        apiKey,
        `/api/v1/cases/${encodeURIComponent(caseId)}/aml-mica-checklist`,
      );
      if (!isRegulatoryChecklist(result) || result.case_id !== caseId) {
        throw new Error("The API returned an invalid AML/MiCA checklist.");
      }
      setRegulatoryChecklists((previous) => ({ ...previous, [caseId]: result }));
      setCaseMessage(`Loaded the EU CASP regulatory-review checklist for case ${caseId}.`);
    } catch (error) {
      setCaseMessage(error instanceof Error ? error.message : "Unable to load AML/MiCA checklist.");
    } finally {
      setCaseBusy(false);
    }
  }

  async function updateRegulatoryControl(
    caseId: string,
    control: RegulatoryChecklistControl,
  ) {
    if (!createdBy.trim()) {
      setCaseMessage("Enter your analyst name before recording a regulatory review.");
      return;
    }
    const draftKey = `${caseId}:${control.control_id}`;
    const draft = regulatoryDrafts[draftKey];
    setCaseBusy(true);
    setCaseMessage("");
    try {
      const result: unknown = await sendCaseRequest(
        apiKey,
        `/api/v1/cases/${encodeURIComponent(caseId)}/aml-mica-checklist/${encodeURIComponent(control.control_id)}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            updated_by: createdBy.trim(),
            applicability: draft?.applicability ?? control.applicability,
            review_state: draft?.review_state ?? control.review_state,
            ...(draft?.summary.trim()
              ? { summary: draft.summary.trim() }
              : control.summary
                ? { summary: control.summary }
                : {}),
          }),
        },
      );
      if (!isRegulatoryChecklist(result) || result.case_id !== caseId) {
        throw new Error("The API returned an invalid AML/MiCA checklist update.");
      }
      setRegulatoryChecklists((previous) => ({ ...previous, [caseId]: result }));
      setCaseMessage(`Saved review metadata for ${control.control_id}; overall status remains NOT ASSESSED.`);
    } catch (error) {
      setCaseMessage(error instanceof Error ? error.message : "Unable to update the regulatory checklist.");
    } finally {
      setCaseBusy(false);
    }
  }

  async function addRegulatoryEvidence(
    caseId: string,
    control: RegulatoryChecklistControl,
  ) {
    if (!createdBy.trim()) {
      setCaseMessage("Enter your analyst name before recording evidence.");
      return;
    }
    const draftKey = `${caseId}:${control.control_id}`;
    const draft = regulatoryDrafts[draftKey];
    if (
      !draft?.evidence_source.trim() ||
      !draft.evidence_reference.trim() ||
      !/^[0-9a-f]{64}$/.test(draft.evidence_sha256.trim())
    ) {
      setCaseMessage("Enter an evidence source, reference, and lowercase SHA-256 digest.");
      return;
    }
    setCaseBusy(true);
    setCaseMessage("");
    try {
      const result: unknown = await sendCaseRequest(
        apiKey,
        `/api/v1/cases/${encodeURIComponent(caseId)}/aml-mica-checklist/${encodeURIComponent(control.control_id)}/evidence`,
        {
          method: "POST",
          body: JSON.stringify({
            source: draft.evidence_source.trim(),
            reference: draft.evidence_reference.trim(),
            sha256: draft.evidence_sha256.trim(),
            recorded_by: createdBy.trim(),
          }),
        },
      );
      if (!isRegulatoryChecklist(result) || result.case_id !== caseId) {
        throw new Error("The API returned an invalid AML/MiCA evidence record.");
      }
      setRegulatoryChecklists((previous) => ({ ...previous, [caseId]: result }));
      setRegulatoryDrafts((previous) => ({
        ...previous,
        [draftKey]: {
          ...draft,
          evidence_source: "",
          evidence_reference: "",
          evidence_sha256: "",
        },
      }));
      setCaseMessage("Added an evidence reference; no evidence file was uploaded and compliance remains NOT ASSESSED.");
    } catch (error) {
      setCaseMessage(error instanceof Error ? error.message : "Unable to record regulatory evidence.");
    } finally {
      setCaseBusy(false);
    }
  }

  async function selectOnChainRiskReport(caseId: string, file: File | undefined) {
    if (!file) {
      setOnchainRiskReportDrafts((previous) => ({ ...previous, [caseId]: "" }));
      return;
    }
    if (file.size > 1_000_000) {
      setCaseMessage("Risk report cannot exceed 1 MB.");
      return;
    }
    try {
      const content = await file.text();
      setOnchainRiskReportDrafts((previous) => ({ ...previous, [caseId]: content }));
      setCaseMessage(`Selected provider report ${file.name}; it has not been uploaded.`);
    } catch (error) {
      setCaseMessage(error instanceof Error ? error.message : "Unable to read provider report.");
    }
  }

  async function importOnChainRiskReport(caseId: string) {
    const content = onchainRiskReportDrafts[caseId];
    if (!content) {
      setCaseMessage("Select a normalized provider report file first.");
      return;
    }
    setCaseBusy(true);
    setCaseMessage("");
    try {
      const result: unknown = await sendCaseRequest(
        apiKey,
        `/api/v1/cases/${encodeURIComponent(caseId)}/onchain-risk/import`,
        {
          method: "POST",
          body: JSON.stringify({ content }),
        },
      );
      if (
        !isRecord(result) ||
        result.case_id !== caseId ||
        typeof result.report_sha256 !== "string" ||
        typeof result.record_count !== "number" ||
        typeof result.inserted_count !== "number" ||
        typeof result.duplicate_count !== "number" ||
        result.raw_report_persisted !== false ||
        result.status !== "IMPORTED_PROVIDER_REPORTS_UNVERIFIED"
      ) {
        throw new Error("The API returned an invalid provider report import result.");
      }
      setOnchainRiskReportDrafts((previous) => ({ ...previous, [caseId]: "" }));
      setCaseMessage(
        `Imported ${result.inserted_count} provider assessment(s); reload the graph to see matching labels. Report SHA-256 ${result.report_sha256}.`,
      );
    } catch (error) {
      setCaseMessage(error instanceof Error ? error.message : "Unable to import provider report.");
    } finally {
      setCaseBusy(false);
    }
  }

  async function runPurpleTeamReplay(caseId: string) {
    if (!createdBy.trim() || !purpleScenarioId.trim() || !purpleExpectedRuleId.trim()) {
      setCaseMessage("Enter your analyst name, scenario ID, and expected detection rule ID.");
      return;
    }
    setCaseBusy(true);
    setCaseMessage("");
    try {
      const result: unknown = await sendCaseRequest(
        apiKey,
        `/api/v1/cases/${encodeURIComponent(caseId)}/purple-team/replays`,
        {
          method: "POST",
          body: JSON.stringify({
            scenario_id: purpleScenarioId.trim(),
            expected_rule_id: purpleExpectedRuleId.trim(),
            evaluated_by: createdBy.trim(),
          }),
        },
      );
      if (!isPurpleTeamReplay(result)) {
        throw new Error("The API returned an invalid Purple Team replay.");
      }
      setCaseRecords((previous) =>
        previous.map((item) =>
          item.case_id === caseId
            ? {
                ...item,
                purple_team_replays: [
                  ...(item.purple_team_replays ?? []),
                  result,
                ],
              }
            : item,
        ),
      );
      setCaseMessage(
        result.result.detection_verified
          ? "Expected detection metadata found in the recorded case timeline."
          : "Expected detection metadata not found in the recorded case timeline.",
      );
    } catch (error) {
      setCaseMessage(error instanceof Error ? error.message : "Unable to run Purple Team replay.");
    } finally {
      setCaseBusy(false);
    }
  }

  async function downloadCaseReport(caseId: string) {
    setCaseBusy(true);
    setCaseMessage("");
    try {
      const report: unknown = await sendCaseRequest(
        apiKey,
        `/api/v1/cases/${encodeURIComponent(caseId)}/report`,
      );
      if (
        !isRecord(report) ||
        report.schema_version !== "1.0" ||
        typeof report.report_sha256 !== "string" ||
        !/^[0-9a-f]{64}$/.test(report.report_sha256)
      ) {
        throw new Error("The API returned an invalid case report.");
      }
      const blob = new Blob([JSON.stringify(report, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `sanctum-case-${caseId}.json`;
      link.click();
      URL.revokeObjectURL(url);
      setCaseMessage(`Downloaded report for case ${caseId}.`);
    } catch (error) {
      setCaseMessage(error instanceof Error ? error.message : "Unable to export case report.");
    } finally {
      setCaseBusy(false);
    }
  }

  async function loadCasePlaybooks(caseId: string) {
    setCaseBusy(true);
    setCaseMessage("");
    try {
      const result: unknown = await sendCaseRequest(
        apiKey,
        `/api/v1/cases/${encodeURIComponent(caseId)}/playbooks`,
      );
      if (!isPlaybookList(result)) {
        throw new Error("The API returned an invalid playbook list.");
      }
      setPlaybooksByCase((previous) => ({ ...previous, [caseId]: result.playbooks }));
      setCaseMessage(`Loaded ${result.playbooks.length} simulated playbook(s).`);
    } catch (error) {
      setCaseMessage(error instanceof Error ? error.message : "Unable to load playbooks.");
    } finally {
      setCaseBusy(false);
    }
  }

  async function loadAccessAudit() {
    setCaseBusy(true);
    setCaseMessage("");
    try {
      const result: unknown = await sendCaseRequest(
        apiKey,
        "/api/v1/governance/access-log?limit=100",
      );
      if (
        !isRecord(result) ||
        !Array.isArray(result.records) ||
        !result.records.every(isIncidentAuditRecord) ||
        typeof result.limitations !== "string"
      ) {
        throw new Error("The API returned an invalid access audit.");
      }
      setAccessAuditRecords(result.records);
      setAuditLimitations(result.limitations);
      setCaseMessage(`Loaded ${result.records.length} access audit records.`);
    } catch (error) {
      setCaseMessage(error instanceof Error ? error.message : "Unable to load access audit.");
    } finally {
      setCaseBusy(false);
    }
  }

  async function loadSyntheticScenarios() {
    setCaseBusy(true);
    setCaseMessage("");
    try {
      const result: unknown = await sendCaseRequest(apiKey, "/api/v1/lab/scenarios");
      if (!isSyntheticScenarioCatalog(result)) {
        throw new Error("The API returned an invalid synthetic scenario catalog.");
      }
      setSyntheticScenarios(result.scenarios);
      setSelectedScenarioId((current) => current || result.scenarios[0]?.scenario_id || "");
      setSyntheticLimitations("");
      setCaseMessage(`Loaded ${result.scenarios.length} synthetic training scenarios.`);
    } catch (error) {
      setCaseMessage(error instanceof Error ? error.message : "Unable to load synthetic scenarios.");
    } finally {
      setCaseBusy(false);
    }
  }

  async function runSyntheticScenario() {
    if (!selectedScenarioId) {
      setCaseMessage("Select a synthetic scenario first.");
      return;
    }
    setCaseBusy(true);
    setCaseMessage("");
    try {
      const result: unknown = await sendCaseRequest(
        apiKey,
        `/api/v1/lab/scenarios/${encodeURIComponent(selectedScenarioId)}/run`,
        { method: "POST" },
      );
      if (!isSyntheticRun(result)) throw new Error("The API returned an invalid synthetic run.");
      setIncidents((previous) => [...result.correlations, ...previous].slice(0, 10));
      setSyntheticLimitations(result.limitations);
      setCaseMessage(
        `Generated ${result.events.length} synthetic events. Nothing was persisted or executed.`,
      );
    } catch (error) {
      setCaseMessage(error instanceof Error ? error.message : "Unable to run synthetic scenario.");
    } finally {
      setCaseBusy(false);
    }
  }

  async function loadTelemetryWorkbench() {
    setCaseBusy(true);
    setTelemetryMessage("");
    try {
      const [catalogResult, eventResult]: unknown[] = await Promise.all([
        sendCaseRequest(apiKey, "/api/v1/telemetry/connectors"),
        sendCaseRequest(apiKey, "/api/v1/telemetry/events?limit=100"),
      ]);
      if (!isTelemetryConnectorCatalog(catalogResult)) {
        throw new Error("The API returned an invalid telemetry connector catalog.");
      }
      if (
        !isRecord(eventResult) ||
        !Array.isArray(eventResult.events) ||
        !eventResult.events.every(isNormalizedTelemetryEvent)
      ) {
        throw new Error("The API returned an invalid telemetry event list.");
      }
      setTelemetryCatalog(catalogResult);
      setTelemetryEvents(eventResult.events);
      setTelemetrySourceId((current) =>
        catalogResult.sources.some((source) => source.source_id === current)
          ? current
          : catalogResult.sources[0]?.source_id ?? "",
      );
      setTelemetryMessage(
        `Loaded ${catalogResult.sources.length} configured source(s) and ${eventResult.events.length} recent event(s).`,
      );
    } catch (error) {
      setTelemetryMessage(
        error instanceof Error ? error.message : "Unable to load telemetry configuration.",
      );
    } finally {
      setCaseBusy(false);
    }
  }

  async function loadControlCoverage(): Promise<boolean> {
    setCaseBusy(true);
    setCaseMessage("");
    try {
      const result: unknown = await sendCaseRequest(
        apiKey,
        "/api/v1/controls/coverage",
      );
      if (!isControlCoverageReport(result)) {
        throw new Error("The API returned an invalid control coverage report.");
      }
      setControlCoverage(result);
      setControlAssessmentDraft((previous) => ({
        ...previous,
        control_id:
          result.mappings.find((mapping) => mapping.assessment_state === "not_assessed")
            ?.control_id ?? result.mappings[0]?.control_id ?? "",
      }));
      setCaseMessage(
        `Loaded ${result.mapping_count} related mapping(s) from catalog ${result.catalog_version}.`,
      );
      return true;
    } catch (error) {
      setCaseMessage(error instanceof Error ? error.message : "Unable to load control coverage.");
      return false;
    } finally {
      setCaseBusy(false);
    }
  }

  async function submitControlAssessment() {
    const draft = controlAssessmentDraft;
    if (!createdBy.trim() || !draft.control_id || !draft.summary.trim()) {
      setCaseMessage("Enter your assessor name, select a control, and provide an assessment summary.");
      return;
    }
    const evidenceValues = [
      draft.evidence_source.trim(),
      draft.evidence_reference.trim(),
      draft.evidence_sha256.trim(),
    ];
    const hasEvidence = evidenceValues.some(Boolean);
    if (
      hasEvidence &&
      evidenceValues.some((value) => !value)
    ) {
      setCaseMessage("Provide the evidence source, reference, and SHA-256 digest together.");
      return;
    }
    if (draft.state === "verified" && !hasEvidence) {
      setCaseMessage("A verified assessment requires an evidence reference and digest.");
      return;
    }
    setCaseBusy(true);
    setCaseMessage("");
    try {
      const result: unknown = await sendCaseRequest(
        apiKey,
        `/api/v1/controls/${encodeURIComponent(draft.control_id)}/assessments`,
        {
          method: "POST",
          body: JSON.stringify({
            state: draft.state,
            summary: draft.summary.trim(),
            assessed_by: createdBy.trim(),
            evidence: hasEvidence
              ? [
                  {
                    source: draft.evidence_source.trim(),
                    reference: draft.evidence_reference.trim(),
                    sha256: draft.evidence_sha256.trim(),
                  },
                ]
              : [],
          }),
        },
      );
      if (!isRecord(result) || typeof result.assessment_id !== "string") {
        throw new Error("The API returned an invalid control assessment.");
      }
      setControlAssessmentDraft((previous) => ({ ...previous, summary: "" }));
      if (!(await loadControlCoverage())) {
        throw new Error("Assessment saved, but the refreshed coverage report could not be loaded.");
      }
      setCaseMessage(`Recorded assessment ${result.assessment_id}.`);
    } catch (error) {
      setCaseMessage(error instanceof Error ? error.message : "Unable to record assessment.");
    } finally {
      setCaseBusy(false);
    }
  }

  async function selectTelemetryFile(file: File | undefined) {
    clearTelemetrySelection();
    if (!file) return;
    if (file.size > 4_000_000) {
      setTelemetryMessage("Select a file no larger than 4 MB.");
      return;
    }
    const extension = file.name.split(".").pop()?.toLowerCase();
    const format =
      extension === "jsonl" || extension === "ndjson"
        ? "jsonl"
        : extension === "cef"
          ? "cef"
          : extension === "json"
            ? "json"
            : "";
    if (!format) {
      setTelemetryMessage("Choose a JSON, JSONL, or CEF file.");
      if (telemetryFileInput.current) telemetryFileInput.current.value = "";
      return;
    }
    try {
      const content = await file.text();
      setTelemetryFormat(format);
      setTelemetryFileName(file.name);
      setTelemetryFileContent(content);
      setTelemetryMessage("");
    } catch {
      setTelemetryMessage("The selected file could not be read.");
      if (telemetryFileInput.current) telemetryFileInput.current.value = "";
    }
  }

  function clearTelemetrySelection() {
    setTelemetryFileName("");
    setTelemetryFileContent("");
    if (telemetryFileInput.current) telemetryFileInput.current.value = "";
  }

  async function importTelemetryFile() {
    if (!apiKey || !telemetrySourceId || !telemetryFileContent) {
      setTelemetryMessage("Load configured sources, select a source, and choose a file.");
      return;
    }
    setCaseBusy(true);
    setTelemetryMessage("");
    try {
      const result: unknown = await sendCaseRequest(apiKey, "/api/v1/telemetry/import", {
        method: "POST",
        body: JSON.stringify({
          source_id: telemetrySourceId,
          format: telemetryFormat,
          content: telemetryFileContent,
        }),
      });
      if (
        !isRecord(result) ||
        typeof result.inserted_count !== "number" ||
        typeof result.duplicate_count !== "number" ||
        result.raw_payload_persisted !== false
      ) {
        throw new Error("The API returned an invalid telemetry import result.");
      }
      const eventResult: unknown = await sendCaseRequest(
        apiKey,
        "/api/v1/telemetry/events?limit=100",
      );
      if (
        !isRecord(eventResult) ||
        !Array.isArray(eventResult.events) ||
        !eventResult.events.every(isNormalizedTelemetryEvent)
      ) {
        throw new Error("The import succeeded, but the API returned an invalid event list.");
      }
      setTelemetryEvents(eventResult.events);
      setTelemetryMessage(
        `Imported ${result.inserted_count} event(s); ${result.duplicate_count} duplicate(s) skipped. File content was cleared from page memory.`,
      );
    } catch (error) {
      setTelemetryMessage(
        error instanceof Error ? error.message : "Unable to import telemetry file.",
      );
    } finally {
      clearTelemetrySelection();
      setCaseBusy(false);
    }
  }

  async function correlatePersistedTelemetry() {
    setCaseBusy(true);
    setTelemetryMessage("");
    try {
      const result: unknown = await sendCaseRequest(
        apiKey,
        "/api/v1/telemetry/correlate?window_hours=24",
        { method: "POST" },
      );
      if (
        !isCorrelationResult(result) ||
        !result.correlations.every(isCorrelatedIncident)
      ) {
        throw new Error("The API returned an invalid telemetry correlation result.");
      }
      setIncidents((previous) => [...result.correlations, ...previous].slice(0, 10));
      setTelemetryMessage(
        `Found ${result.correlations.length} correlation group(s). Grouping is exact-token only, not a threat assessment.`,
      );
    } catch (error) {
      setTelemetryMessage(
        error instanceof Error ? error.message : "Unable to correlate stored telemetry.",
      );
    } finally {
      setCaseBusy(false);
    }
  }

  async function simulateCasePlaybook(caseId: string) {
    if (!createdBy.trim()) {
      setCaseMessage("Enter your analyst name before simulating a playbook.");
      return;
    }
    setCaseBusy(true);
    setCaseMessage("");
    try {
      const result: unknown = await sendCaseRequest(
        apiKey,
        `/api/v1/cases/${encodeURIComponent(caseId)}/playbooks/simulate`,
        {
          method: "POST",
          body: JSON.stringify({ simulated_by: createdBy }),
        },
      );
      if (!isIncidentPlaybook(result)) throw new Error("The API returned an invalid playbook.");
      setPlaybooksByCase((previous) => ({
        ...previous,
        [caseId]: [result, ...(previous[caseId] ?? [])],
      }));
      setCaseMessage("Simulated a recommendation-only playbook. No actions were executed.");
    } catch (error) {
      setCaseMessage(error instanceof Error ? error.message : "Unable to simulate playbook.");
    } finally {
      setCaseBusy(false);
    }
  }

  async function decideCasePlaybook(
    plan: IncidentPlaybook,
    decision: "approve" | "reject",
  ) {
    const rationale = decisionDrafts[plan.plan_id]?.trim();
    if (!createdBy.trim() || !rationale) {
      setCaseMessage("Enter your reviewer name and a decision rationale.");
      return;
    }
    setCaseBusy(true);
    setCaseMessage("");
    try {
      const result: unknown = await sendCaseRequest(
        apiKey,
        `/api/v1/playbooks/${encodeURIComponent(plan.plan_id)}/decisions`,
        {
          method: "POST",
          body: JSON.stringify({
            decision,
            reviewer: createdBy,
            rationale,
          }),
        },
      );
      if (!isIncidentPlaybook(result)) throw new Error("The API returned an invalid playbook.");
      setPlaybooksByCase((previous) => ({
        ...previous,
        [plan.case_id]: (previous[plan.case_id] ?? []).map((item) =>
          item.plan_id === plan.plan_id ? result : item,
        ),
      }));
      setDecisionDrafts((previous) => ({ ...previous, [plan.plan_id]: "" }));
      setCaseMessage(
        decision === "approve"
          ? "Approved for manual review only. No response action was executed."
          : "Playbook rejected; the decision was recorded.",
      );
    } catch (error) {
      setCaseMessage(error instanceof Error ? error.message : "Unable to record playbook decision.");
    } finally {
      setCaseBusy(false);
    }
  }

  async function addCaseNote(caseId: string) {
    const body = noteDrafts[caseId]?.trim();
    if (!body || !createdBy.trim()) {
      setCaseMessage("Enter your analyst name and a note.");
      return;
    }
    await appendCaseActivity(caseId, "notes", { author: createdBy, body });
    setNoteDrafts((previous) => ({ ...previous, [caseId]: "" }));
  }

  async function addCaseEvidence(caseId: string) {
    const reference = evidenceDrafts[caseId]?.trim();
    if (!reference || !createdBy.trim()) {
      setCaseMessage("Enter your analyst name and an evidence reference.");
      return;
    }
    await appendCaseActivity(caseId, "evidence", {
      source: "operator-reference",
      reference,
      added_by: createdBy,
    });
    setEvidenceDrafts((previous) => ({ ...previous, [caseId]: "" }));
  }

  async function appendCaseActivity(
    caseId: string,
    activity: "notes" | "evidence",
    payload: Record<string, string>,
  ) {
    setCaseBusy(true);
    setCaseMessage("");
    try {
      const result: unknown = await sendCaseRequest(
        apiKey,
        `/api/v1/cases/${encodeURIComponent(caseId)}/${activity}`,
        { method: "POST", body: JSON.stringify(payload) },
      );
      if (!isIncidentCase(result)) throw new Error("The API returned an invalid case.");
      setCaseRecords((previous) => previous.map((item) => item.case_id === caseId ? result : item));
      setCaseMessage(`Added ${activity === "notes" ? "note" : "evidence reference"} to ${caseId}.`);
    } catch (error) {
      setCaseMessage(error instanceof Error ? error.message : "Unable to update case activity.");
    } finally {
      setCaseBusy(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 p-6 font-mono text-slate-100 md:p-8">
      <header className="mb-8 flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-cyan-400">SANCTUM-SUITE SOC Workbench</h1>
          <p className="text-xs text-slate-400">Operational dashboard preview</p>
        </div>
        <div className="flex items-center gap-2" role="status" aria-live="polite">
          <span className={`h-3 w-3 rounded-full ${connected ? "animate-pulse bg-emerald-500" : "bg-rose-500"}`} />
          <span className="text-xs font-semibold">{status}</span>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {[
          ["Overall Score", "No live score configured"],
          ["Guardrails", "View module configuration"],
          ["MITRE Mapping", "Based on available events"],
        ].map(([label, value]) => (
          <section key={label} className="rounded-lg border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-xs uppercase tracking-wider text-slate-400">{label}</h2>
            <p className="mt-3 text-lg font-bold text-cyan-300">{value}</p>
          </section>
        ))}
        <section className="rounded-lg border border-slate-800 bg-slate-900 p-6 md:col-span-3">
          <h2 className="text-sm font-semibold text-slate-200">On-chain case investigations</h2>
          <p className="mt-2 text-xs text-slate-400">
            Query a block from an operator-configured, read-only node inside an authenticated case. Graphs are not retained and show direct RPC observations only.
          </p>
        </section>
        <section className="mt-4 rounded-lg border border-slate-800 bg-slate-900 p-6 md:col-span-3">
          <div className="flex flex-wrap items-end gap-4">
            <label className="min-w-64 flex-1 text-xs text-slate-300">
              API key or OIDC bearer token (prefix token with &quot;Bearer &quot;; held in memory only)
              <input
                type="password"
                autoComplete="off"
                value={apiKey}
                onChange={(event) => setApiKey(event.target.value)}
                className="mt-2 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
              />
            </label>
            <label className="min-w-48 text-xs text-slate-300">
              Analyst name
              <input
                value={createdBy}
                onChange={(event) => setCreatedBy(event.target.value)}
                className="mt-2 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
              />
            </label>
            <button
              type="button"
              disabled={!apiKey || caseBusy}
              onClick={() => void loadCases()}
              className="rounded bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-50"
            >
              Load cases
            </button>
          </div>
          <h2 className="mb-4 mt-7 text-sm font-semibold text-slate-300">Incident cases</h2>
          {caseMessage && <p className="mb-4 text-xs text-cyan-200" role="status">{caseMessage}</p>}
          <div className="mb-5 rounded border border-violet-900/60 bg-violet-950/20 p-4">
            <div className="flex flex-wrap items-end gap-3">
              <div className="min-w-64 flex-1">
                <h3 className="font-semibold text-violet-200">Synthetic incident lab</h3>
                <p className="mt-1 text-xs text-slate-400">Fictional training data only; no external connections, persistence, or response actions.</p>
              </div>
              <button type="button" disabled={!apiKey || caseBusy} onClick={() => void loadSyntheticScenarios()} className="rounded border border-violet-800 px-3 py-2 text-violet-200 disabled:opacity-50">Load scenarios</button>
              {syntheticScenarios.length > 0 && (
                <>
                  <select aria-label="Synthetic scenario" value={selectedScenarioId} disabled={caseBusy} onChange={(event) => setSelectedScenarioId(event.target.value)} className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100">
                    {syntheticScenarios.map((scenario) => <option key={scenario.scenario_id} value={scenario.scenario_id}>{scenario.title}</option>)}
                  </select>
                  <button type="button" disabled={!apiKey || caseBusy || !selectedScenarioId} onClick={() => void runSyntheticScenario()} className="rounded bg-violet-400 px-3 py-2 font-semibold text-slate-950 disabled:opacity-50">Run demo</button>
                </>
              )}
            </div>
            {syntheticScenarios.find((scenario) => scenario.scenario_id === selectedScenarioId) && (
              <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-slate-400">
                {syntheticScenarios.find((scenario) => scenario.scenario_id === selectedScenarioId)?.learning_objectives.map((objective) => <li key={objective}>{objective}</li>)}
              </ul>
            )}
            {syntheticLimitations && <p className="mt-3 text-xs text-violet-200">{syntheticLimitations}</p>}
          </div>
          <div className="mb-5 rounded border border-amber-900/60 bg-amber-950/20 p-4">
            <div className="flex flex-wrap items-end gap-3">
              <div className="min-w-64 flex-1">
                <h3 className="font-semibold text-amber-200">Versioned control coverage</h3>
                <p className="mt-1 text-xs text-slate-400">
                  Operator-entered assessments and related source mappings; not a compliance or certification result.
                </p>
              </div>
              <label className="text-xs text-slate-400">
                Framework filter
                <select
                  aria-label="Control coverage framework"
                  value={coverageFramework}
                  disabled={caseBusy}
                  onChange={(event) => setCoverageFramework(event.target.value)}
                  className="ml-2 rounded border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100"
                >
                  <option value="">All mapped frameworks</option>
                  {[...new Set((controlCoverage?.mappings ?? []).map((item) => item.framework))]
                    .sort()
                    .map((framework) => <option key={framework} value={framework}>{framework}</option>)}
                </select>
              </label>
              <button
                type="button"
                disabled={!apiKey || caseBusy}
                onClick={() => void loadControlCoverage()}
                className="rounded border border-amber-800 px-3 py-2 text-amber-200 disabled:opacity-50"
              >
                Load coverage report
              </button>
            </div>
            {controlCoverage && (
              <>
                <p className="mt-3 text-xs text-slate-300">
                  Catalog v{controlCoverage.catalog_version} · {controlCoverage.mapping_count} related mappings
                  {" · "}not assessed: {controlCoverage.state_counts.not_assessed ?? 0}
                  {" · "}certification: {controlCoverage.certification_status}
                </p>
                <div className="mt-3 max-h-56 overflow-auto rounded border border-slate-800 bg-slate-950 p-3">
                  <ul className="space-y-2 text-xs text-slate-400">
                    {controlCoverage.mappings
                      .filter((mapping) => !coverageFramework || mapping.framework === coverageFramework)
                      .map((mapping) => (
                      <li key={mapping.mapping_id}>
                        <span className="text-slate-200">{mapping.control_id} · {mapping.control_title}</span>
                        {" → "}{mapping.framework} {mapping.framework_version}: {mapping.source_reference}
                        {" · "}<span className={mapping.assessment_state === "not_assessed" ? "text-amber-300" : "text-cyan-200"}>
                          {mapping.assessment_state}
                        </span>
                        {mapping.assessment_id
                          ? ` · ${mapping.evidence_reference_count} evidence reference(s) · ${mapping.assessed_at}`
                          : ""}
                        {" · RELATED, not equivalent"}
                      </li>
                      ))}
                  </ul>
                </div>
                <p className="mt-2 break-all text-[10px] text-slate-500">
                  Report SHA-256 {controlCoverage.report_sha256} · generated {controlCoverage.generated_at}
                </p>
                <div className="mt-4 border-t border-slate-800 pt-3">
                  <h4 className="text-xs font-semibold text-slate-200">Record control assessment</h4>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    <label className="text-xs text-slate-400">
                      Control
                      <select
                        aria-label="Control to assess"
                        value={controlAssessmentDraft.control_id}
                        disabled={caseBusy}
                        onChange={(event) => setControlAssessmentDraft((previous) => ({ ...previous, control_id: event.target.value }))}
                        className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100"
                      >
                        {[...new Map(controlCoverage.mappings
                          .filter((item) => !coverageFramework || item.framework === coverageFramework)
                          .map((item) => [item.control_id, item])).values()]
                          .map((item) => <option key={item.control_id} value={item.control_id}>{item.control_id} · {item.control_title}</option>)}
                      </select>
                    </label>
                    <label className="text-xs text-slate-400">
                      Assessment state
                      <select
                        aria-label="Assessment state"
                        value={controlAssessmentDraft.state}
                        disabled={caseBusy}
                        onChange={(event) => setControlAssessmentDraft((previous) => ({ ...previous, state: event.target.value as ControlCoverageRow["assessment_state"] }))}
                        className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100"
                      >
                        {["verified", "failed", "needs_review", "not_assessed", "not_applicable"].map((state) => <option key={state} value={state}>{state}</option>)}
                      </select>
                    </label>
                    <label className="text-xs text-slate-400 sm:col-span-2">
                      Assessment summary
                      <textarea
                        aria-label="Assessment summary"
                        value={controlAssessmentDraft.summary}
                        disabled={caseBusy}
                        onChange={(event) => setControlAssessmentDraft((previous) => ({ ...previous, summary: event.target.value }))}
                        maxLength={4000}
                        rows={2}
                        className="mt-1 w-full rounded border border-slate-700 bg-slate-950 p-2 text-slate-100"
                      />
                    </label>
                    <input
                      aria-label="Evidence source"
                      placeholder="Evidence source"
                      value={controlAssessmentDraft.evidence_source}
                      disabled={caseBusy}
                      onChange={(event) => setControlAssessmentDraft((previous) => ({ ...previous, evidence_source: event.target.value }))}
                      className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-xs"
                    />
                    <input
                      aria-label="Evidence reference"
                      placeholder="Evidence reference (no file upload)"
                      value={controlAssessmentDraft.evidence_reference}
                      disabled={caseBusy}
                      onChange={(event) => setControlAssessmentDraft((previous) => ({ ...previous, evidence_reference: event.target.value }))}
                      className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-xs"
                    />
                    <input
                      aria-label="Evidence SHA-256"
                      placeholder="Evidence SHA-256 (64 lowercase hex)"
                      value={controlAssessmentDraft.evidence_sha256}
                      disabled={caseBusy}
                      onChange={(event) => setControlAssessmentDraft((previous) => ({ ...previous, evidence_sha256: event.target.value }))}
                      className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-xs sm:col-span-2"
                    />
                  </div>
                  <button
                    type="button"
                    disabled={!apiKey || !createdBy.trim() || caseBusy || !controlCoverage.mappings.length}
                    onClick={() => void submitControlAssessment()}
                    className="mt-2 rounded bg-amber-300 px-3 py-2 text-xs font-semibold text-slate-950 disabled:opacity-50"
                  >
                    Save assessment
                  </button>
                </div>
                <ul className="mt-3 list-disc space-y-1 pl-5 text-[10px] text-slate-500">
                  {controlCoverage.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
                </ul>
              </>
            )}
          </div>
          <div className="mb-5 rounded border border-teal-900/60 bg-teal-950/20 p-4">
            <div className="flex flex-wrap items-end gap-3">
              <div className="min-w-64 flex-1">
                <h3 className="font-semibold text-teal-200">Configured telemetry sources</h3>
                <p className="mt-1 text-xs text-slate-400">
                  Normalized source data only. Push secrets stay server-side; pull connectors are not activated by default.
                </p>
              </div>
              <button
                type="button"
                disabled={!apiKey || caseBusy}
                onClick={() => void loadTelemetryWorkbench()}
                className="rounded border border-teal-800 px-3 py-2 text-teal-200 disabled:opacity-50"
              >
                Load telemetry
              </button>
              <button
                type="button"
                disabled={!apiKey || caseBusy}
                onClick={() => void correlatePersistedTelemetry()}
                className="rounded bg-teal-400 px-3 py-2 font-semibold text-slate-950 disabled:opacity-50"
              >
                Correlate stored events
              </button>
            </div>
            {telemetryCatalog && (
              <div className="mt-3 text-xs text-slate-400">
                <p>
                  {telemetryCatalog.push_ingestion_enabled
                    ? `Ingestion enabled · retention ${telemetryCatalog.event_retention_days} days`
                    : "Ingestion disabled · configure source credentials and event retention on the API server"}
                  {" · "}formats: {telemetryCatalog.file_formats.join(", ") || "none"}
                  {" · "}pull adapters: {telemetryCatalog.pull_adapters.join(", ") || "none registered"}
                </p>
                <p className="mt-1">{telemetryCatalog.limitations}</p>
              </div>
            )}
            <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              <label className="text-xs text-slate-400">
                Configured source
                <select
                  aria-label="Telemetry source"
                  value={telemetrySourceId}
                  disabled={caseBusy || !telemetryCatalog?.sources.length}
                  onChange={(event) => setTelemetrySourceId(event.target.value)}
                  className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100"
                >
                  {telemetryCatalog?.sources.length ? (
                    telemetryCatalog.sources.map((source) => (
                      <option key={source.source_id} value={source.source_id}>
                        {source.source_id}
                      </option>
                    ))
                  ) : (
                    <option value="">Load configured sources</option>
                  )}
                </select>
              </label>
              <label className="text-xs text-slate-400">
                File format
                <select
                  aria-label="Telemetry file format"
                  value={telemetryFormat}
                  disabled={caseBusy}
                  onChange={(event) => setTelemetryFormat(event.target.value)}
                  className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100"
                >
                  {["json", "jsonl", "cef"].map((format) => (
                    <option key={format} value={format}>{format.toUpperCase()}</option>
                  ))}
                </select>
              </label>
              <label className="text-xs text-slate-400 sm:col-span-2">
                Import file (maximum 4 MB)
                <input
                  ref={telemetryFileInput}
                  type="file"
                  accept=".json,.jsonl,.ndjson,.cef"
                  disabled={caseBusy}
                  onChange={(event) => void selectTelemetryFile(event.currentTarget.files?.[0])}
                  className="mt-1 block w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 text-slate-300"
                />
              </label>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              {telemetryFileName && (
                <>
                  <span className="text-xs text-slate-400">Selected: {telemetryFileName}</span>
                  <button
                    type="button"
                    disabled={caseBusy}
                    onClick={clearTelemetrySelection}
                    className="text-xs text-slate-400 underline disabled:opacity-50"
                  >
                    Clear selection
                  </button>
                </>
              )}
              <button
                type="button"
                disabled={
                  !apiKey ||
                  !telemetrySourceId ||
                  !telemetryFileContent ||
                  caseBusy
                }
                onClick={() => void importTelemetryFile()}
                className="rounded border border-teal-800 px-3 py-2 text-teal-200 disabled:opacity-50"
              >
                Import selected file
              </button>
            </div>
            {telemetryMessage && (
              <p className="mt-3 text-xs text-teal-200" role="status">{telemetryMessage}</p>
            )}
            {telemetryEvents.length > 0 && (
              <div className="mt-3 max-h-48 overflow-auto rounded border border-slate-800 bg-slate-950 p-3">
                <p className="mb-2 text-xs font-semibold text-slate-300">
                  Recent normalized events ({telemetryEvents.length})
                </p>
                <ul className="space-y-1 text-xs text-slate-400">
                  {telemetryEvents.map((event) => (
                    <li key={event.event_id}>
                      {event.observed_at} · {event.source_id} · {event.event_type}
                      {event.reported_severity ? ` · reported ${event.reported_severity}` : ""}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          <div className="rounded border border-slate-800 bg-slate-950 p-4">
            <h3 className="font-semibold text-slate-200">Correlate a supplied event batch</h3>
            <p className="mt-1 text-slate-500">Events are sent to the authenticated API for exact-key grouping only; they are not persisted until you create a case.</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              <input aria-label="Event ID" placeholder="Event ID *" value={eventDraft.event_id} onChange={(event) => setEventDraft((previous) => ({ ...previous, event_id: event.target.value }))} className="rounded border border-slate-700 bg-slate-900 px-3 py-2" />
              <input aria-label="Event type" placeholder="Event type *" value={eventDraft.event_type} onChange={(event) => setEventDraft((previous) => ({ ...previous, event_type: event.target.value }))} className="rounded border border-slate-700 bg-slate-900 px-3 py-2" />
              <input aria-label="Correlation key" placeholder="Correlation key *" value={eventDraft.correlation_key} onChange={(event) => setEventDraft((previous) => ({ ...previous, correlation_key: event.target.value }))} className="rounded border border-slate-700 bg-slate-900 px-3 py-2" />
              <input aria-label="Event source" placeholder="Source (optional)" value={eventDraft.source} onChange={(event) => setEventDraft((previous) => ({ ...previous, source: event.target.value }))} className="rounded border border-slate-700 bg-slate-900 px-3 py-2" />
              <input aria-label="Event time" type="datetime-local" value={eventDraft.observed_at} onChange={(event) => setEventDraft((previous) => ({ ...previous, observed_at: event.target.value }))} className="rounded border border-slate-700 bg-slate-900 px-3 py-2" />
              <select aria-label="Reported severity" value={eventDraft.severity} onChange={(event) => setEventDraft((previous) => ({ ...previous, severity: event.target.value }))} className="rounded border border-slate-700 bg-slate-900 px-3 py-2">
                <option value="">Severity (optional)</option>
                {["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"].map((severity) => <option key={severity}>{severity}</option>)}
              </select>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <button type="button" onClick={addCorrelationEvent} className="rounded border border-slate-700 px-3 py-2 text-slate-200">Add event</button>
              <button type="button" disabled={!apiKey || correlationEvents.length === 0 || caseBusy} onClick={() => void correlateEventBatch()} className="rounded bg-cyan-400 px-3 py-2 font-semibold text-slate-950 disabled:opacity-50">Correlate {correlationEvents.length} event(s)</button>
              <button type="button" disabled={correlationEvents.length === 0 || caseBusy} onClick={() => setCorrelationEvents([])} className="rounded border border-slate-700 px-3 py-2 text-slate-400 disabled:opacity-50">Clear batch</button>
            </div>
            {correlationEvents.length > 0 && (
              <ul className="mt-3 space-y-1 text-slate-400">
                {correlationEvents.map((event, index) => (
                  <li key={`${event.event_id}-${index}`} className="flex justify-between gap-3">
                    <span>{event.event_id} · {event.event_type} · key: {event.correlation_key}</span>
                    <button type="button" onClick={() => setCorrelationEvents((previous) => previous.filter((_, eventIndex) => eventIndex !== index))} className="text-rose-300">Remove</button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          {caseRecords.length === 0 ? (
            <p className="text-xs text-slate-500">No cases loaded. Enter an API key and load cases.</p>
          ) : (
            <div className="space-y-4">
              {caseRecords.map((item) => (
                <article key={item.case_id} className="rounded border border-slate-800 bg-slate-950 p-4 text-xs">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h3 className="font-bold text-cyan-300">{item.title}</h3>
                      <p className="mt-1 text-slate-400">{item.case_id} · {item.priority} · {item.event_count} events</p>
                      <p className="mt-2 max-w-3xl text-slate-300">{item.summary}</p>
                    </div>
                    <button
                      type="button"
                      disabled={caseBusy || (item.notes !== undefined && item.evidence !== undefined)}
                      onClick={() => void loadCaseDetails(item.case_id)}
                      className="mt-3 rounded border border-slate-700 px-3 py-1.5 text-slate-300 disabled:opacity-50"
                    >
                      {item.notes !== undefined && item.evidence !== undefined ? "Activity loaded" : "Load notes and evidence"}
                    </button>
                    <div className="mt-4 rounded border border-cyan-900/60 bg-cyan-950/20 p-3">
                      <h4 className="font-semibold text-cyan-200">On-chain block graph · read only</h4>
                      <p className="mt-1 text-slate-400">
                        Queries only the node configured on the API server. Optional case storage retains normalized blocks and on-chain addresses until the configured retention expires.
                      </p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <select
                          aria-label={`On-chain network for ${item.title}`}
                          value={onchainQueryDrafts[item.case_id]?.chain ?? "bitcoin"}
                          disabled={caseBusy}
                          onChange={(event) =>
                            setOnchainQueryDrafts((previous) => ({
                              ...previous,
                              [item.case_id]: {
                                chain: event.target.value as "bitcoin" | "ethereum",
                                height: previous[item.case_id]?.height ?? "",
                              },
                            }))
                          }
                          className="rounded border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100"
                        >
                          <option value="bitcoin">Bitcoin</option>
                          <option value="ethereum">Ethereum</option>
                        </select>
                        <input
                          aria-label={`Block height for ${item.title}`}
                          inputMode="numeric"
                          pattern="[0-9]*"
                          placeholder="Block height"
                          value={onchainQueryDrafts[item.case_id]?.height ?? ""}
                          disabled={caseBusy}
                          onChange={(event) =>
                            setOnchainQueryDrafts((previous) => ({
                              ...previous,
                              [item.case_id]: {
                                chain: previous[item.case_id]?.chain ?? "bitcoin",
                                height: event.target.value,
                              },
                            }))
                          }
                          className="min-w-40 rounded border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100"
                        />
                        <button
                          type="button"
                          disabled={!apiKey || caseBusy}
                          onClick={() =>
                            void loadOnChainGraph(item.case_id, {
                              chain: onchainQueryDrafts[item.case_id]?.chain ?? "bitcoin",
                              height: onchainQueryDrafts[item.case_id]?.height ?? "",
                            })
                          }
                          className="rounded border border-cyan-800 px-3 py-2 text-cyan-200 disabled:opacity-50"
                        >
                          Load block graph
                        </button>
                        <button
                          type="button"
                          disabled={!apiKey || caseBusy}
                          onClick={() => void loadOnChainSnapshots(item.case_id)}
                          className="rounded border border-slate-700 px-3 py-2 text-slate-200 disabled:opacity-50"
                        >
                          Load saved blocks
                        </button>
                      </div>
                      {(onchainSnapshots[item.case_id]?.length ?? 0) > 0 && (
                        <div className="mt-3 flex flex-wrap gap-2">
                          <select
                            aria-label={`Saved on-chain block for ${item.title}`}
                            value={onchainSnapshotSelections[item.case_id] ?? ""}
                            disabled={caseBusy}
                            onChange={(event) =>
                              setOnchainSnapshotSelections((previous) => ({
                                ...previous,
                                [item.case_id]: event.target.value,
                              }))
                            }
                            className="min-w-64 rounded border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100"
                          >
                            <option value="">Select a saved block</option>
                            {onchainSnapshots[item.case_id].map((snapshot) => (
                              <option key={snapshot.snapshot_id} value={snapshot.snapshot_id}>
                                {snapshot.chain} #{snapshot.height} · {snapshot.block_hash.slice(0, 16)} · {snapshot.stored_at}
                              </option>
                            ))}
                          </select>
                          <button
                            type="button"
                            disabled={
                              !apiKey ||
                              caseBusy ||
                              !onchainSnapshots[item.case_id].some(
                                (snapshot) => snapshot.snapshot_id === onchainSnapshotSelections[item.case_id],
                              )
                            }
                            onClick={() => {
                              const snapshot = onchainSnapshots[item.case_id]?.find(
                                (candidate) =>
                                  candidate.snapshot_id === onchainSnapshotSelections[item.case_id],
                              );
                              if (snapshot) {
                                void loadOnChainGraph(
                                  item.case_id,
                                  { chain: snapshot.chain, height: String(snapshot.height) },
                                  snapshot.block_hash,
                                );
                              }
                            }}
                            className="rounded border border-cyan-800 px-3 py-2 text-cyan-200 disabled:opacity-50"
                          >
                            Load saved graph
                          </button>
                        </div>
                      )}
                      {(onchainQueryDrafts[item.case_id]?.chain ?? "bitcoin") === "ethereum" && (
                        <>
                          <div className="mt-3 flex flex-wrap items-end gap-2 rounded border border-violet-900/50 bg-violet-950/10 p-3">
                            <button
                              type="button"
                              disabled={!apiKey || caseBusy || !/^\d+$/.test(onchainQueryDrafts[item.case_id]?.height ?? "")}
                              onClick={() =>
                                void loadOnChainForensics(
                                  item.case_id,
                                  onchainQueryDrafts[item.case_id]?.height ?? "",
                                )
                              }
                              className="rounded border border-violet-800 px-3 py-2 text-violet-200 disabled:opacity-50"
                            >
                              Load block logs &amp; token events
                            </button>
                            <label className="min-w-72 flex-1 text-slate-400">
                              Ethereum transaction hash for call trace
                              <input
                                aria-label={`Ethereum transaction hash for ${item.title}`}
                                placeholder="0x + 64 hex characters"
                                value={onchainTraceDrafts[item.case_id] ?? ""}
                                disabled={caseBusy}
                                onChange={(event) =>
                                  setOnchainTraceDrafts((previous) => ({
                                    ...previous,
                                    [item.case_id]: event.target.value,
                                  }))
                                }
                                className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100"
                              />
                            </label>
                            <button
                              type="button"
                              disabled={
                                !apiKey ||
                                caseBusy ||
                                !/^0x[0-9a-fA-F]{64}$/.test(onchainTraceDrafts[item.case_id] ?? "")
                              }
                              onClick={() => void loadOnChainTrace(item.case_id)}
                              className="rounded border border-violet-800 px-3 py-2 text-violet-200 disabled:opacity-50"
                            >
                              Load bounded call trace
                            </button>
                          </div>
                          {onchainForensics[item.case_id] && (
                            <div className="mt-3 rounded border border-violet-900/50 bg-slate-950 p-3">
                              <h5 className="font-semibold text-violet-200">
                                Ethereum block {onchainForensics[item.case_id].block.height} ·{" "}
                                {onchainForensics[item.case_id].logs.length} logs ·{" "}
                                {onchainForensics[item.case_id].transfer_observations.length} transfer-shaped events
                              </h5>
                              <p className="mt-1 text-amber-200">
                                Provider observations only. AML / MiCA status: NOT ASSESSED.
                              </p>
                              {onchainForensics[item.case_id].transfer_observations.length > 0 && (
                                <ul className="mt-2 space-y-1 text-slate-300">
                                  {onchainForensics[item.case_id].transfer_observations.slice(0, 20).map((transfer) => (
                                    <li key={`${transfer.transaction_hash}-${transfer.log_index}`}>
                                      <span className="text-violet-200">{transfer.token_contract}</span>
                                      {" · "}{transfer.from_address} → {transfer.to_address}
                                      {transfer.value_atomic !== null
                                        ? ` · base units ${transfer.value_atomic}`
                                        : ` · token ID ${transfer.token_id ?? "unknown"}`}
                                      {" · "}{transfer.confidence}
                                    </li>
                                  ))}
                                </ul>
                              )}
                              {onchainForensics[item.case_id].provider_assessments.length > 0 && (
                                <p className="mt-2 text-amber-300">
                                  Matching imported OSINT labels:{" "}
                                  {onchainForensics[item.case_id].provider_assessments
                                    .slice(0, 10)
                                    .map((assessment) => `${assessment.provider} ${assessment.provider_rating} (unverified)`)
                                    .join(" · ")}
                                </p>
                              )}
                            </div>
                          )}
                          {onchainTraces[item.case_id] && (
                            <div className="mt-3 rounded border border-violet-900/50 bg-slate-950 p-3">
                              <h5 className="font-semibold text-violet-200">
                                Bounded trace · block {onchainTraces[item.case_id].block_height} ·{" "}
                                {onchainTraces[item.case_id].trace.call_type}
                              </h5>
                              <p className="mt-1 break-all text-slate-300">
                                {onchainTraces[item.case_id].trace.from_address}
                                {" → "}{onchainTraces[item.case_id].trace.to_address ?? "contract creation"}
                                {" · value (wei): "}{onchainTraces[item.case_id].trace.value_atomic}
                                {" · selector: "}{onchainTraces[item.case_id].trace.input_selector ?? "none"}
                                {" · nested calls: "}{onchainTraces[item.case_id].trace.calls.length}
                              </p>
                              <p className="mt-1 text-amber-200">
                                Provider trace only. AML / MiCA status: NOT ASSESSED.
                              </p>
                            </div>
                          )}
                        </>
                      )}
                      <div className="mt-3 grid gap-2 md:grid-cols-[1fr_auto]">
                        <label className="text-slate-400">
                          Import normalized provider report (JSON, up to 1 MB)
                          <input
                            aria-label={`Provider risk report for ${item.title}`}
                            type="file"
                            accept=".json,application/json"
                            disabled={caseBusy}
                            onChange={(event) =>
                              void selectOnChainRiskReport(
                                item.case_id,
                                event.currentTarget.files?.[0],
                              )
                            }
                            className="mt-1 block w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 text-slate-300"
                          />
                        </label>
                        <button
                          type="button"
                          disabled={!apiKey || !onchainRiskReportDrafts[item.case_id] || caseBusy}
                          onClick={() => void importOnChainRiskReport(item.case_id)}
                          className="self-end rounded border border-amber-800 px-3 py-2 text-amber-200 disabled:opacity-50"
                        >
                          Import provider report
                        </button>
                      </div>
                      <p className="mt-2 text-[10px] text-amber-200">
                        Import stores normalized ratings and a digest, not the raw report. Provider signatures and ratings are not verified; view the report format and limitations in the docs.
                      </p>
                      {onchainGraphs[item.case_id] && (
                        <div className="mt-4">
                          <p className="mb-2 text-xs text-slate-400">
                            {onchainGraphs[item.case_id].storage.enabled
                              ? onchainGraphs[item.case_id].storage.loaded_from_snapshot
                                ? "Loaded from retained case snapshot."
                                : onchainGraphs[item.case_id].storage.inserted
                                  ? `Snapshot retained${onchainGraphs[item.case_id].storage.reorg_fork_preserved ? " · another block hash exists at this height" : ""}.`
                                  : "Snapshot already retained."
                              : "Snapshot storage is disabled; this graph is an ephemeral RPC observation."}
                          </p>
                          <AttackGraphVisualizer data={onchainGraphs[item.case_id]} />
                        </div>
                      )}
                    </div>
                    <div className="mt-4 rounded border border-amber-900/60 bg-amber-950/10 p-3">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <h4 className="font-semibold text-amber-200">
                            EU CASP · AML / MiCA review checklist
                          </h4>
                          <p className="mt-1 text-slate-400">
                            Case-scoped review metadata and evidence references only; this is not legal advice or a compliance determination.
                          </p>
                        </div>
                        <button
                          type="button"
                          disabled={!apiKey || caseBusy}
                          onClick={() => void loadRegulatoryChecklist(item.case_id)}
                          className="rounded border border-amber-800 px-3 py-2 text-amber-200 disabled:opacity-50"
                        >
                          {regulatoryChecklists[item.case_id] ? "Reload checklist" : "Load checklist"}
                        </button>
                      </div>
                      {regulatoryChecklists[item.case_id] && (
                        <div className="mt-3 space-y-3">
                          <p className="rounded border border-amber-900/50 bg-slate-950 p-2 text-amber-200">
                            Overall status: NOT ASSESSED · profile version {regulatoryChecklists[item.case_id].profile_version}
                          </p>
                          {regulatoryChecklists[item.case_id].controls.map((control) => {
                            const draftKey = `${item.case_id}:${control.control_id}`;
                            const draft = regulatoryDrafts[draftKey];
                            return (
                              <article
                                key={control.control_id}
                                className="rounded border border-slate-800 bg-slate-950 p-3"
                              >
                                <div className="flex flex-wrap items-start justify-between gap-2">
                                  <div>
                                    <h5 className="font-semibold text-slate-200">
                                      {control.framework} · {control.title}
                                    </h5>
                                    <p className="mt-1 text-slate-400">{control.review_prompt}</p>
                                    <a
                                      href={control.source_url}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="mt-1 inline-block text-cyan-300 underline"
                                    >
                                      {control.official_reference} · official source
                                    </a>
                                  </div>
                                  <span className="text-amber-200">
                                    {control.applicability.replaceAll("_", " ")} · {control.review_state.replaceAll("_", " ")}
                                  </span>
                                </div>
                                <div className="mt-3 grid gap-2 md:grid-cols-2">
                                  <label className="text-slate-400">
                                    Applicability
                                    <select
                                      aria-label={`Applicability for ${control.control_id}`}
                                      value={draft?.applicability ?? control.applicability}
                                      disabled={caseBusy}
                                      onChange={(event) =>
                                        setRegulatoryDrafts((previous) => ({
                                          ...previous,
                                          [draftKey]: {
                                            applicability: event.target.value as RegulatoryChecklistControl["applicability"],
                                            review_state: previous[draftKey]?.review_state ?? control.review_state,
                                            summary: previous[draftKey]?.summary ?? control.summary,
                                            evidence_source: previous[draftKey]?.evidence_source ?? "",
                                            evidence_reference: previous[draftKey]?.evidence_reference ?? "",
                                            evidence_sha256: previous[draftKey]?.evidence_sha256 ?? "",
                                          },
                                        }))
                                      }
                                      className="mt-1 block w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100"
                                    >
                                      <option value="not_assessed">Not assessed</option>
                                      <option value="in_scope">In scope</option>
                                      <option value="out_of_scope">Out of scope · rationale required</option>
                                      <option value="needs_legal_review">Needs legal review</option>
                                    </select>
                                  </label>
                                  <label className="text-slate-400">
                                    Review state
                                    <select
                                      aria-label={`Review state for ${control.control_id}`}
                                      value={draft?.review_state ?? control.review_state}
                                      disabled={caseBusy}
                                      onChange={(event) =>
                                        setRegulatoryDrafts((previous) => ({
                                          ...previous,
                                          [draftKey]: {
                                            applicability: previous[draftKey]?.applicability ?? control.applicability,
                                            review_state: event.target.value as RegulatoryChecklistControl["review_state"],
                                            summary: previous[draftKey]?.summary ?? control.summary,
                                            evidence_source: previous[draftKey]?.evidence_source ?? "",
                                            evidence_reference: previous[draftKey]?.evidence_reference ?? "",
                                            evidence_sha256: previous[draftKey]?.evidence_sha256 ?? "",
                                          },
                                        }))
                                      }
                                      className="mt-1 block w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100"
                                    >
                                      <option value="not_assessed">Not assessed</option>
                                      <option value="evidence_recorded" disabled={control.evidence.length === 0}>
                                        Evidence recorded
                                      </option>
                                      <option value="needs_review">Needs review</option>
                                    </select>
                                  </label>
                                </div>
                                <label className="mt-2 block text-slate-400">
                                  Analyst summary / out-of-scope rationale
                                  <textarea
                                    value={draft?.summary ?? control.summary}
                                    disabled={caseBusy}
                                    onChange={(event) =>
                                      setRegulatoryDrafts((previous) => ({
                                        ...previous,
                                        [draftKey]: {
                                          applicability: previous[draftKey]?.applicability ?? control.applicability,
                                          review_state: previous[draftKey]?.review_state ?? control.review_state,
                                          summary: event.target.value,
                                          evidence_source: previous[draftKey]?.evidence_source ?? "",
                                          evidence_reference: previous[draftKey]?.evidence_reference ?? "",
                                          evidence_sha256: previous[draftKey]?.evidence_sha256 ?? "",
                                        },
                                      }))
                                    }
                                    rows={2}
                                    maxLength={4000}
                                    className="mt-1 w-full rounded border border-slate-700 bg-slate-900 p-2 text-slate-100"
                                  />
                                </label>
                                <div className="mt-2 flex flex-wrap gap-2">
                                  <button
                                    type="button"
                                    disabled={!apiKey || !createdBy.trim() || caseBusy}
                                    onClick={() => void updateRegulatoryControl(item.case_id, control)}
                                    className="rounded border border-amber-800 px-3 py-1.5 text-amber-200 disabled:opacity-50"
                                  >
                                    Save review metadata
                                  </button>
                                </div>
                                <div className="mt-3 grid gap-2 md:grid-cols-2">
                                  {([
                                    ["evidence_source", "Evidence source"],
                                    ["evidence_reference", "Evidence reference"],
                                    ["evidence_sha256", "Evidence SHA-256"],
                                  ] as const).map(([field, label]) => (
                                    <label key={field} className="text-slate-400">
                                      {label}
                                      <input
                                        aria-label={`${label} for ${control.control_id}`}
                                        value={draft?.[field] ?? ""}
                                        disabled={caseBusy}
                                        onChange={(event) =>
                                          setRegulatoryDrafts((previous) => ({
                                            ...previous,
                                            [draftKey]: {
                                              applicability: previous[draftKey]?.applicability ?? control.applicability,
                                              review_state: previous[draftKey]?.review_state ?? control.review_state,
                                              summary: previous[draftKey]?.summary ?? control.summary,
                                              evidence_source: previous[draftKey]?.evidence_source ?? "",
                                              evidence_reference: previous[draftKey]?.evidence_reference ?? "",
                                              evidence_sha256: previous[draftKey]?.evidence_sha256 ?? "",
                                              [field]: event.target.value,
                                            },
                                          }))
                                        }
                                        className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100"
                                      />
                                    </label>
                                  ))}
                                  <button
                                    type="button"
                                    disabled={!apiKey || !createdBy.trim() || caseBusy}
                                    onClick={() => void addRegulatoryEvidence(item.case_id, control)}
                                    className="self-end rounded border border-cyan-800 px-3 py-2 text-cyan-200 disabled:opacity-50"
                                  >
                                    Add evidence reference
                                  </button>
                                </div>
                                {control.evidence.length > 0 && (
                                  <ul className="mt-3 space-y-1 border-t border-slate-800 pt-2 text-slate-400">
                                    {control.evidence.slice(-5).map((entry) => (
                                      <li key={entry.evidence_id} className="break-all">
                                        {entry.source} · {entry.reference} · SHA-256 {entry.sha256} · {entry.recorded_by}
                                      </li>
                                    ))}
                                  </ul>
                                )}
                              </article>
                            );
                          })}
                        </div>
                      )}
                    </div>
                    <div className="mt-4 rounded border border-amber-900/60 bg-amber-950/20 p-3">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <h4 className="font-semibold text-amber-200">Response playbooks · recommendation only</h4>
                          <p className="mt-1 text-slate-400">Simulation and approval never run commands, contact services, or change systems.</p>
                        </div>
                        <div className="flex gap-2">
                          <button type="button" disabled={!apiKey || caseBusy} onClick={() => void simulateCasePlaybook(item.case_id)} className="rounded border border-amber-800 px-3 py-2 text-amber-200 disabled:opacity-50">Simulate</button>
                          <button type="button" disabled={!apiKey || caseBusy} onClick={() => void loadCasePlaybooks(item.case_id)} className="rounded border border-slate-700 px-3 py-2 text-slate-300 disabled:opacity-50">Load playbooks</button>
                        </div>
                      </div>
                      {(playbooksByCase[item.case_id] ?? []).map((plan) => (
                        <div key={plan.plan_id} className="mt-3 rounded border border-slate-800 bg-slate-950 p-3">
                          <div className="flex flex-wrap justify-between gap-2">
                            <span className="font-semibold text-slate-200">Plan {plan.plan_id}</span>
                            <span className="text-amber-200">{plan.status.replaceAll("_", " ")} · {plan.execution_status}</span>
                          </div>
                          <p className="mt-1 text-slate-500">Simulated by {plan.simulated_by} · {plan.steps.length} review steps</p>
                          <ol className="mt-3 list-decimal space-y-2 pl-5 text-slate-300">
                            {plan.steps.map((step) => (
                              <li key={step.step_id}>
                                <span className="font-semibold">{step.title}</span>
                                <p className="mt-0.5 text-slate-400">{step.description}</p>
                                <p className="mt-0.5 text-slate-500">Basis: {step.basis}</p>
                              </li>
                            ))}
                          </ol>
                          <label className="mt-3 block text-slate-400">
                            Decision rationale (required)
                            <textarea
                              value={decisionDrafts[plan.plan_id] ?? ""}
                              onChange={(event) => setDecisionDrafts((previous) => ({ ...previous, [plan.plan_id]: event.target.value }))}
                              className="mt-1 w-full rounded border border-slate-700 bg-slate-900 p-2 text-slate-100"
                              rows={2}
                            />
                          </label>
                          <div className="mt-2 flex flex-wrap gap-2">
                            <button type="button" disabled={!apiKey || caseBusy} onClick={() => void decideCasePlaybook(plan, "approve")} className="rounded border border-emerald-800 px-3 py-1.5 text-emerald-200 disabled:opacity-50">Approve for manual review</button>
                            <button type="button" disabled={!apiKey || caseBusy} onClick={() => void decideCasePlaybook(plan, "reject")} className="rounded border border-rose-900 px-3 py-1.5 text-rose-200 disabled:opacity-50">Reject</button>
                          </div>
                          {plan.decisions.length > 0 && (
                            <ul className="mt-3 space-y-2 border-t border-slate-800 pt-3 text-slate-400">
                              {plan.decisions.map((entry) => (
                                <li key={entry.decision_id}>
                                  <span className="text-slate-200">{entry.reviewer} {entry.decision === "approve" ? "approved" : "rejected"}:</span> {entry.rationale}
                                  <span className="ml-2 text-slate-600">{entry.created_at}</span>
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      ))}
                    </div>
                    <label className="text-slate-400">
                      Status
                      <select
                        value={item.status}
                        disabled={caseBusy}
                        onChange={(event) => void updateCase(item.case_id, { status: event.target.value as IncidentCaseRecord["status"] })}
                        className="ml-2 rounded border border-slate-700 bg-slate-900 px-2 py-1 text-slate-100"
                      >
                        {["open", "in_progress", "resolved", "closed"].map((value) => <option key={value}>{value}</option>)}
                      </select>
                    </label>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <input
                      aria-label={`Assignee for ${item.title}`}
                      value={assigneeDrafts[item.case_id] ?? ""}
                      onChange={(event) => setAssigneeDrafts((previous) => ({ ...previous, [item.case_id]: event.target.value }))}
                      placeholder="Assign to analyst"
                      className="min-w-48 rounded border border-slate-700 bg-slate-900 px-3 py-2"
                    />
                    <button
                      type="button"
                      disabled={caseBusy}
                      onClick={() => void updateCase(item.case_id, { assigned_to: assigneeDrafts[item.case_id]?.trim() || null })}
                      className="rounded border border-slate-700 px-3 py-2 text-cyan-200 disabled:opacity-50"
                    >
                      Save assignment
                    </button>
                  </div>
                  <div className="mt-4 rounded border border-violet-900/60 bg-violet-950/20 p-3">
                    <h4 className="font-semibold text-violet-200">Purple Team detection replay · offline</h4>
                    <p className="mt-1 text-slate-400">
                      Checks recorded, source-provided detection IDs in this case only. It does not execute a scenario or contact an EDR/XDR service.
                    </p>
                    <div className="mt-3 grid gap-2 sm:grid-cols-2">
                      <input
                        aria-label={`Purple Team scenario ID for ${item.title}`}
                        value={purpleScenarioId}
                        onChange={(event) => setPurpleScenarioId(event.target.value)}
                        placeholder="Scenario ID"
                        className="rounded border border-slate-700 bg-slate-900 px-3 py-2"
                      />
                      <input
                        aria-label={`Expected detection rule ID for ${item.title}`}
                        value={purpleExpectedRuleId}
                        onChange={(event) => setPurpleExpectedRuleId(event.target.value)}
                        placeholder="Expected detection rule ID"
                        className="rounded border border-slate-700 bg-slate-900 px-3 py-2"
                      />
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <button
                        type="button"
                        disabled={!apiKey || caseBusy}
                        onClick={() => void runPurpleTeamReplay(item.case_id)}
                        className="rounded border border-violet-800 px-3 py-2 text-violet-200 disabled:opacity-50"
                      >
                        Record detection replay
                      </button>
                      <button
                        type="button"
                        disabled={!apiKey || caseBusy}
                        onClick={() => void downloadCaseReport(item.case_id)}
                        className="rounded border border-slate-700 px-3 py-2 text-slate-200 disabled:opacity-50"
                      >
                        Export case report (JSON)
                      </button>
                    </div>
                    {(item.purple_team_replays ?? []).length > 0 && (
                      <ul className="mt-3 space-y-2 border-t border-slate-800 pt-3 text-slate-400">
                        {item.purple_team_replays?.map((replay) => (
                          <li key={replay.replay_id}>
                            <span className={replay.result.detection_verified ? "text-emerald-300" : "text-amber-300"}>
                              {replay.result.status}
                            </span>
                            {" · "}{replay.scenario_id} / {replay.expected_rule_id}
                            {replay.result.matched_alert?.event_id
                              ? ` · matched event ${replay.result.matched_alert.event_id}`
                              : ""}
                            {" · "}{replay.created_at}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    <div>
                      <label className="block text-slate-400">
                        Add note
                        <textarea
                          value={noteDrafts[item.case_id] ?? ""}
                          onChange={(event) => setNoteDrafts((previous) => ({ ...previous, [item.case_id]: event.target.value }))}
                          className="mt-1 w-full rounded border border-slate-700 bg-slate-900 p-2 text-slate-100"
                          rows={2}
                        />
                      </label>
                      <button type="button" disabled={caseBusy} onClick={() => void addCaseNote(item.case_id)} className="mt-1 rounded border border-slate-700 px-3 py-1.5 text-cyan-200 disabled:opacity-50">Add note</button>
                    </div>
                    <div>
                      <label className="block text-slate-400">
                        Evidence reference (no file upload)
                        <input
                          value={evidenceDrafts[item.case_id] ?? ""}
                          onChange={(event) => setEvidenceDrafts((previous) => ({ ...previous, [item.case_id]: event.target.value }))}
                          className="mt-1 w-full rounded border border-slate-700 bg-slate-900 p-2 text-slate-100"
                        />
                      </label>
                      <button type="button" disabled={caseBusy} onClick={() => void addCaseEvidence(item.case_id)} className="mt-1 rounded border border-slate-700 px-3 py-1.5 text-cyan-200 disabled:opacity-50">Add reference</button>
                    </div>
                  </div>
                  {(item.notes ?? []).length > 0 && (
                    <ul className="mt-4 space-y-1 border-t border-slate-800 pt-3 text-slate-400">
                      {item.notes?.map((note) => <li key={note.note_id}><span className="text-slate-300">{note.author}:</span> {note.body}</li>)}
                    </ul>
                  )}
                  {(item.evidence ?? []).length > 0 && (
                    <ul className="mt-3 space-y-1 text-slate-400">
                      {item.evidence?.map((evidence) => <li key={evidence.evidence_id}>Evidence · {evidence.source}: {evidence.reference}{evidence.sha256 ? ` · SHA-256 ${evidence.sha256}` : ""}</li>)}
                    </ul>
                  )}
                </article>
              ))}
            </div>
          )}
          <p className="mt-4 text-xs text-slate-500">Case notes and evidence references are append-only. Evidence content is not uploaded or stored here. The API key is not saved by the dashboard.</p>
          <div className="mt-5 border-t border-slate-800 pt-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="font-semibold text-slate-200">Access audit</h3>
                <p className="mt-1 text-xs text-slate-500">Shows authenticated case and playbook API access without request bodies or client IP addresses.</p>
              </div>
              <button type="button" disabled={!apiKey || caseBusy} onClick={() => void loadAccessAudit()} className="rounded border border-slate-700 px-3 py-2 text-slate-300 disabled:opacity-50">Load access audit</button>
            </div>
            {auditLimitations && <p className="mt-2 text-xs text-amber-300">{auditLimitations}</p>}
            {accessAuditRecords.length > 0 && (
              <ol className="mt-3 max-h-64 space-y-2 overflow-y-auto text-xs text-slate-400">
                {accessAuditRecords.map((record) => (
                  <li key={record.audit_id} className="flex flex-wrap justify-between gap-2 border-b border-slate-800 pb-2">
                    <span>{record.action} · HTTP {record.outcome_code} · {record.record_type}</span>
                    <span>{record.credential_fingerprint ?? "policy"} · {record.occurred_at}</span>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </section>
        <section className="mt-4 rounded-lg border border-slate-800 bg-slate-900 p-6 md:col-span-3">
          <h2 className="mb-4 text-sm font-semibold text-slate-300">Live incident stream</h2>
          <div className="max-h-72 space-y-2 overflow-y-auto">
            {incidents.length === 0 ? (
              <p className="text-xs text-slate-500">No incident events received. Check the API WebSocket endpoint and connection status.</p>
            ) : incidents.map((item, index) => "timeline" in item ? (
              <article key={`${item.correlation_id}-${index}`} className="rounded border border-slate-800 bg-slate-950 p-4 text-xs">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h3 className={`font-bold ${item.synthetic ? "text-violet-300" : "text-cyan-300"}`}>
                    {item.synthetic ? `SYNTHETIC DEMO · ${item.scenario_title ?? "Scenario"}` : "Correlated incident"} · {item.correlation_id}
                  </h3>
                  <span className="font-semibold text-amber-300">Reported priority: {item.priority}</span>
                </div>
                <button
                  type="button"
                  disabled={!apiKey || caseBusy}
                  onClick={() => void createCase(item)}
                  className="mt-3 rounded border border-cyan-700 px-3 py-1.5 text-cyan-200 disabled:opacity-50"
                >
                  Create case
                </button>
                <ul className="mt-3 space-y-1 text-slate-400">
                  {item.priority_reasons.map((reason) => <li key={reason}>• {reason}</li>)}
                </ul>
                <ol className="mt-4 space-y-2 border-l border-slate-700 pl-4">
                  {item.timeline.map((entry) => (
                    <li key={entry.event_id} className="relative">
                      <span className="font-semibold text-slate-200">{entry.event_type}</span>
                      <span className="ml-2 text-slate-500">{entry.observed_at ?? "Time not provided"}</span>
                      <div className="mt-1 text-slate-400">
                        {entry.source ?? "Source not provided"} · {entry.reported_severity ?? "Severity not reported"}
                      </div>
                    </li>
                  ))}
                </ol>
              </article>
            ) : (
              <div key={`${item.source}-${item.event}-${index}`} className="flex flex-wrap items-center justify-between gap-3 rounded border border-slate-800 bg-slate-950 p-3 text-xs">
                <span className="font-bold text-rose-300">[{item.severity ?? "UNKNOWN"}] {item.event}</span>
                <span className="text-slate-400">{item.details ?? ""}</span>
                <span className="text-cyan-400">{item.source}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
