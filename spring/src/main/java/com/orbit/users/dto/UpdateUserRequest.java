package com.orbit.users.dto;

import com.orbit.users.domain.Gender;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Past;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import jakarta.validation.constraints.PositiveOrZero;
import java.time.LocalDate;

@Schema(description = "회원 정보 수정 요청")
public record UpdateUserRequest(
	@Schema(description = "이름", example = "홍길동", maxLength = 20, nullable = true)
	@Pattern(regexp = ".*\\S.*", message = "이름은 공백일 수 없습니다.")
	@Size(max = 20, message = "이름은 20자 이하여야 합니다.")
	String name,

	@Schema(description = "생년월일", example = "1995-01-01", type = "string", format = "date", nullable = true)
	@Past(message = "생년월일은 과거 날짜여야 합니다.")
	LocalDate birthDate,

	@Schema(description = "성별", example = "MALE", allowableValues = {"MALE", "FEMALE"}, nullable = true)
	Gender gender,

	@Schema(description = "보유 자산(원). 생략/null이면 기존 값 유지", nullable = true)
	@PositiveOrZero
	Long asset,

	@Schema(description = "월 지출액(원). 생략/null이면 기존 값 유지", nullable = true)
	@PositiveOrZero
	Long monthlyExpenses,

	@Schema(description = "현재 근속연수(년). 생략/null이면 기존 값 유지", nullable = true)
	@PositiveOrZero
	Integer currentYears,

	@Schema(description = "월 연금 수령액(원). 생략/null이면 기존 값 유지", nullable = true)
	@PositiveOrZero
	Long monthlyPension
) {
}
