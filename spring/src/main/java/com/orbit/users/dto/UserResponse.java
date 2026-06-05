package com.orbit.users.dto;

import com.orbit.users.domain.EmploymentStatus;
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

	@Schema(description = "재직 상태", example = "employees", allowableValues = {"employees", "retirees"})
	EmploymentStatus employmentStatus
) {

	public static UserResponse from(User user) {
		return new UserResponse(
			user.getEmail(),
			user.getName(),
			user.getBirthDate(),
			user.getGender(),
			user.getEmploymentStatus()
		);
	}
}
