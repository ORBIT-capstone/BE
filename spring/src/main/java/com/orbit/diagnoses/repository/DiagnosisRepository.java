package com.orbit.diagnoses.repository;

import com.orbit.diagnoses.domain.Diagnosis;
import com.orbit.diagnoses.domain.DiagnosisType;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface DiagnosisRepository extends JpaRepository<Diagnosis, Long> {

	Optional<Diagnosis> findByIdAndUserIdAndDiagnosisType(Long id, Long userId, DiagnosisType diagnosisType);
}
