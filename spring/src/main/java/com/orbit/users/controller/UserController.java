package com.orbit.users.controller;

import com.orbit.global.exception.ErrorResponse;
import com.orbit.global.auth.AuthenticatedUser;
import com.orbit.users.domain.User;
import com.orbit.users.dto.LoginRequest;
import com.orbit.users.dto.MessageResponse;
import com.orbit.users.dto.RefreshTokenRequest;
import com.orbit.users.dto.SignupRequest;
import com.orbit.users.dto.SignupResponse;
import com.orbit.users.dto.TokenResponse;
import com.orbit.users.dto.UpdateUserRequest;
import com.orbit.users.dto.UserResponse;
import com.orbit.users.service.AuthService;
import com.orbit.users.service.UserService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
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
	@Operation(summary = "회원가입", description = "이메일, 비밀번호, 이름, 생년월일, 성별로 회원가입합니다.")
	@ApiResponses({
		@ApiResponse(responseCode = "400", description = "회원가입 입력값 검증 실패", content = @Content(schema = @Schema(implementation = ErrorResponse.class))),
		@ApiResponse(responseCode = "409", description = "이미 가입된 이메일", content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
	})
	public ResponseEntity<SignupResponse> signup(@Valid @RequestBody SignupRequest request) {
		userService.signup(request);
		return ResponseEntity.status(HttpStatus.CREATED)
			.body(new SignupResponse("회원가입이 완료되었습니다."));
	}

	@PostMapping("/login")
	@Operation(summary = "로그인", description = "이메일과 비밀번호로 로그인하고 액세스 토큰과 리프레시 토큰을 발급합니다.")
	@ApiResponses({
		@ApiResponse(responseCode = "400", description = "로그인 입력값 검증 실패", content = @Content(schema = @Schema(implementation = ErrorResponse.class))),
		@ApiResponse(responseCode = "401", description = "이메일 또는 비밀번호 불일치", content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
	})
	public ResponseEntity<TokenResponse> login(@Valid @RequestBody LoginRequest request) {
		return ResponseEntity.ok(authService.login(request));
	}

	@GetMapping("/me")
	@SecurityRequirement(name = "bearerAuth")
	@Operation(summary = "회원 정보 조회", description = "현재 로그인한 회원의 정보를 조회합니다.")
	@ApiResponse(responseCode = "401", description = "인증 정보가 없거나 유효하지 않음", content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
	public ResponseEntity<UserResponse> getMe(
		@Parameter(hidden = true) @AuthenticatedUser User user
	) {
		return ResponseEntity.ok(UserResponse.from(user));
	}

	@PatchMapping("/me")
	@SecurityRequirement(name = "bearerAuth")
	@Operation(summary = "회원 정보 수정", description = "현재 로그인한 회원의 이름, 생년월일, 성별을 수정합니다.")
	@ApiResponses({
		@ApiResponse(responseCode = "400", description = "회원 정보 입력값 검증 실패", content = @Content(schema = @Schema(implementation = ErrorResponse.class))),
		@ApiResponse(responseCode = "401", description = "인증 정보가 없거나 유효하지 않음", content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
	})
	public ResponseEntity<UserResponse> updateMe(
		@Parameter(hidden = true) @AuthenticatedUser User user,
		@Valid @RequestBody UpdateUserRequest request
	) {
		User updatedUser = userService.update(user.getId(), request);
		return ResponseEntity.ok(UserResponse.from(updatedUser));
	}

	@PostMapping("/logout")
	@SecurityRequirement(name = "bearerAuth")
	@Operation(summary = "로그아웃", description = "리프레시 토큰을 검증하고 무효화합니다.")
	@ApiResponses({
		@ApiResponse(responseCode = "400", description = "요청 값 검증 실패", content = @Content(schema = @Schema(implementation = ErrorResponse.class))),
		@ApiResponse(responseCode = "401", description = "액세스 토큰 또는 리프레시 토큰이 유효하지 않음", content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
	})
	public ResponseEntity<MessageResponse> logout(
		@Parameter(hidden = true) @AuthenticatedUser User user,
		@Valid @RequestBody RefreshTokenRequest request
	) {
		authService.logout(user.getId(), request.refreshToken());
		return ResponseEntity.ok(new MessageResponse("로그아웃이 완료되었습니다."));
	}

	@DeleteMapping("/me")
	@SecurityRequirement(name = "bearerAuth")
	@Operation(summary = "회원 탈퇴", description = "현재 로그인한 사용자를 탈퇴 처리합니다.")
	@ApiResponse(responseCode = "401", description = "인증 정보가 없거나 유효하지 않음", content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
	public ResponseEntity<MessageResponse> deleteMe(
		@Parameter(hidden = true) @AuthenticatedUser User user
	) {
		userService.delete(user);
		return ResponseEntity.ok(new MessageResponse("회원 탈퇴가 완료되었습니다."));
	}
}
