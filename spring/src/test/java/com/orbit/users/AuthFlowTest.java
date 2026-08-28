package com.orbit.users;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

@SpringBootTest(properties = {
	"spring.datasource.url=jdbc:h2:mem:auth-test;MODE=MySQL;DB_CLOSE_DELAY=-1",
	"spring.datasource.driver-class-name=org.h2.Driver",
	"spring.datasource.username=sa", "spring.datasource.password=",
	"spring.jpa.hibernate.ddl-auto=create-drop",
	"spring.jpa.database-platform=org.hibernate.dialect.H2Dialect"
})
@AutoConfigureMockMvc
class AuthFlowTest {
	@Autowired MockMvc mockMvc;
	@Autowired ObjectMapper objectMapper;
	private String email;

	@BeforeEach
	void signup() throws Exception {
		email = "auth-" + System.nanoTime() + "@example.com";
		mockMvc.perform(post("/api/users/signup").contentType(MediaType.APPLICATION_JSON).content("""
			{"email":"%s","password":"password123","name":"홍길동","birthDate":"1990-01-01","gender":"MALE"}
			""".formatted(email))).andExpect(status().isCreated());
	}

	@Test
	void invalidPasswordReturns401() throws Exception {
		mockMvc.perform(post("/api/users/login").contentType(MediaType.APPLICATION_JSON).content("""
			{"email":"%s","password":"wrong-password"}
			""".formatted(email))).andExpect(status().isUnauthorized())
			.andExpect(jsonPath("$.code").value("INVALID_CREDENTIALS"));
	}

	@Test
	void refreshRotatesTokenAndRejectsPreviousRefreshToken() throws Exception {
		JsonNode first = login();
		String oldRefresh = first.get("refreshToken").asString();
		mockMvc.perform(post("/api/auth/refresh").contentType(MediaType.APPLICATION_JSON)
			.content("{\"refreshToken\":\"" + oldRefresh + "\"}"))
			.andExpect(status().isOk()).andExpect(jsonPath("$.refreshToken").isNotEmpty());
		mockMvc.perform(post("/api/auth/refresh").contentType(MediaType.APPLICATION_JSON)
			.content("{\"refreshToken\":\"" + oldRefresh + "\"}"))
			.andExpect(status().isUnauthorized()).andExpect(jsonPath("$.code").value("INVALID_TOKEN"));
	}

	@Test
	void logoutInvalidatesRefreshToken() throws Exception {
		JsonNode tokens = login();
		String access = tokens.get("accessToken").asString();
		String refresh = tokens.get("refreshToken").asString();
		mockMvc.perform(post("/api/users/logout").header("Authorization", "Bearer " + access)
			.contentType(MediaType.APPLICATION_JSON).content("{\"refreshToken\":\"" + refresh + "\"}"))
			.andExpect(status().isOk());
		mockMvc.perform(post("/api/auth/refresh").contentType(MediaType.APPLICATION_JSON)
			.content("{\"refreshToken\":\"" + refresh + "\"}"))
			.andExpect(status().isUnauthorized());
	}

	@Test
	void authenticatedProfileCanBeUpdatedAndDeleted() throws Exception {
		String access = login().get("accessToken").asString();
		mockMvc.perform(patch("/api/users/me").header("Authorization", "Bearer " + access)
			.contentType(MediaType.APPLICATION_JSON).content("{\"name\":\"새이름\"}"))
			.andExpect(status().isOk()).andExpect(jsonPath("$.name").value("새이름"));
		mockMvc.perform(delete("/api/users/me").header("Authorization", "Bearer " + access))
			.andExpect(status().isOk());
		mockMvc.perform(get("/api/users/me").header("Authorization", "Bearer " + access))
			.andExpect(status().isUnauthorized());
	}

	@Test
	void malformedAuthorizationHeaderReturns401() throws Exception {
		mockMvc.perform(get("/api/users/me").header("Authorization", "Token malformed"))
			.andExpect(status().isUnauthorized()).andExpect(jsonPath("$.code").value("UNAUTHORIZED"));
	}

	private JsonNode login() throws Exception {
		String response = mockMvc.perform(post("/api/users/login").contentType(MediaType.APPLICATION_JSON).content("""
			{"email":"%s","password":"password123"}
			""".formatted(email))).andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
		return objectMapper.readTree(response);
	}
}
