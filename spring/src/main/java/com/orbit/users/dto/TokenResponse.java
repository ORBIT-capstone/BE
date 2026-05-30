package com.orbit.users.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "토큰 응답")
public record TokenResponse(
	@Schema(description = "인증 타입", example = "Bearer")
	String tokenType,

	@Schema(description = "액세스 토큰")
	String accessToken,

	@Schema(description = "리프레시 토큰")
	String refreshToken
) {
	public static TokenResponse bearer(String accessToken, String refreshToken) {
		return new TokenResponse("Bearer", accessToken, refreshToken);
	}
}
