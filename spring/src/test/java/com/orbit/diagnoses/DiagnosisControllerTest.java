package com.orbit.diagnoses;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.orbit.diagnoses.client.FastApiDiagnosisClient;
import com.orbit.diagnoses.dto.DiagnosisRequest;
import com.orbit.diagnoses.exception.FastApiUnavailableException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

@SpringBootTest(properties = {
	"spring.datasource.url=jdbc:h2:mem:diagnoses-test;MODE=MySQL;DB_CLOSE_DELAY=-1",
	"spring.datasource.driver-class-name=org.h2.Driver",
	"spring.datasource.username=sa",
	"spring.datasource.password=",
	"spring.jpa.hibernate.ddl-auto=create-drop",
	"spring.jpa.database-platform=org.hibernate.dialect.H2Dialect",
	"fastapi.base-url=http://localhost:0"
})
@AutoConfigureMockMvc
class DiagnosisControllerTest {

	private static final String DIAGNOSIS_REQUEST_BODY = """
		{
		  "currentAge": 60,
		  "monthlyExpenses": 250,
		  "monthlyPension": 150,
		  "asset": 10000,
		  "gender": "MALE"
		}
		""";

	@Autowired
	private MockMvc mockMvc;

	@Autowired
	private ObjectMapper objectMapper;

	@MockitoBean
	private FastApiDiagnosisClient fastApiDiagnosisClient;

	private String accessToken;

	@BeforeEach
	void signUpAndLogIn() throws Exception {
		String email = "diagnosis-test-" + System.nanoTime() + "@example.com";

		mockMvc.perform(post("/api/users/signup")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{
					  "email": "%s",
					  "password": "password123",
					  "name": "홍길동",
					  "birthDate": "1965-01-01",
					  "gender": "MALE",
					  "employmentStatus": "retirees"
					}
					""".formatted(email)))
			.andExpect(status().isCreated());

		String loginResponse = mockMvc.perform(post("/api/users/login")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{
					  "email": "%s",
					  "password": "password123"
					}
					""".formatted(email)))
			.andExpect(status().isOk())
			.andReturn()
			.getResponse()
			.getContentAsString();

		accessToken = objectMapper.readTree(loginResponse).get("accessToken").asString();
	}

	private JsonNode fastApiResult(int depletionAge, String status) throws Exception {
		return objectMapper.readTree("""
			{
			  "current_age": 60,
			  "monthly_gap": 100.0,
			  "depletion_age": %d,
			  "target_age": 84,
			  "status": "%s",
			  "timeline": [
			    {"age": 60, "asset": 10000.0, "income": 1800.0, "expense": 3000.0, "gap": 1200.0, "cumulative_gap": 1200.0}
			  ]
			}
			""".formatted(depletionAge, status));
	}

	@Test
	void createDiagnosisSavesAndReturnsFastApiResultAsIs() throws Exception {
		JsonNode result = fastApiResult(75, "INSUFFICIENT");
		when(fastApiDiagnosisClient.diagnose(any(DiagnosisRequest.class))).thenReturn(result);

		mockMvc.perform(post("/api/diagnoses")
				.header("Authorization", "Bearer " + accessToken)
				.contentType(MediaType.APPLICATION_JSON)
				.content(DIAGNOSIS_REQUEST_BODY))
			.andExpect(status().isCreated())
			.andExpect(jsonPath("$.status").value("INSUFFICIENT"))
			.andExpect(jsonPath("$.depletion_age").value(75))
			.andExpect(jsonPath("$.timeline[0].age").value(60));
	}

	@Test
	void listAndGetDiagnosisFlowWorks() throws Exception {
		JsonNode result = fastApiResult(80, "MIDDLE");
		when(fastApiDiagnosisClient.diagnose(any(DiagnosisRequest.class))).thenReturn(result);

		String createResponse = mockMvc.perform(post("/api/diagnoses")
				.header("Authorization", "Bearer " + accessToken)
				.contentType(MediaType.APPLICATION_JSON)
				.content(DIAGNOSIS_REQUEST_BODY))
			.andExpect(status().isCreated())
			.andReturn()
			.getResponse()
			.getContentAsString();
		// FastAPI 원본 응답에는 id가 없으므로, 목록 조회로 생성된 진단의 id를 확인한다
		org.junit.jupiter.api.Assertions.assertTrue(createResponse.contains("\"status\":\"MIDDLE\""));

		String listResponse = mockMvc.perform(get("/api/diagnoses")
				.header("Authorization", "Bearer " + accessToken))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$[0].status").value("MIDDLE"))
			.andExpect(jsonPath("$[0].depletionAge").value(80))
			.andReturn()
			.getResponse()
			.getContentAsString();

		Long id = objectMapper.readTree(listResponse).get(0).get("id").asLong();

		mockMvc.perform(get("/api/diagnoses/" + id)
				.header("Authorization", "Bearer " + accessToken))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.id").value(id))
			.andExpect(jsonPath("$.status").value("MIDDLE"))
			.andExpect(jsonPath("$.depletionAge").value(80))
			.andExpect(jsonPath("$.result.status").value("MIDDLE"))
			.andExpect(jsonPath("$.result.timeline[0].age").value(60));
	}

	@Test
	void createDiagnosisWithoutAuthorizationReturns401() throws Exception {
		mockMvc.perform(post("/api/diagnoses")
				.contentType(MediaType.APPLICATION_JSON)
				.content(DIAGNOSIS_REQUEST_BODY))
			.andExpect(status().isUnauthorized());
	}

	@Test
	void listDiagnosesWithoutAuthorizationReturns401() throws Exception {
		mockMvc.perform(get("/api/diagnoses"))
			.andExpect(status().isUnauthorized());
	}

	@Test
	void getDiagnosisOfAnotherUserReturns404() throws Exception {
		JsonNode result = fastApiResult(80, "MIDDLE");
		when(fastApiDiagnosisClient.diagnose(any(DiagnosisRequest.class))).thenReturn(result);

		String createResponse = mockMvc.perform(post("/api/diagnoses")
				.header("Authorization", "Bearer " + accessToken)
				.contentType(MediaType.APPLICATION_JSON)
				.content(DIAGNOSIS_REQUEST_BODY))
			.andExpect(status().isCreated())
			.andReturn()
			.getResponse()
			.getContentAsString();
		org.junit.jupiter.api.Assertions.assertNotNull(createResponse);

		String listResponse = mockMvc.perform(get("/api/diagnoses")
				.header("Authorization", "Bearer " + accessToken))
			.andReturn()
			.getResponse()
			.getContentAsString();
		Long id = objectMapper.readTree(listResponse).get(0).get("id").asLong();

		// 다른 유저로 새로 가입/로그인
		String otherEmail = "other-user-" + System.nanoTime() + "@example.com";
		mockMvc.perform(post("/api/users/signup")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{
					  "email": "%s",
					  "password": "password123",
					  "name": "다른유저",
					  "birthDate": "1970-01-01",
					  "gender": "FEMALE",
					  "employmentStatus": "retirees"
					}
					""".formatted(otherEmail)))
			.andExpect(status().isCreated());

		String otherLoginResponse = mockMvc.perform(post("/api/users/login")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{
					  "email": "%s",
					  "password": "password123"
					}
					""".formatted(otherEmail)))
			.andReturn()
			.getResponse()
			.getContentAsString();
		String otherAccessToken = objectMapper.readTree(otherLoginResponse).get("accessToken").asString();

		mockMvc.perform(get("/api/diagnoses/" + id)
				.header("Authorization", "Bearer " + otherAccessToken))
			.andExpect(status().isNotFound())
			.andExpect(jsonPath("$.code").value("DIAGNOSIS_NOT_FOUND"));
	}

	@Test
	void getNonExistentDiagnosisReturns404() throws Exception {
		mockMvc.perform(get("/api/diagnoses/999999")
				.header("Authorization", "Bearer " + accessToken))
			.andExpect(status().isNotFound())
			.andExpect(jsonPath("$.code").value("DIAGNOSIS_NOT_FOUND"));
	}

	@Test
	void getDiagnosisWithNonNumericIdReturns400() throws Exception {
		mockMvc.perform(get("/api/diagnoses/abc")
				.header("Authorization", "Bearer " + accessToken))
			.andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.code").value("INVALID_REQUEST"));
	}

	@Test
	void createDiagnosisReturns502WhenFastApiFails() throws Exception {
		when(fastApiDiagnosisClient.diagnose(any(DiagnosisRequest.class)))
			.thenThrow(new FastApiUnavailableException(new RuntimeException("connection refused")));

		mockMvc.perform(post("/api/diagnoses")
				.header("Authorization", "Bearer " + accessToken)
				.contentType(MediaType.APPLICATION_JSON)
				.content(DIAGNOSIS_REQUEST_BODY))
			.andExpect(status().isBadGateway())
			.andExpect(jsonPath("$.code").value("FASTAPI_UNAVAILABLE"));

		mockMvc.perform(get("/api/diagnoses")
				.header("Authorization", "Bearer " + accessToken))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.length()").value(0));
	}
}
