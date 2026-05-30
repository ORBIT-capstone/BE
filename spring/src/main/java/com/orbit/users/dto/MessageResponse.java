package com.orbit.users.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "메시지 응답")
public record MessageResponse(
	@Schema(description = "처리 결과 메시지")
	String message
) {
}
