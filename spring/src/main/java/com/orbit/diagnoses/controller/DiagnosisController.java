package com.orbit.diagnoses.controller;

import com.orbit.diagnoses.dto.DiagnosisDetailResponse;
import com.orbit.diagnoses.dto.DiagnosisRequest;
import com.orbit.diagnoses.dto.DiagnosisSummaryResponse;
import com.orbit.diagnoses.service.DiagnosisService;
import com.orbit.users.domain.User;
import com.orbit.users.service.AuthService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import tools.jackson.databind.JsonNode;

@RestController
@RequestMapping("/api/diagnoses")
@RequiredArgsConstructor
@Tag(name = "Diagnoses", description = "진단 결과 저장/조회 API")
public class DiagnosisController {

	private final DiagnosisService diagnosisService;
	private final AuthService authService;

	@PostMapping
	@SecurityRequirement(name = "bearerAuth")
	@Operation(summary = "진단 실행 및 저장", description = "FastAPI 진단 결과를 계산해 저장하고 결과를 그대로 반환합니다.")
	public ResponseEntity<JsonNode> create(
		@Parameter(hidden = true) @RequestHeader(value = "Authorization", required = false) String authorizationHeader,
		@Valid @RequestBody DiagnosisRequest request
	) {
		User user = authService.getUserFromAuthorizationHeader(authorizationHeader);
		JsonNode result = diagnosisService.createDiagnosis(user.getId(), request);
		return ResponseEntity.status(HttpStatus.CREATED).body(result);
	}

	@GetMapping
	@SecurityRequirement(name = "bearerAuth")
	@Operation(summary = "진단 목록 조회", description = "로그인한 회원의 진단 결과 목록을 생성일 최신순으로 조회합니다.")
	public ResponseEntity<List<DiagnosisSummaryResponse>> list(
		@Parameter(hidden = true) @RequestHeader(value = "Authorization", required = false) String authorizationHeader
	) {
		User user = authService.getUserFromAuthorizationHeader(authorizationHeader);
		return ResponseEntity.ok(diagnosisService.getSummaries(user.getId()));
	}

	@GetMapping("/{id}")
	@SecurityRequirement(name = "bearerAuth")
	@Operation(summary = "진단 상세 조회", description = "로그인한 회원의 진단 결과를 상세 조회합니다.")
	public ResponseEntity<DiagnosisDetailResponse> get(
		@Parameter(hidden = true) @RequestHeader(value = "Authorization", required = false) String authorizationHeader,
		@PathVariable Long id
	) {
		User user = authService.getUserFromAuthorizationHeader(authorizationHeader);
		return ResponseEntity.ok(diagnosisService.getDetail(user.getId(), id));
	}
}
