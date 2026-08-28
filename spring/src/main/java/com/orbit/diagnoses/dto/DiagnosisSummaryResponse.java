package com.orbit.diagnoses.dto;

import com.orbit.diagnoses.domain.Diagnosis;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

@Schema(description = "진단 결과 목록 항목")
public record DiagnosisSummaryResponse(
	@Schema(description = "진단 ID")
	Long id,

	@Schema(description = "노후 준비 상태")
	String status,

	@Schema(description = "자산 고갈 나이")
	Integer depletionAge,

	@Schema(description = "생성 일시")
	LocalDateTime createdAt
) {

	public static DiagnosisSummaryResponse from(Diagnosis diagnosis) {
		return new DiagnosisSummaryResponse(
			diagnosis.getId(),
			diagnosis.getStatus(),
			diagnosis.getDepletionAge(),
			diagnosis.getCreatedAt()
		);
	}
}
