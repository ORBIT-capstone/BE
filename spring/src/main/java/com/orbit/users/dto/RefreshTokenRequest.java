package com.orbit.users.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

@Schema(description = "토큰 재발급 요청")
public record RefreshTokenRequest(
	@Schema(description = "리프레시 토큰")
	@NotBlank(message = "리프레시 토큰은 필수입니다.")
	String refreshToken
) {
}
