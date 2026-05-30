package com.orbit.users.controller;

import com.orbit.users.domain.User;
import com.orbit.users.dto.LoginRequest;
import com.orbit.users.dto.MessageResponse;
import com.orbit.users.dto.RefreshTokenRequest;
import com.orbit.users.dto.SignupRequest;
import com.orbit.users.dto.SignupResponse;
import com.orbit.users.dto.TokenResponse;
import com.orbit.users.service.AuthService;
import com.orbit.users.service.UserService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/users")
@RequiredArgsConstructor
@Tag(name = "Users", description = "회원 API")
public class UserController {

	private final UserService userService;
	private final AuthService authService;

	@PostMapping("/signup")
	@Operation(summary = "회원가입", description = "이메일, 비밀번호, 이름, 생년월일, 성별, 재직 상태로 회원가입합니다.")
	public ResponseEntity<SignupResponse> signup(@Valid @RequestBody SignupRequest request) {
		userService.signup(request);
		return ResponseEntity.status(HttpStatus.CREATED)
			.body(new SignupResponse("회원가입이 완료되었습니다."));
	}

	@PostMapping("/login")
	@Operation(summary = "로그인", description = "이메일과 비밀번호로 로그인하고 액세스 토큰과 리프레시 토큰을 발급합니다.")
	public ResponseEntity<TokenResponse> login(@Valid @RequestBody LoginRequest request) {
		return ResponseEntity.ok(authService.login(request));
	}

	@PostMapping("/logout")
	@SecurityRequirement(name = "bearerAuth")
	@Operation(summary = "로그아웃", description = "리프레시 토큰을 검증하고 무효화합니다.")
	public ResponseEntity<MessageResponse> logout(
		@Parameter(hidden = true) @RequestHeader(value = "Authorization", required = false) String authorizationHeader,
		@Valid @RequestBody RefreshTokenRequest request
	) {
		authService.logout(authorizationHeader, request.refreshToken());
		return ResponseEntity.ok(new MessageResponse("로그아웃이 완료되었습니다."));
	}

	@DeleteMapping("/me")
	@SecurityRequirement(name = "bearerAuth")
	@Operation(summary = "회원 탈퇴", description = "현재 로그인한 사용자를 탈퇴 처리합니다.")
	public ResponseEntity<MessageResponse> deleteMe(
		@Parameter(hidden = true) @RequestHeader(value = "Authorization", required = false) String authorizationHeader
	) {
		User user = authService.getUserFromAuthorizationHeader(authorizationHeader);
		userService.delete(user);
		return ResponseEntity.ok(new MessageResponse("회원 탈퇴가 완료되었습니다."));
	}
}
