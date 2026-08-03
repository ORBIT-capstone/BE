package com.orbit.diagnoses.service;

import com.orbit.diagnoses.client.FastApiDiagnosisClient;
import com.orbit.diagnoses.domain.Diagnosis;
import com.orbit.diagnoses.dto.DiagnosisDetailResponse;
import com.orbit.diagnoses.dto.DiagnosisRequest;
import com.orbit.diagnoses.dto.DiagnosisSummaryResponse;
import com.orbit.diagnoses.dto.FastApiDiagnosisResponse;
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

	public DiagnosisDetailResponse createDiagnosis(Long userId, DiagnosisRequest request) {
		// FastAPI 호출 완료 후에만 저장을 수행한다(트랜잭션 없이) — 호출 실패 시 자연스럽게 미저장되고,
		// 네트워크 대기 동안 DB 커넥션을 점유하지 않는다.
		FastApiDiagnosisResponse response = fastApiDiagnosisClient.diagnose(request);
		JsonNode result = response.raw();

		Diagnosis diagnosis = Diagnosis.builder()
			.userId(userId)
			.status(response.status())
			.depletionAge(response.depletionAge())
			.resultJson(result.toString())
			.build();

		Diagnosis savedDiagnosis = diagnosisRepository.save(diagnosis);

		return DiagnosisDetailResponse.from(savedDiagnosis, result);
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
			return node.isString() ? objectMapper.readTree(node.asString()) : node;
		} catch (JacksonException exception) {
			throw new IllegalStateException("저장된 진단 결과를 읽을 수 없습니다.", exception);
		}
	}
}
