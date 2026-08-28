package com.orbit.diagnoses.dto;

import com.orbit.diagnoses.domain.Diagnosis;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;
import tools.jackson.databind.JsonNode;

@Schema(description = "진단 결과 상세")
public record DiagnosisDetailResponse(
	@Schema(description = "진단 ID")
	Long id,

	@Schema(description = "노후 준비 상태")
	String status,

	@Schema(description = "자산 고갈 나이")
	Integer depletionAge,

	@Schema(description = "생성 일시")
	LocalDateTime createdAt,

	@Schema(description = "FastAPI 진단 결과 전체")
	JsonNode result
) {

	public static DiagnosisDetailResponse from(Diagnosis diagnosis, JsonNode result) {
		return new DiagnosisDetailResponse(
			diagnosis.getId(),
			diagnosis.getStatus(),
			diagnosis.getDepletionAge(),
			diagnosis.getCreatedAt(),
			result
		);
	}
}
