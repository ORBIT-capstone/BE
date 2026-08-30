package com.orbit.diagnoses;

import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import com.orbit.diagnoses.domain.DiagnosisType;
import com.orbit.diagnoses.repository.DiagnosisRepository;
import com.orbit.users.repository.UserRepository;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ObjectNode;

@SpringBootTest(properties = {
    "spring.datasource.url=jdbc:h2:mem:diagnoses-test;MODE=MySQL;DB_CLOSE_DELAY=-1",
    "spring.datasource.driver-class-name=org.h2.Driver",
    "spring.datasource.username=sa", "spring.datasource.password=",
    "spring.jpa.hibernate.ddl-auto=create-drop",
    "spring.jpa.database-platform=org.hibernate.dialect.H2Dialect",
    // 계산 서버가 없어도 저장과 조회가 성공해야 한다.
    "fastapi.base-url=http://127.0.0.1:1"
})
@AutoConfigureMockMvc
class DiagnosisControllerTest {
    @Autowired MockMvc mockMvc;
    @Autowired ObjectMapper mapper;
    @Autowired DiagnosisRepository diagnoses;
    @Autowired UserRepository users;
    @Autowired org.springframework.jdbc.core.JdbcTemplate jdbc;
    String token;
    String email;

    @BeforeEach
    void setup() throws Exception {
        email = "diagnosis-" + System.nanoTime() + "@example.com";
        token = signupAndLogin(email);
    }

    String signupAndLogin(String address) throws Exception {
        mockMvc.perform(post("/api/users/signup").contentType(MediaType.APPLICATION_JSON).content("""
            {"email":"%s","password":"password123","name":"홍길동","birthDate":"1965-01-01","gender":"MALE"}
            """.formatted(address))).andExpect(status().isCreated());
        String body = mockMvc.perform(post("/api/users/login").contentType(MediaType.APPLICATION_JSON).content("""
            {"email":"%s","password":"password123"}
            """.formatted(address))).andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
        return mapper.readTree(body).get("accessToken").asString();
    }

    String path(DiagnosisType type) {
        return "/api/diagnoses/" + switch (type) {
            case RETIREMENT_ASSET -> "retirement/diagnosis";
            case PENSION_REDUCTION -> "retirement/reduction";
            case RETIREMENT_RECOMMENDATION -> "retirement/recommendations";
            case EMPLOYEE_PENSION -> "employees/simulate";
            case RECEIPT_SCENARIOS -> "employees/scenarios";
        };
    }

    ObjectNode result(DiagnosisType type) throws Exception {
        String fixture = switch (type) {
            case RETIREMENT_ASSET -> "diagnosis_insufficient";
            case PENSION_REDUCTION -> "reduction_partial";
            case RETIREMENT_RECOMMENDATION -> "recommendations_saving_only";
            case EMPLOYEE_PENSION -> "simulate_normal";
            case RECEIPT_SCENARIOS -> "scenarios_basic";
        };
        // 실제 계산 API의 회귀 테스트 응답을 사용하여 저장 계약이 FastAPI와 일치하는지 검증한다.
        return (ObjectNode) mapper.readTree(Files.readString(
            Path.of("..", "fastapi", "tests", "golden", fixture + ".json"))).get("body");
    }

    long save(DiagnosisType type, JsonNode body) throws Exception {
        String json = mockMvc.perform(post(path(type)).header("Authorization", "Bearer " + token)
            .contentType(MediaType.APPLICATION_JSON).content(body.toString()))
            .andExpect(status().isCreated()).andExpect(jsonPath("$.diagnosisType").value(type.name()))
            .andExpect(jsonPath("$.createdAt").exists())
            .andReturn().getResponse().getContentAsString();
        JsonNode saved = mapper.readTree(json);
        assertEquals(body, saved.get("result"));
        if (type == DiagnosisType.EMPLOYEE_PENSION || type == DiagnosisType.RECEIPT_SCENARIOS) {
            assertTrue(saved.get("status").isNull());
            assertTrue(saved.get("depletionAge").isNull());
        } else {
            assertEquals(body.get("status"), saved.get("status"));
            assertEquals(body.get("depletion_age"), saved.get("depletionAge"));
        }
        return saved.get("id").asLong();
    }

    JsonNode getResult(DiagnosisType type, long id) throws Exception {
        String json = mockMvc.perform(get(path(type) + "/" + id).header("Authorization", "Bearer " + token))
            .andExpect(status().isOk()).andExpect(jsonPath("$.diagnosisType").value(type.name()))
            .andReturn().getResponse().getContentAsString();
        return mapper.readTree(json).get("result");
    }

    @ParameterizedTest
    @EnumSource(DiagnosisType.class)
    void savesAndRetrievesCompleteCalculationResponseWithoutCalculationServer(DiagnosisType type) throws Exception {
        JsonNode body = result(type);
        long id = save(type, body);
        assertEquals(body, getResult(type, id));
        JsonNode stored = mapper.readTree(diagnoses.findById(id).orElseThrow().getResultJson());
        assertEquals(body, stored.isString() ? mapper.readTree(stored.asString()) : stored);

        DiagnosisType wrong = type == DiagnosisType.RETIREMENT_ASSET
            ? DiagnosisType.EMPLOYEE_PENSION : DiagnosisType.RETIREMENT_ASSET;
        mockMvc.perform(get(path(wrong) + "/" + id).header("Authorization", "Bearer " + token))
            .andExpect(status().isNotFound());
        String other = signupAndLogin("other-" + System.nanoTime() + "@example.com");
        mockMvc.perform(get(path(type) + "/" + id).header("Authorization", "Bearer " + other))
            .andExpect(status().isNotFound());
    }

    @ParameterizedTest
    @EnumSource(DiagnosisType.class)
    void preservesExtraResultFieldsWithoutOverridingOwnerOrType(DiagnosisType type) throws Exception {
        ObjectNode body = result(type);
        body.putObject("display_metadata").put("label", "프론트에 표시한 원본 결과");
        body.put("userId", -1);
        body.put("diagnosisType", "OTHER_TYPE");
        long id = save(type, body);
        assertEquals(body, getResult(type, id));
        assertEquals(users.findByEmail(email).orElseThrow().getId(), diagnoses.findById(id).orElseThrow().getUserId());
        assertEquals(type, diagnoses.findById(id).orElseThrow().getDiagnosisType());
    }

    @ParameterizedTest
    @EnumSource(DiagnosisType.class)
    void rejectsUnauthenticatedSaveAndRead(DiagnosisType type) throws Exception {
        mockMvc.perform(post(path(type)).contentType(MediaType.APPLICATION_JSON)
            .content(result(type).toString())).andExpect(status().isUnauthorized());
        mockMvc.perform(get(path(type) + "/1")).andExpect(status().isUnauthorized());
    }

    @Test
    void oldRoutesAreRemoved() throws Exception {
        mockMvc.perform(get("/api/diagnoses")).andExpect(status().isNotFound());
        mockMvc.perform(get("/api/diagnoses/1")).andExpect(status().isNotFound());
        mockMvc.perform(post("/api/diagnoses").contentType(MediaType.APPLICATION_JSON).content("{}"))
            .andExpect(status().isNotFound());
    }

    @ParameterizedTest
    @EnumSource(DiagnosisType.class)
    void rejectsCalculationInputsAndWrappedResultsInsteadOfSavingThem(DiagnosisType type) throws Exception {
        long count = diagnoses.count();
        String inputs = """
            {"currentAge":60,"monthlyExpenses":2500000,"monthlyPension":1500000,"asset":100000000,
             "gender":"MALE","currentYears":20,"currentIncome":4000000,"retireAtAge":65,
             "reemploymentIncome":4000000,"baseMonthlyIncome":3000000,"totalServiceYears":25}
            """;
        for (String body : List.of(inputs, "{}", "[]", "123", "{\"result\":" + result(type) + "}")) {
            mockMvc.perform(post(path(type)).header("Authorization", "Bearer " + token)
                .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isBadRequest()).andExpect(jsonPath("$.code").value("INVALID_DIAGNOSIS_RESULT"));
        }
        assertEquals(count, diagnoses.count());
    }

    @ParameterizedTest
    @EnumSource(DiagnosisType.class)
    void rejectsMissingOrMalformedResultFieldsWithoutSaving(DiagnosisType type) throws Exception {
        long count = diagnoses.count();
        ObjectNode body = result(type);
        String field = type == DiagnosisType.EMPLOYEE_PENSION ? "monthly_pension"
            : type == DiagnosisType.RECEIPT_SCENARIOS ? "scenarios" : "timeline";
        body.remove(field);
        mockMvc.perform(post(path(type)).header("Authorization", "Bearer " + token)
            .contentType(MediaType.APPLICATION_JSON).content(body.toString()))
            .andExpect(status().isBadRequest());
        body.put(field, "invalid");
        mockMvc.perform(post(path(type)).header("Authorization", "Bearer " + token)
            .contentType(MediaType.APPLICATION_JSON).content(body.toString()))
            .andExpect(status().isBadRequest());
        assertEquals(count, diagnoses.count());
    }

    @Test
    void rejectsInconsistentNestedScenarioAndTimelineFields() throws Exception {
        long count = diagnoses.count();
        ObjectNode scenarios = result(DiagnosisType.RECEIPT_SCENARIOS);
        ObjectNode scenario = (ObjectNode) scenarios.get("scenarios").get(0);
        scenario.putNull("depletion_age");
        scenario.put("depleted", true);
        mockMvc.perform(post(path(DiagnosisType.RECEIPT_SCENARIOS)).header("Authorization", "Bearer " + token)
            .contentType(MediaType.APPLICATION_JSON).content(scenarios.toString()))
            .andExpect(status().isBadRequest());
        ObjectNode reduction = result(DiagnosisType.PENSION_REDUCTION);
        ((ObjectNode) reduction.get("timeline").get(0)).remove("annual_income");
        mockMvc.perform(post(path(DiagnosisType.PENSION_REDUCTION)).header("Authorization", "Bearer " + token)
            .contentType(MediaType.APPLICATION_JSON).content(reduction.toString()))
            .andExpect(status().isBadRequest());
        assertEquals(count, diagnoses.count());
    }

    @Test
    void nullDepletionAndZeroAmountsRoundTripUnchanged() throws Exception {
        ObjectNode body = result(DiagnosisType.PENSION_REDUCTION);
        body.putNull("depletion_age");
        body.put("depleted", false);
        body.put("status", "SUFFICIENT");
        body.put("monthly_reduction", 0);
        body.put("reemployment_income", 0);
        long id = save(DiagnosisType.PENSION_REDUCTION, body);
        assertEquals(body, getResult(DiagnosisType.PENSION_REDUCTION, id));
    }

    @Test
    void legacySavedCalculationResultsRemainReadable() throws Exception {
        Long userId = users.findByEmail(email).orElseThrow().getId();
        JsonNode body = result(DiagnosisType.RETIREMENT_ASSET);
        jdbc.update("INSERT INTO diagnoses (user_id, status, depletion_age, result_json, created_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
            userId, body.get("status").asString(), body.get("depletion_age").asInt(), body.toString());
        Long id = jdbc.queryForObject("SELECT id FROM diagnoses WHERE user_id = ?", Long.class, userId);
        assertEquals(body, getResult(DiagnosisType.RETIREMENT_ASSET, id));
    }

    @Test
    void invalidAndUnknownIdsAreRejected() throws Exception {
        for (DiagnosisType type : DiagnosisType.values()) {
            mockMvc.perform(get(path(type) + "/abc").header("Authorization", "Bearer " + token))
                .andExpect(status().isBadRequest());
            mockMvc.perform(get(path(type) + "/999999").header("Authorization", "Bearer " + token))
                .andExpect(status().isNotFound());
        }
    }

    @Test
    void openApiDocumentsResponseBodiesAsSaveRequests() throws Exception {
        String json = mockMvc.perform(get("/api/v3/api-docs")).andExpect(status().isOk())
            .andReturn().getResponse().getContentAsString();
        JsonNode api = mapper.readTree(json);
        for (DiagnosisType type : DiagnosisType.values()) {
            JsonNode operation = api.get("paths").get(path(type)).get("post");
            String ref = operation.get("requestBody").get("content").get("application/json").get("schema").get("$ref").asString();
            JsonNode schema = api.get("components").get("schemas").get(ref.substring(ref.lastIndexOf('/') + 1));
            for (String field : result(type).propertyNames()) {
                assertTrue(schema.get("properties").has(field), type + ": " + field);
            }
            assertFalse(schema.get("properties").has("currentAge"));
            assertFalse(operation.get("responses").has("502"));
        }
    }
}
