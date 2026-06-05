package com.orbit.users.dto;

import com.orbit.users.domain.EmploymentStatus;
import com.orbit.users.domain.Gender;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Past;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
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

	@Schema(description = "재직 상태", example = "employees", allowableValues = {"employees", "retirees"}, nullable = true)
	EmploymentStatus employmentStatus
) {
}
