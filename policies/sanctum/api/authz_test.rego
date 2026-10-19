package sanctum.api.authz

import rego.v1

test_api_key_retains_legacy_access if {
	allow with input as {
		"identity": {
			"authentication_method": "api_key",
			"tenant_id": "legacy",
			"roles": ["ADMIN"],
		},
		"request": {
			"method": "GET",
			"route": "/api/v1/analytics",
		},
	}
}

test_event_source_can_only_ingest if {
	allow with input as {
		"identity": {
			"authentication_method": "event_source",
			"tenant_id": "tenant-a",
			"roles": ["ADMIN"],
		},
		"request": {
			"method": "POST",
			"route": "/api/v1/telemetry/ingest",
		},
	}
	not allow with input as {
		"identity": {
			"authentication_method": "event_source",
			"tenant_id": "tenant-a",
			"roles": ["ADMIN"],
		},
		"request": {
			"method": "POST",
			"route": "/api/v1/cases",
		},
	}
}

test_viewer_can_read_tenant_api if {
	allow with input as {
		"identity": {
			"authentication_method": "oidc",
			"tenant_id": "tenant-a",
			"roles": ["VIEWER"],
		},
		"request": {
			"method": "GET",
			"route": "/api/v1/cases",
		},
	}
}

test_viewer_cannot_write if {
	not allow with input as {
		"identity": {
			"authentication_method": "oidc",
			"tenant_id": "tenant-a",
			"roles": ["VIEWER"],
		},
		"request": {
			"method": "POST",
			"route": "/api/v1/cases",
		},
	}
}

test_auditor_can_write_cases if {
	allow with input as {
		"identity": {
			"authentication_method": "oidc",
			"tenant_id": "tenant-a",
			"roles": ["AUDITOR"],
		},
		"request": {
			"method": "POST",
			"route": "/api/v1/cases",
		},
	}
}

test_auditor_cannot_write_telemetry if {
	not allow with input as {
		"identity": {
			"authentication_method": "oidc",
			"tenant_id": "tenant-a",
			"roles": ["AUDITOR"],
		},
		"request": {
			"method": "POST",
			"route": "/api/v1/telemetry/ingest",
		},
	}
}

test_oidc_cannot_access_unscoped_analytics if {
	not allow with input as {
		"identity": {
			"authentication_method": "oidc",
			"tenant_id": "tenant-a",
			"roles": ["ADMIN"],
		},
		"request": {
			"method": "GET",
			"route": "/api/v1/analytics",
		},
	}
}

test_readiness_probe_is_denied if {
	not decision.allow with input as {
		"identity": {
			"authentication_method": "readiness_probe",
			"tenant_id": "readiness",
			"roles": [],
		},
		"request": {
			"method": "GET",
			"route": "/__sanctum_opa_readiness__",
		},
	}
}
