package com.orbit.diagnoses.client;

import com.orbit.diagnoses.dto.DiagnosisRequest;
import com.orbit.diagnoses.exception.FastApiUnavailableException;
import java.net.http.HttpClient;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import tools.jackson.databind.JsonNode;

@Component
public class FastApiDiagnosisClient {

	private static final String DIAGNOSIS_PATH = "/api/retirement/diagnosis";

	private final RestClient restClient;

	public FastApiDiagnosisClient(
		@Value("${fastapi.base-url}") String baseUrl,
		@Value("${fastapi.connect-timeout-ms:3000}") long connectTimeoutMs,
		@Value("${fastapi.read-timeout-ms:5000}") long readTimeoutMs
	) {
		HttpClient httpClient = HttpClient.newBuilder()
			.connectTimeout(Duration.ofMillis(connectTimeoutMs))
			.build();
		JdkClientHttpRequestFactory requestFactory = new JdkClientHttpRequestFactory(httpClient);
		requestFactory.setReadTimeout(Duration.ofMillis(readTimeoutMs));

		this.restClient = RestClient.builder()
			.baseUrl(baseUrl)
			.requestFactory(requestFactory)
			.build();
	}

	public JsonNode diagnose(DiagnosisRequest request) {
		try {
			return restClient.post()
				.uri(DIAGNOSIS_PATH)
				.contentType(MediaType.APPLICATION_JSON)
				.body(toPayload(request))
				.retrieve()
				.body(JsonNode.class);
		} catch (RestClientException exception) {
			throw new FastApiUnavailableException(exception);
		}
	}

	private Map<String, Object> toPayload(DiagnosisRequest request) {
		Map<String, Object> payload = new LinkedHashMap<>();
		payload.put("current_age", request.currentAge());
		payload.put("monthly_expenses", request.monthlyExpenses());
		payload.put("monthly_pension", request.monthlyPension());
		payload.put("asset", request.asset());
		payload.put("gender", request.gender().name().toLowerCase());
		return payload;
	}
}
