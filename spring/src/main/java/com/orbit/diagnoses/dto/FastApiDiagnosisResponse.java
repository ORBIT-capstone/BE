package com.orbit.diagnoses.dto;

import java.util.Set;
import tools.jackson.databind.JsonNode;

/** FastAPI 진단 응답에서 저장에 필요한 필드와 최소 응답 계약을 검증한다. */
public record FastApiDiagnosisResponse(
	JsonNode raw,
	String status,
	Integer depletionAge
) {

	private static final Set<String> ALLOWED_STATUSES = Set.of("SUFFICIENT", "MIDDLE", "INSUFFICIENT");

	public static FastApiDiagnosisResponse from(JsonNode raw) {
		if (raw == null || !raw.isObject()) {
			throw new IllegalArgumentException("진단 응답은 JSON 객체여야 합니다.");
		}

		requireInteger(raw, "current_age");
		requireFiniteNumber(raw, "monthly_gap");
		requireInteger(raw, "target_age");
		requireArray(raw, "timeline");

		JsonNode statusNode = raw.get("status");
		if (statusNode == null || !statusNode.isString() || !ALLOWED_STATUSES.contains(statusNode.asString())) {
			throw new IllegalArgumentException("진단 응답의 status가 올바르지 않습니다.");
		}

		JsonNode depletionAgeNode = raw.get("depletion_age");
		Integer depletionAge = null;
		if (depletionAgeNode == null) {
			throw new IllegalArgumentException("진단 응답에 depletion_age가 없습니다.");
		}
		if (!depletionAgeNode.isNull()) {
			if (!depletionAgeNode.isIntegralNumber()) {
				throw new IllegalArgumentException("진단 응답의 depletion_age가 올바르지 않습니다.");
			}
			depletionAge = depletionAgeNode.asInt();
		}

		JsonNode depletedNode = raw.get("depleted");
		if (depletedNode == null || !depletedNode.isBoolean()
			|| depletedNode.asBoolean() != (depletionAge != null)) {
			throw new IllegalArgumentException("진단 응답의 depleted와 depletion_age가 일치하지 않습니다.");
		}

		return new FastApiDiagnosisResponse(raw, statusNode.asString(), depletionAge);
	}

	private static void requireInteger(JsonNode raw, String field) {
		JsonNode node = raw.get(field);
		if (node == null || !node.isIntegralNumber()) {
			throw new IllegalArgumentException("진단 응답의 " + field + "가 올바르지 않습니다.");
		}
	}

	private static void requireFiniteNumber(JsonNode raw, String field) {
		JsonNode node = raw.get(field);
		if (node == null || !node.isNumber() || !Double.isFinite(node.asDouble())) {
			throw new IllegalArgumentException("진단 응답의 " + field + "가 올바르지 않습니다.");
		}
	}

	private static void requireArray(JsonNode raw, String field) {
		JsonNode node = raw.get(field);
		if (node == null || !node.isArray()) {
			throw new IllegalArgumentException("진단 응답의 " + field + "가 올바르지 않습니다.");
		}
	}
}
