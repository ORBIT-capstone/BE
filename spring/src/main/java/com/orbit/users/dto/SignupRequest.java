package com.orbit.users.dto;

import com.orbit.users.domain.Gender;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Past;
import jakarta.validation.constraints.Size;
import java.time.LocalDate;

@Schema(description = "회원가입 요청")
public record SignupRequest(
	@Schema(description = "이메일(ID)", example = "user@example.com")
	@NotBlank(message = "이메일은 필수입니다.")
	@Email(message = "이메일 형식이 올바르지 않습니다.")
	String email,

	@Schema(description = "비밀번호", example = "password123", minLength = 8, maxLength = 20)
	@NotBlank(message = "비밀번호는 필수입니다.")
	@Size(min = 8, max = 20, message = "비밀번호는 8자 이상 20자 이하여야 합니다.")
	String password,

	@Schema(description = "이름", example = "홍길동", maxLength = 20)
	@NotBlank(message = "이름은 필수입니다.")
	@Size(max = 20, message = "이름은 20자 이하여야 합니다.")
	String name,

	@Schema(description = "생년월일", example = "1995-01-01", type = "string", format = "date")
	@NotNull(message = "생년월일은 필수입니다.")
	@Past(message = "생년월일은 과거 날짜여야 합니다.")
	LocalDate birthDate,

	@Schema(description = "성별", example = "MALE", allowableValues = {"MALE", "FEMALE"})
	@NotNull(message = "성별은 필수입니다.")
	Gender gender
) {
}
