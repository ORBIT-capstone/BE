package com.orbit.diagnoses.dto;

import java.util.Set;
import java.util.HashSet;
import com.orbit.diagnoses.domain.DiagnosisType;
import tools.jackson.databind.JsonNode;

/** 프론트가 전달한 FastAPI 계산 응답의 형식을 검증하고 저장용 메타데이터를 추출한다. 재계산하지 않는다. */
public record FastApiDiagnosisResponse(
	JsonNode raw,
	String status,
	Integer depletionAge
) {

	private static final Set<String> ALLOWED_STATUSES = Set.of("SUFFICIENT", "MIDDLE", "INSUFFICIENT");

	public static FastApiDiagnosisResponse from(JsonNode raw) {
		return from(DiagnosisType.RETIREMENT_ASSET, raw);
	}

	public static FastApiDiagnosisResponse from(DiagnosisType type, JsonNode raw) {
		if (raw == null || !raw.isObject()) {
			throw new IllegalArgumentException("진단 응답은 JSON 객체여야 합니다.");
		}

		if (type == DiagnosisType.EMPLOYEE_PENSION) {
			for (String field : new String[]{"retire_months", "estimated_avg_income", "monthly_pension",
				"lump_sum", "severance_pay", "service_cap_years"}) {
				requireInteger(raw, field);
			}
			requireString(raw, "current_band");
			requireString(raw, "retire_band");
			requireFiniteNumber(raw, "income_factor");
			requireEnum(raw, "cap_basis", Set.of("STATUTORY_TIERED", "STATUTORY_DEFAULT", "DEFAULT_MAX"));
			return new FastApiDiagnosisResponse(raw, null, null);
		}
		if (type == DiagnosisType.RECEIPT_SCENARIOS) {
			requireInteger(raw, "current_age");
			Set<String> kinds = Set.of("NORMAL", "EARLY", "LUMP_SUM", "INSTALLMENT");
			requireEnum(raw, "best_scenario", kinds);
			requireArray(raw, "scenarios");
			Set<String> seen = new HashSet<>();
			for (JsonNode scenario : raw.get("scenarios")) {
				requireEnum(scenario, "scenario_type", kinds);
				if (!seen.add(scenario.get("scenario_type").asString())) {
					throw new IllegalArgumentException("중복 수령방식 결과입니다.");
				}
				validateDepletion(scenario);
				requireNullableInteger(scenario, "break_even_age");
				requireFiniteNumber(scenario, "total_received");
				requireArray(scenario, "timeline");
				validateTimeline(scenario.get("timeline"));
			}
			if (!seen.equals(kinds)) {
				throw new IllegalArgumentException("4가지 수령방식 결과가 필요합니다.");
			}
			return new FastApiDiagnosisResponse(raw, null, null);
		}
		requireInteger(raw, "current_age");
		switch (type) {
			case RETIREMENT_ASSET -> requireFiniteNumber(raw, "monthly_gap");
			case PENSION_REDUCTION -> {
				for (String field : new String[]{"reemployment_income", "monthly_reduction",
					"reduced_monthly_pension", "full_payment_income_threshold"}) {
					requireFiniteNumber(raw, field);
				}
			}
			case RETIREMENT_RECOMMENDATION -> {
				requireFiniteNumber(raw, "required_saving");
				requireFiniteNumber(raw, "required_income");
				requireEnum(raw, "recommendation_type", Set.of("SUFFICIENT", "SAVING_ONLY", "SAVING_AND_INCOME"));
				requireEnum(raw, "target_status", Set.of("SUFFICIENT"));
			}
			default -> throw new IllegalArgumentException("지원하지 않는 진단 유형입니다.");
		}
		requireInteger(raw, "target_age");
		requireArray(raw, "timeline");
		validateTimeline(raw.get("timeline"));

		JsonNode statusNode = raw.get("status");
		if (statusNode == null || !statusNode.isString() || !ALLOWED_STATUSES.contains(statusNode.asString())) {
			throw new IllegalArgumentException("진단 응답의 status가 올바르지 않습니다.");
		}

		Integer depletionAge = validateDepletion(raw);
		return new FastApiDiagnosisResponse(raw, statusNode.asString(), depletionAge);
	}

	private static Integer validateDepletion(JsonNode raw) {
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

		return depletionAge;
	}

	private static void requireString(JsonNode raw, String field) {
		JsonNode node = raw.get(field);
		if (node == null || !node.isString()) {
			throw new IllegalArgumentException("진단 응답의 " + field + "가 올바르지 않습니다.");
		}
	}

	private static void requireEnum(JsonNode raw, String field, Set<String> allowed) {
		requireString(raw, field);
		if (!allowed.contains(raw.get(field).asString())) {
			throw new IllegalArgumentException("진단 응답의 " + field + "가 올바르지 않습니다.");
		}
	}

	private static void requireNullableInteger(JsonNode raw, String field) {
		JsonNode node = raw.get(field);
		if (node == null || (!node.isNull() && !node.isIntegralNumber())) {
			throw new IllegalArgumentException("진단 응답의 " + field + "가 올바르지 않습니다.");
		}
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

	private static void validateTimeline(JsonNode timeline) {
		for (JsonNode point : timeline) {
			if (!point.isObject()) {
				throw new IllegalArgumentException("진단 응답의 timeline 항목은 객체여야 합니다.");
			}
			requireInteger(point, "age");
			requireFiniteNumber(point, "asset");
			requireFiniteNumber(point, "annual_income");
			requireFiniteNumber(point, "annual_expense");
			requireFiniteNumber(point, "annual_gap");
			requireFiniteNumber(point, "cumulative_annual_gap");
		}
	}
}
