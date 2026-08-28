package com.orbit.diagnoses.client;

import com.orbit.diagnoses.dto.DiagnosisRequest;
import com.orbit.diagnoses.dto.FastApiDiagnosisResponse;
import com.orbit.diagnoses.exception.FastApiInvalidRequestException;
import com.orbit.diagnoses.exception.FastApiUnavailableException;
import com.orbit.global.exception.ErrorResponse;
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
import org.springframework.web.client.RestClientResponseException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

@Component
public class FastApiDiagnosisClient {

	private static final String DIAGNOSIS_PATH = "/api/retirement/diagnosis";

	private final RestClient restClient;
	private final ObjectMapper objectMapper;

	public FastApiDiagnosisClient(
		ObjectMapper objectMapper,
		@Value("${fastapi.base-url}") String baseUrl,
		@Value("${fastapi.connect-timeout-ms:3000}") long connectTimeoutMs,
		@Value("${fastapi.read-timeout-ms:5000}") long readTimeoutMs
	) {
		this.objectMapper = objectMapper;
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

	public FastApiDiagnosisResponse diagnose(DiagnosisRequest request) {
		try {
			JsonNode raw = restClient.post()
				.uri(DIAGNOSIS_PATH)
				.contentType(MediaType.APPLICATION_JSON)
				.body(toPayload(request))
				.retrieve()
				.body(JsonNode.class);
			return FastApiDiagnosisResponse.from(raw);
		} catch (RestClientResponseException exception) {
			int statusCode = exception.getStatusCode().value();
			if (statusCode == 400 || statusCode == 422) {
				throw toInvalidRequestException(exception);
			}
			throw new FastApiUnavailableException(exception);
		} catch (RestClientException | IllegalArgumentException exception) {
			throw new FastApiUnavailableException(exception);
		}
	}

	private FastApiInvalidRequestException toInvalidRequestException(RestClientResponseException exception) {
		try {
			ErrorResponse errorResponse = objectMapper.readValue(
				exception.getResponseBodyAsString(),
				ErrorResponse.class
			);
			return new FastApiInvalidRequestException(errorResponse, exception);
		} catch (Exception parsingException) {
			return new FastApiInvalidRequestException(exception);
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
