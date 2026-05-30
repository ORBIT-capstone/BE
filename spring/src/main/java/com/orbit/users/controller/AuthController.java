package com.orbit.users.controller;

import com.orbit.users.dto.RefreshTokenRequest;
import com.orbit.users.dto.TokenResponse;
import com.orbit.users.service.AuthService;
import io.swagger.v3.oas.annotations.Operation;
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
	@Operation(summary = "토큰 재발급", description = "리프레시 토큰을 검증하고 새 액세스 토큰과 리프레시 토큰을 발급합니다.")
	public ResponseEntity<TokenResponse> refresh(@Valid @RequestBody RefreshTokenRequest request) {
		return ResponseEntity.ok(authService.refresh(request.refreshToken()));
	}
}
