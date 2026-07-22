package com.orbit.diagnoses.dto;

import com.orbit.users.domain.Gender;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.PositiveOrZero;

@Schema(description = "은퇴 자산 진단 요청")
public record DiagnosisRequest(
	@Schema(description = "현재 나이", example = "60")
	@NotNull
	@Positive
	Integer currentAge,

	@Schema(description = "월 생활비", example = "250")
	@NotNull
	@Positive
	Double monthlyExpenses,

	@Schema(description = "월 연금 수령액", example = "150")
	@NotNull
	@PositiveOrZero
	Double monthlyPension,

	@Schema(description = "현재 보유 자산", example = "10000")
	@NotNull
	@PositiveOrZero
	Double asset,

	@Schema(description = "성별", example = "MALE", allowableValues = {"MALE", "FEMALE"})
	@NotNull
	Gender gender
) {
}
