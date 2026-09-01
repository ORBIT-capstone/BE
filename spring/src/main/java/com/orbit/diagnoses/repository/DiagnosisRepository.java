package com.orbit.diagnoses.repository;

import com.orbit.diagnoses.domain.Diagnosis;
import com.orbit.diagnoses.domain.DiagnosisType;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface DiagnosisRepository extends JpaRepository<Diagnosis, Long> {

	Optional<Diagnosis> findByIdAndUserIdAndDiagnosisType(Long id, Long userId, DiagnosisType diagnosisType);

	Optional<Diagnosis> findByIdAndUserId(Long id, Long userId);

	List<Diagnosis> findByUserIdOrderByCreatedAtDesc(Long userId);

	void deleteAllByUserId(Long userId);
}
