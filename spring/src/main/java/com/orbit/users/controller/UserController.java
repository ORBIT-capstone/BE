package com.orbit.users.controller;

import com.orbit.users.dto.SignupRequest;
import com.orbit.users.dto.SignupResponse;
import com.orbit.users.service.UserService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
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

	@PostMapping("/signup")
	@Operation(summary = "회원가입", description = "이메일, 비밀번호, 이름, 생년월일, 성별, 재직 상태로 회원가입합니다.")
	public ResponseEntity<SignupResponse> signup(@Valid @RequestBody SignupRequest request) {
		userService.signup(request);
		return ResponseEntity.status(HttpStatus.CREATED)
			.body(new SignupResponse("회원가입이 완료되었습니다."));
	}
}
