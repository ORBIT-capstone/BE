package com.orbit.diagnoses.dto;

import com.orbit.diagnoses.domain.Diagnosis;
import com.orbit.diagnoses.domain.DiagnosisType;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

@Schema(description = "진단 결과 요약")
public record DiagnosisSummaryResponse(
	@Schema(description = "진단 ID")
	Long id,

	@Schema(description = "계산 기능 구분")
	DiagnosisType diagnosisType,

	@Schema(description = "노후 준비 상태. 재직자 연금/수령방식 비교는 최상위 상태가 없어 null", nullable = true)
	String status,

	@Schema(description = "자산 고갈 나이. 재직자 연금/수령방식 비교는 최상위 값이 없어 null", nullable = true)
	Integer depletionAge,

	@Schema(description = "생성 일시")
	LocalDateTime createdAt
) {

	public static DiagnosisSummaryResponse from(Diagnosis diagnosis) {
		return new DiagnosisSummaryResponse(
			diagnosis.getId(),
			diagnosis.getDiagnosisType(),
			diagnosis.getStatus(),
			diagnosis.getDepletionAge(),
			diagnosis.getCreatedAt()
		);
	}
}
