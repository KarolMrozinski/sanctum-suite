package sanctum.api.authz

import rego.v1

policy_version := "1.0.0"
unscoped_routes := {"/api/v1/audit", "/api/v1/analytics"}

default allow := false
has_supported_role if {
	some role in input.identity.roles
	role in {"ADMIN", "AUDITOR", "VIEWER"}
}

allow if {
	input.identity.authentication_method == "api_key"
}

allow if {
	input.identity.authentication_method == "event_source"
	input.request.method == "POST"
	input.request.route == "/api/v1/telemetry/ingest"
}

allow if {
	input.identity.authentication_method == "oidc"
	not input.request.route in unscoped_routes
	input.request.method in {"GET", "HEAD", "OPTIONS"}
	has_supported_role
}

allow if {
	input.identity.authentication_method == "oidc"
	not input.request.route in unscoped_routes
	"ADMIN" in input.identity.roles
}

allow if {
	input.identity.authentication_method == "oidc"
	not input.request.route in unscoped_routes
	"AUDITOR" in input.identity.roles
	input.request.method in {"POST", "PUT", "PATCH", "DELETE"}
	startswith(input.request.route, "/api/v1/controls/")
}

allow if {
	input.identity.authentication_method == "oidc"
	not input.request.route in unscoped_routes
	"AUDITOR" in input.identity.roles
	input.request.method in {"POST", "PUT", "PATCH", "DELETE"}
	startswith(input.request.route, "/api/v1/cases")
}

allow if {
	input.identity.authentication_method == "oidc"
	not input.request.route in unscoped_routes
	"AUDITOR" in input.identity.roles
	input.request.method in {"POST", "PUT", "PATCH", "DELETE"}
	startswith(input.request.route, "/api/v1/playbooks")
}

allow if {
	input.identity.authentication_method == "oidc"
	not input.request.route in unscoped_routes
	"AUDITOR" in input.identity.roles
	input.request.method in {"POST", "PUT", "PATCH", "DELETE"}
	input.request.route == "/api/v1/governance/retention/purge"
}

decision := {
	"allow": allow,
	"policy_version": policy_version,
}
