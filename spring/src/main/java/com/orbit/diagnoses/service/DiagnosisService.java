package com.orbit.diagnoses.service;

import com.orbit.diagnoses.client.FastApiDiagnosisClient;
import com.orbit.diagnoses.domain.Diagnosis;
import com.orbit.diagnoses.dto.DiagnosisDetailResponse;
import com.orbit.diagnoses.dto.DiagnosisRequest;
import com.orbit.diagnoses.dto.DiagnosisSummaryResponse;
import com.orbit.diagnoses.exception.DiagnosisNotFoundException;
import com.orbit.diagnoses.repository.DiagnosisRepository;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

@Service
@RequiredArgsConstructor
public class DiagnosisService {

	private final DiagnosisRepository diagnosisRepository;
	private final FastApiDiagnosisClient fastApiDiagnosisClient;
	private final ObjectMapper objectMapper;

	@Transactional
	public JsonNode createDiagnosis(Long userId, DiagnosisRequest request) {
		JsonNode result = fastApiDiagnosisClient.diagnose(request);

		Diagnosis diagnosis = Diagnosis.builder()
			.userId(userId)
			.status(result.path("status").asText(null))
			.depletionAge(result.hasNonNull("depletion_age") ? result.get("depletion_age").asInt() : null)
			.resultJson(result.toString())
			.build();

		diagnosisRepository.save(diagnosis);

		return result;
	}

	@Transactional(readOnly = true)
	public List<DiagnosisSummaryResponse> getSummaries(Long userId) {
		return diagnosisRepository.findByUserIdOrderByCreatedAtDesc(userId).stream()
			.map(DiagnosisSummaryResponse::from)
			.toList();
	}

	@Transactional(readOnly = true)
	public DiagnosisDetailResponse getDetail(Long userId, Long id) {
		Diagnosis diagnosis = diagnosisRepository.findByIdAndUserId(id, userId)
			.orElseThrow(DiagnosisNotFoundException::new);

		return DiagnosisDetailResponse.from(diagnosis, readResultJson(diagnosis.getResultJson()));
	}

	private JsonNode readResultJson(String resultJson) {
		try {
			JsonNode node = objectMapper.readTree(resultJson);
			// H2(MySQL 모드)의 JSON 컬럼은 문자열 바인딩 시 값을 한 번 더 JSON 문자열로
			// 감싸 저장하는 경우가 있어(MySQL 실제 환경에서는 발생하지 않음), 텍스트 노드로
			// 읽힌 경우에 한해 한 번 더 파싱해 원래 결과 트리를 복원한다.
			return node.isTextual() ? objectMapper.readTree(node.asText()) : node;
		} catch (JacksonException exception) {
			throw new IllegalStateException("저장된 진단 결과를 읽을 수 없습니다.", exception);
		}
	}
}
