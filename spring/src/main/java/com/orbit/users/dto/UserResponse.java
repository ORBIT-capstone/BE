package com.orbit.users.dto;

import com.orbit.users.domain.Gender;
import com.orbit.users.domain.User;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDate;

@Schema(description = "회원 정보 응답")
public record UserResponse(
	@Schema(description = "이메일", example = "user@example.com")
	String email,

	@Schema(description = "이름", example = "홍길동")
	String name,

	@Schema(description = "생년월일", example = "1995-01-01", type = "string", format = "date")
	LocalDate birthDate,

	@Schema(description = "성별", example = "MALE", allowableValues = {"MALE", "FEMALE"})
	Gender gender,

	@Schema(description = "보유 자산(원)", nullable = true)
	Long asset,

	@Schema(description = "월 지출액(원)", nullable = true)
	Long monthlyExpenses,

	@Schema(description = "현재 근속연수(년)", nullable = true)
	Integer currentYears,

	@Schema(description = "월 연금 수령액(원)", nullable = true)
	Long monthlyPension,

	@Schema(description = "세전 월 소득(원)", example = "4000000", nullable = true)
	Long monthlyIncome
) {

	public static UserResponse from(User user) {
		return new UserResponse(
			user.getEmail(),
			user.getName(),
			user.getBirthDate(),
			user.getGender(),
			user.getAsset(),
			user.getMonthlyExpenses(),
			user.getCurrentYears(),
			user.getMonthlyPension(),
			user.getMonthlyIncome()
		);
	}
}
