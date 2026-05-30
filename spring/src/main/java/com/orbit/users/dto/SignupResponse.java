package com.orbit.users.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "회원가입 응답")
public record SignupResponse(
	@Schema(description = "회원가입 성공 메시지", example = "회원가입이 완료되었습니다.")
	String message
) {
}
