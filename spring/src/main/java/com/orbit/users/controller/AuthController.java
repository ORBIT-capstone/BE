package com.orbit.users.controller;

import com.orbit.global.exception.ErrorResponse;
import com.orbit.users.dto.RefreshTokenRequest;
import com.orbit.users.dto.TokenResponse;
import com.orbit.users.service.AuthService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
@Tag(name = "Auth", description = "인증 API")
public class AuthController {

	private final AuthService authService;

	@PostMapping("/refresh")
	@Operation(summary = "토큰 재발급", description = "리프레시 토큰을 검증하고 새 액세스 토큰과 리프레시 토큰을 발급합니다. 기존 액세스 토큰과 리프레시 토큰은 즉시 무효화됩니다.")
	@ApiResponses({
		@ApiResponse(responseCode = "400", description = "요청 값 검증 실패", content = @Content(schema = @Schema(implementation = ErrorResponse.class))),
		@ApiResponse(responseCode = "401", description = "유효하지 않은 리프레시 토큰", content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
	})
	public ResponseEntity<TokenResponse> refresh(@Valid @RequestBody RefreshTokenRequest request) {
		return ResponseEntity.ok(authService.refresh(request.refreshToken()));
	}
}
