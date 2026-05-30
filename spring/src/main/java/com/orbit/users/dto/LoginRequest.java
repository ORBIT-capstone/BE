package com.orbit.users.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

@Schema(description = "로그인 요청")
public record LoginRequest(
	@Schema(description = "이메일", example = "user@example.com")
	@NotBlank(message = "이메일은 필수입니다.")
	@Email(message = "이메일 형식이 올바르지 않습니다.")
	String email,

	@Schema(description = "비밀번호", example = "password123", minLength = 8, maxLength = 20)
	@NotBlank(message = "비밀번호는 필수입니다.")
	@Size(min = 8, max = 20, message = "비밀번호는 8자 이상 20자 이하여야 합니다.")
	String password
) {
}
