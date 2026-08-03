package com.orbit;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import tools.jackson.databind.ObjectMapper;

@SpringBootTest(properties = {
	"spring.datasource.url=jdbc:h2:mem:orbit-test;MODE=MySQL;DB_CLOSE_DELAY=-1",
	"spring.datasource.driver-class-name=org.h2.Driver",
	"spring.datasource.username=sa",
	"spring.datasource.password=",
	"spring.jpa.hibernate.ddl-auto=create-drop",
	"spring.jpa.database-platform=org.hibernate.dialect.H2Dialect"
})
@AutoConfigureMockMvc
class ApplicationTests {

	@Autowired
	private MockMvc mockMvc;

	@Autowired
	private ObjectMapper objectMapper;

	@Test
	void contextLoads() {
	}

	@Test
	void duplicateEmailReturns409Conflict() throws Exception {
		String requestBody = """
			{
			  "email": "duplicate-test@example.com",
			  "password": "password123",
			  "name": "Duplicate User",
			  "birthDate": "1995-01-01",
			  "gender": "MALE"
			}
			""";

		mockMvc.perform(post("/api/users/signup")
				.contentType(MediaType.APPLICATION_JSON)
				.content(requestBody))
			.andExpect(status().isCreated());

		mockMvc.perform(post("/api/users/signup")
				.contentType(MediaType.APPLICATION_JSON)
				.content(requestBody))
			.andExpect(status().isConflict())
			.andExpect(jsonPath("$.code").value("DUPLICATE_EMAIL"))
			.andExpect(jsonPath("$.message").isNotEmpty())
			.andExpect(jsonPath("$.details[0].field").value("email"))
			.andExpect(jsonPath("$.details[0].reason").isNotEmpty())
			.andExpect(jsonPath("$.timestamp").isNotEmpty());
	}

	@Test
	void validationErrorUsesUnifiedResponseShape() throws Exception {
		mockMvc.perform(post("/api/users/signup")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{
					  "email": "not-an-email",
					  "password": "short",
					  "name": "",
					  "birthDate": "1995-01-01",
					  "gender": "MALE"
					}
					"""))
			.andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.code").value("VALIDATION_ERROR"))
			.andExpect(jsonPath("$.message").isNotEmpty())
			.andExpect(jsonPath("$.details").isArray())
			.andExpect(jsonPath("$.details[0].field").isNotEmpty())
			.andExpect(jsonPath("$.details[0].reason").isNotEmpty())
			.andExpect(jsonPath("$.timestamp").isNotEmpty());
	}

	@Test
	void getMeDoesNotReturnEmploymentStatus() throws Exception {
		mockMvc.perform(post("/api/users/signup")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{
					  "email": "profile-test@example.com",
					  "password": "password123",
					  "name": "Hong Gil-dong",
					  "birthDate": "1995-01-01",
					  "gender": "MALE"
					}
					"""))
			.andExpect(status().isCreated());

		String loginResponse = mockMvc.perform(post("/api/users/login")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
					{
					  "email": "profile-test@example.com",
					  "password": "password123"
					}
					"""))
			.andExpect(status().isOk())
			.andReturn()
			.getResponse()
			.getContentAsString();

		String accessToken = objectMapper.readTree(loginResponse)
			.get("accessToken")
			.asString();

		mockMvc.perform(get("/api/users/me")
				.header("Authorization", "Bearer " + accessToken))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.email").value("profile-test@example.com"))
			.andExpect(jsonPath("$.employmentStatus").doesNotExist());
	}
}
