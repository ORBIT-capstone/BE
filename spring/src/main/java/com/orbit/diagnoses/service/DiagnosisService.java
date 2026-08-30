package com.orbit.diagnoses.service;

import com.orbit.diagnoses.domain.Diagnosis;
import com.orbit.diagnoses.domain.DiagnosisType;
import com.orbit.diagnoses.dto.DiagnosisDetailResponse;
import com.orbit.diagnoses.dto.FastApiDiagnosisResponse;
import com.orbit.diagnoses.exception.DiagnosisNotFoundException;
import com.orbit.diagnoses.exception.InvalidDiagnosisResultException;
import com.orbit.diagnoses.repository.DiagnosisRepository;
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
	private final ObjectMapper objectMapper;

	@Transactional
	public DiagnosisDetailResponse saveResult(Long userId, DiagnosisType type, JsonNode result) {
		// 프론트가 받은 계산 응답을 검증 후 그대로 저장한다. 계산 서버를 호출하지 않는다.
		FastApiDiagnosisResponse response;
		try {
			response = FastApiDiagnosisResponse.from(type, result);
		} catch (IllegalArgumentException exception) {
			throw new InvalidDiagnosisResultException(exception.getMessage());
		}

		Diagnosis diagnosis = Diagnosis.builder()
			.userId(userId)
			.diagnosisType(type)
			.status(response.status())
			.depletionAge(response.depletionAge())
			.resultJson(result.toString())
			.build();

		Diagnosis savedDiagnosis = diagnosisRepository.save(diagnosis);

		return DiagnosisDetailResponse.from(savedDiagnosis, result);
	}

	@Transactional(readOnly = true)
	public DiagnosisDetailResponse getDetail(Long userId, Long id, DiagnosisType type) {
		Diagnosis diagnosis = diagnosisRepository.findByIdAndUserIdAndDiagnosisType(id, userId, type)
			.orElseThrow(DiagnosisNotFoundException::new);

		// 저장 시 전달받은 결과 전체를 복원한다. 입력값으로 재계산하거나 필드를 재구성하지 않는다.
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
