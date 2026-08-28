package com.orbit.diagnoses.controller;

import com.orbit.global.exception.ErrorResponse;
import com.orbit.global.auth.AuthenticatedUser;
import com.orbit.users.domain.User;
import com.orbit.diagnoses.dto.DiagnosisDetailResponse;
import com.orbit.diagnoses.dto.DiagnosisRequest;
import com.orbit.diagnoses.dto.DiagnosisSummaryResponse;
import com.orbit.diagnoses.service.DiagnosisService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
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
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/diagnoses")
@RequiredArgsConstructor
@Tag(name = "Diagnoses", description = "진단 결과 저장/조회 API")
public class DiagnosisController {

	private final DiagnosisService diagnosisService;

	@PostMapping
	@SecurityRequirement(name = "bearerAuth")
	@Operation(summary = "진단 실행 및 저장", description = "FastAPI 진단 결과를 계산해 저장하고 생성된 진단 ID와 상세 결과를 반환합니다.")
	@ApiResponses({
		@ApiResponse(responseCode = "400", description = "진단 입력값 검증 실패", content = @Content(schema = @Schema(implementation = ErrorResponse.class))),
		@ApiResponse(responseCode = "401", description = "인증 정보가 없거나 유효하지 않음", content = @Content(schema = @Schema(implementation = ErrorResponse.class))),
		@ApiResponse(responseCode = "502", description = "진단 서버 연결 실패 또는 비정상 응답", content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
	})
	public ResponseEntity<DiagnosisDetailResponse> create(
		@Parameter(hidden = true) @AuthenticatedUser User user,
		@Valid @RequestBody DiagnosisRequest request
	) {
		DiagnosisDetailResponse result = diagnosisService.createDiagnosis(user.getId(), request);
		return ResponseEntity.status(HttpStatus.CREATED).body(result);
	}

	@GetMapping
	@SecurityRequirement(name = "bearerAuth")
	@Operation(summary = "진단 목록 조회", description = "로그인한 회원의 진단 결과 목록을 생성일 최신순으로 조회합니다.")
	@ApiResponse(responseCode = "401", description = "인증 정보가 없거나 유효하지 않음", content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
	public ResponseEntity<List<DiagnosisSummaryResponse>> list(
		@Parameter(hidden = true) @AuthenticatedUser User user
	) {
		return ResponseEntity.ok(diagnosisService.getSummaries(user.getId()));
	}

	@GetMapping("/{id}")
	@SecurityRequirement(name = "bearerAuth")
	@Operation(summary = "진단 상세 조회", description = "로그인한 회원의 진단 결과를 상세 조회합니다.")
	@ApiResponses({
		@ApiResponse(responseCode = "400", description = "진단 ID 형식 오류", content = @Content(schema = @Schema(implementation = ErrorResponse.class))),
		@ApiResponse(responseCode = "401", description = "인증 정보가 없거나 유효하지 않음", content = @Content(schema = @Schema(implementation = ErrorResponse.class))),
		@ApiResponse(responseCode = "404", description = "진단 결과를 찾을 수 없음", content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
	})
	public ResponseEntity<DiagnosisDetailResponse> get(
		@Parameter(hidden = true) @AuthenticatedUser User user,
		@PathVariable Long id
	) {
		return ResponseEntity.ok(diagnosisService.getDetail(user.getId(), id));
	}
}
