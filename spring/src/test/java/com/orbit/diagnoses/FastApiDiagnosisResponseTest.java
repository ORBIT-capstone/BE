package com.orbit.diagnoses;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.orbit.diagnoses.dto.FastApiDiagnosisResponse;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.ObjectMapper;

class FastApiDiagnosisResponseTest {

	private final ObjectMapper objectMapper = new ObjectMapper();

	@Test
	void acceptsValidContract() throws Exception {
		var node = objectMapper.readTree("""
			{"current_age":60,"monthly_gap":1000000,"depletion_age":75,"depleted":true,
			 "target_age":84,"status":"INSUFFICIENT","timeline":[]}
			""");

		assertDoesNotThrow(() -> FastApiDiagnosisResponse.from(node));
	}

	@Test
	void rejectsMissingStatus() throws Exception {
		var node = objectMapper.readTree("""
			{"current_age":60,"monthly_gap":1000000,"depletion_age":null,"depleted":false,
			 "target_age":84,"timeline":[]}
			""");

		assertThrows(IllegalArgumentException.class, () -> FastApiDiagnosisResponse.from(node));
	}

	@Test
	void rejectsInconsistentDepletionFields() throws Exception {
		var node = objectMapper.readTree("""
			{"current_age":60,"monthly_gap":1000000,"depletion_age":null,"depleted":true,
			 "target_age":84,"status":"SUFFICIENT","timeline":[]}
			""");

		assertThrows(IllegalArgumentException.class, () -> FastApiDiagnosisResponse.from(node));
	}
}
