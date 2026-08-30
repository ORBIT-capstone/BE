package com.orbit.diagnoses.controller;

import com.orbit.diagnoses.domain.DiagnosisType;
import com.orbit.diagnoses.dto.DiagnosisDetailResponse;
import com.orbit.diagnoses.dto.DiagnosisResultBodies;
import com.orbit.diagnoses.service.DiagnosisService;
import com.orbit.global.auth.AuthenticatedUser;
import com.orbit.global.exception.ErrorResponse;
import com.orbit.users.domain.User;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import tools.jackson.databind.JsonNode;

@RestController
@RequestMapping("/api/diagnoses")
@RequiredArgsConstructor
@SecurityRequirement(name = "bearerAuth")
@Tag(name = "Diagnoses", description = "기능별 계산 응답 원본 저장/조회 API")
@ApiResponse(responseCode = "400", description = "계산 결과 형식 또는 ID 오류", content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
@ApiResponse(responseCode = "401", description = "인증 정보가 없거나 유효하지 않음", content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
public class DiagnosisController {
    private final DiagnosisService diagnosisService;

    @PostMapping("/retirement/diagnosis")
    @Operation(summary = "은퇴자산 진단 결과 저장",
        description = "프론트가 받은 계산 API의 response body 전체를 그대로 보냅니다. result로 감싸지 않으며, 재계산 없이 로그인 사용자 소유로 저장합니다.")
    @ApiResponse(responseCode = "201", description = "계산 결과 원본 저장 완료",
        content = @Content(schema = @Schema(implementation = DiagnosisDetailResponse.class)))
    public ResponseEntity<DiagnosisDetailResponse> saveRetirementAsset(
        @Parameter(hidden = true) @AuthenticatedUser User user,
        @io.swagger.v3.oas.annotations.parameters.RequestBody(required = true,
            content = @Content(schema = @Schema(implementation = DiagnosisResultBodies.RetirementAssetResult.class)))
        @RequestBody JsonNode result
    ) {
        return ResponseEntity.status(HttpStatus.CREATED)
            .body(diagnosisService.saveResult(user.getId(), DiagnosisType.RETIREMENT_ASSET, result));
    }

    @GetMapping("/retirement/diagnosis/{id}")
    @Operation(summary = "은퇴자산 진단 결과 조회",
        description = "본인이 저장한 해당 기능의 계산 응답 전체를 result에 그대로 반환합니다. 재계산하지 않습니다.")
    @ApiResponse(responseCode = "404", description = "본인 소유의 해당 기능 결과를 찾을 수 없음", content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
    public ResponseEntity<DiagnosisDetailResponse> getRetirementAsset(
        @Parameter(hidden = true) @AuthenticatedUser User user,
        @PathVariable Long id
    ) {
        return ResponseEntity.ok(diagnosisService.getDetail(user.getId(), id, DiagnosisType.RETIREMENT_ASSET));
    }

    @PostMapping("/retirement/reduction")
    @Operation(summary = "재취업 연금 감액 계산 결과 저장",
        description = "프론트가 받은 계산 API의 response body 전체를 그대로 보냅니다. result로 감싸지 않으며, 재계산 없이 로그인 사용자 소유로 저장합니다.")
    @ApiResponse(responseCode = "201", description = "계산 결과 원본 저장 완료",
        content = @Content(schema = @Schema(implementation = DiagnosisDetailResponse.class)))
    public ResponseEntity<DiagnosisDetailResponse> savePensionReduction(
        @Parameter(hidden = true) @AuthenticatedUser User user,
        @io.swagger.v3.oas.annotations.parameters.RequestBody(required = true,
            content = @Content(schema = @Schema(implementation = DiagnosisResultBodies.PensionReductionResult.class)))
        @RequestBody JsonNode result
    ) {
        return ResponseEntity.status(HttpStatus.CREATED)
            .body(diagnosisService.saveResult(user.getId(), DiagnosisType.PENSION_REDUCTION, result));
    }

    @GetMapping("/retirement/reduction/{id}")
    @Operation(summary = "재취업 연금 감액 계산 결과 조회",
        description = "본인이 저장한 해당 기능의 계산 응답 전체를 result에 그대로 반환합니다. 재계산하지 않습니다.")
    @ApiResponse(responseCode = "404", description = "본인 소유의 해당 기능 결과를 찾을 수 없음", content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
    public ResponseEntity<DiagnosisDetailResponse> getPensionReduction(
        @Parameter(hidden = true) @AuthenticatedUser User user,
        @PathVariable Long id
    ) {
        return ResponseEntity.ok(diagnosisService.getDetail(user.getId(), id, DiagnosisType.PENSION_REDUCTION));
    }

    @PostMapping("/retirement/recommendations")
    @Operation(summary = "노후 준비 개선 추천 결과 저장",
        description = "프론트가 받은 계산 API의 response body 전체를 그대로 보냅니다. result로 감싸지 않으며, 재계산 없이 로그인 사용자 소유로 저장합니다.")
    @ApiResponse(responseCode = "201", description = "계산 결과 원본 저장 완료",
        content = @Content(schema = @Schema(implementation = DiagnosisDetailResponse.class)))
    public ResponseEntity<DiagnosisDetailResponse> saveRetirementRecommendation(
        @Parameter(hidden = true) @AuthenticatedUser User user,
        @io.swagger.v3.oas.annotations.parameters.RequestBody(required = true,
            content = @Content(schema = @Schema(implementation = DiagnosisResultBodies.RetirementRecommendationResult.class)))
        @RequestBody JsonNode result
    ) {
        return ResponseEntity.status(HttpStatus.CREATED)
            .body(diagnosisService.saveResult(user.getId(), DiagnosisType.RETIREMENT_RECOMMENDATION, result));
    }

    @GetMapping("/retirement/recommendations/{id}")
    @Operation(summary = "노후 준비 개선 추천 결과 조회",
        description = "본인이 저장한 해당 기능의 계산 응답 전체를 result에 그대로 반환합니다. 재계산하지 않습니다.")
    @ApiResponse(responseCode = "404", description = "본인 소유의 해당 기능 결과를 찾을 수 없음", content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
    public ResponseEntity<DiagnosisDetailResponse> getRetirementRecommendation(
        @Parameter(hidden = true) @AuthenticatedUser User user,
        @PathVariable Long id
    ) {
        return ResponseEntity.ok(diagnosisService.getDetail(user.getId(), id, DiagnosisType.RETIREMENT_RECOMMENDATION));
    }

    @PostMapping("/employees/simulate")
    @Operation(summary = "재직자 연금 시뮬레이션 결과 저장",
        description = "프론트가 받은 계산 API의 response body 전체를 그대로 보냅니다. result로 감싸지 않으며, 재계산 없이 로그인 사용자 소유로 저장합니다.")
    @ApiResponse(responseCode = "201", description = "계산 결과 원본 저장 완료",
        content = @Content(schema = @Schema(implementation = DiagnosisDetailResponse.class)))
    public ResponseEntity<DiagnosisDetailResponse> saveEmployeePension(
        @Parameter(hidden = true) @AuthenticatedUser User user,
        @io.swagger.v3.oas.annotations.parameters.RequestBody(required = true,
            content = @Content(schema = @Schema(implementation = DiagnosisResultBodies.EmployeePensionResult.class)))
        @RequestBody JsonNode result
    ) {
        return ResponseEntity.status(HttpStatus.CREATED)
            .body(diagnosisService.saveResult(user.getId(), DiagnosisType.EMPLOYEE_PENSION, result));
    }

    @GetMapping("/employees/simulate/{id}")
    @Operation(summary = "재직자 연금 시뮬레이션 결과 조회",
        description = "본인이 저장한 해당 기능의 계산 응답 전체를 result에 그대로 반환합니다. 재계산하지 않습니다.")
    @ApiResponse(responseCode = "404", description = "본인 소유의 해당 기능 결과를 찾을 수 없음", content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
    public ResponseEntity<DiagnosisDetailResponse> getEmployeePension(
        @Parameter(hidden = true) @AuthenticatedUser User user,
        @PathVariable Long id
    ) {
        return ResponseEntity.ok(diagnosisService.getDetail(user.getId(), id, DiagnosisType.EMPLOYEE_PENSION));
    }

    @PostMapping("/employees/scenarios")
    @Operation(summary = "수령방식별 시나리오 비교 결과 저장",
        description = "프론트가 받은 계산 API의 response body 전체를 그대로 보냅니다. result로 감싸지 않으며, 재계산 없이 로그인 사용자 소유로 저장합니다.")
    @ApiResponse(responseCode = "201", description = "계산 결과 원본 저장 완료",
        content = @Content(schema = @Schema(implementation = DiagnosisDetailResponse.class)))
    public ResponseEntity<DiagnosisDetailResponse> saveReceiptScenarios(
        @Parameter(hidden = true) @AuthenticatedUser User user,
        @io.swagger.v3.oas.annotations.parameters.RequestBody(required = true,
            content = @Content(schema = @Schema(implementation = DiagnosisResultBodies.ReceiptScenariosResult.class)))
        @RequestBody JsonNode result
    ) {
        return ResponseEntity.status(HttpStatus.CREATED)
            .body(diagnosisService.saveResult(user.getId(), DiagnosisType.RECEIPT_SCENARIOS, result));
    }

    @GetMapping("/employees/scenarios/{id}")
    @Operation(summary = "수령방식별 시나리오 비교 결과 조회",
        description = "본인이 저장한 해당 기능의 계산 응답 전체를 result에 그대로 반환합니다. 재계산하지 않습니다.")
    @ApiResponse(responseCode = "404", description = "본인 소유의 해당 기능 결과를 찾을 수 없음", content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
    public ResponseEntity<DiagnosisDetailResponse> getReceiptScenarios(
        @Parameter(hidden = true) @AuthenticatedUser User user,
        @PathVariable Long id
    ) {
        return ResponseEntity.ok(diagnosisService.getDetail(user.getId(), id, DiagnosisType.RECEIPT_SCENARIOS));
    }

}
