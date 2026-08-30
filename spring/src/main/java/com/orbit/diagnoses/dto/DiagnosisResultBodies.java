package com.orbit.diagnoses.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.math.BigInteger;
import java.util.List;

/**
 * 저장 요청의 OpenAPI 스키마. 필드명은 FastAPI 응답과 동일한 snake_case다.
 * 실제 본문은 JsonNode로 받아 추가 필드도 보존하며 FastApiDiagnosisResponse에서 계약을 검증한다.
 */
public final class DiagnosisResultBodies {
    private DiagnosisResultBodies() {}

    public enum ReadinessStatus { SUFFICIENT, MIDDLE, INSUFFICIENT }
    public enum RecommendationType { SUFFICIENT, SAVING_ONLY, SAVING_AND_INCOME }
    public enum ScenarioType { NORMAL, EARLY, LUMP_SUM, INSTALLMENT }
    public enum CapBasis { STATUTORY_TIERED, STATUTORY_DEFAULT, DEFAULT_MAX }

    @Schema(name = "TimelinePoint", description = "계산 API 응답 본문 그대로 사용. 금액은 원 단위",
        requiredProperties = {"age", "asset", "annual_income", "annual_expense", "annual_gap", "cumulative_annual_gap"})
    public record TimelinePoint(
        Integer age,
        BigInteger asset,
        BigInteger annual_income,
        BigInteger annual_expense,
        BigInteger annual_gap,
        BigInteger cumulative_annual_gap
    ) {}

    @Schema(name = "RetirementAssetResult", description = "계산 API 응답 본문 그대로 사용. 금액은 원 단위",
        requiredProperties = {"current_age", "monthly_gap", "depletion_age", "depleted", "target_age", "status", "timeline"})
    public record RetirementAssetResult(
        Integer current_age,
        BigInteger monthly_gap,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED)
        Integer depletion_age,
        Boolean depleted,
        Integer target_age,
        ReadinessStatus status,
        List<TimelinePoint> timeline
    ) {}

    @Schema(name = "PensionReductionResult", description = "계산 API 응답 본문 그대로 사용. 금액은 원 단위",
        requiredProperties = {"current_age", "reemployment_income", "monthly_reduction", "reduced_monthly_pension", "full_payment_income_threshold", "depletion_age", "depleted", "target_age", "status", "timeline"})
    public record PensionReductionResult(
        Integer current_age,
        BigInteger reemployment_income,
        BigInteger monthly_reduction,
        BigInteger reduced_monthly_pension,
        BigInteger full_payment_income_threshold,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED)
        Integer depletion_age,
        Boolean depleted,
        Integer target_age,
        ReadinessStatus status,
        List<TimelinePoint> timeline
    ) {}

    @Schema(name = "RetirementRecommendationResult", description = "계산 API 응답 본문 그대로 사용. 금액은 원 단위",
        requiredProperties = {"current_age", "recommendation_type", "required_saving", "required_income", "target_status", "depletion_age", "depleted", "target_age", "status", "timeline"})
    public record RetirementRecommendationResult(
        Integer current_age,
        RecommendationType recommendation_type,
        BigInteger required_saving,
        BigInteger required_income,
        ReadinessStatus target_status,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED)
        Integer depletion_age,
        Boolean depleted,
        Integer target_age,
        ReadinessStatus status,
        List<TimelinePoint> timeline
    ) {}

    @Schema(name = "EmployeePensionResult", description = "계산 API 응답 본문 그대로 사용. 금액은 원 단위",
        requiredProperties = {"retire_months", "current_band", "retire_band", "income_factor", "estimated_avg_income", "monthly_pension", "lump_sum", "severance_pay", "service_cap_years", "cap_basis"})
    public record EmployeePensionResult(
        Integer retire_months,
        String current_band,
        String retire_band,
        Double income_factor,
        BigInteger estimated_avg_income,
        BigInteger monthly_pension,
        BigInteger lump_sum,
        BigInteger severance_pay,
        Integer service_cap_years,
        CapBasis cap_basis
    ) {}

    @Schema(name = "ScenarioOutcome", description = "계산 API 응답 본문 그대로 사용. 금액은 원 단위",
        requiredProperties = {"scenario_type", "depletion_age", "depleted", "total_received", "break_even_age", "timeline"})
    public record ScenarioOutcome(
        ScenarioType scenario_type,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED)
        Integer depletion_age,
        Boolean depleted,
        BigInteger total_received,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED)
        Integer break_even_age,
        List<TimelinePoint> timeline
    ) {}

    @Schema(name = "ReceiptScenariosResult", description = "계산 API 응답 본문 그대로 사용. 금액은 원 단위",
        requiredProperties = {"current_age", "scenarios", "best_scenario"})
    public record ReceiptScenariosResult(
        Integer current_age,
        List<ScenarioOutcome> scenarios,
        ScenarioType best_scenario
    ) {}

}

