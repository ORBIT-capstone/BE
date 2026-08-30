package com.orbit.diagnoses.dto;

import com.orbit.diagnoses.domain.Diagnosis;
import com.orbit.diagnoses.domain.DiagnosisType;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;
import tools.jackson.databind.JsonNode;

@Schema(description = "진단 결과 상세")
public record DiagnosisDetailResponse(
	@Schema(description = "진단 ID")
	Long id,

	@Schema(description = "계산 기능 구분")
	DiagnosisType diagnosisType,

	@Schema(description = "노후 준비 상태. 재직자 연금/수령방식 비교는 최상위 상태가 없어 null", nullable = true)
	String status,

	@Schema(description = "자산 고갈 나이. 재직자 연금/수령방식 비교는 최상위 값이 없어 null", nullable = true)
	Integer depletionAge,

	@Schema(description = "생성 일시")
	LocalDateTime createdAt,

	@Schema(description = "저장 요청으로 받은 계산 응답 원본 전체. snake_case 필드와 timeline/scenarios를 그대로 보존",
		oneOf = {DiagnosisResultBodies.RetirementAssetResult.class, DiagnosisResultBodies.PensionReductionResult.class,
			DiagnosisResultBodies.RetirementRecommendationResult.class, DiagnosisResultBodies.EmployeePensionResult.class,
			DiagnosisResultBodies.ReceiptScenariosResult.class})
	JsonNode result
) {

	public static DiagnosisDetailResponse from(Diagnosis diagnosis, JsonNode result) {
		return new DiagnosisDetailResponse(
			diagnosis.getId(),
			diagnosis.getDiagnosisType(),
			diagnosis.getStatus(),
			diagnosis.getDepletionAge(),
			diagnosis.getCreatedAt(),
			result
		);
	}
}
