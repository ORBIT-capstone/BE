package com.orbit.diagnoses.repository;

import com.orbit.diagnoses.domain.Diagnosis;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface DiagnosisRepository extends JpaRepository<Diagnosis, Long> {

	List<Diagnosis> findByUserIdOrderByCreatedAtDesc(Long userId);

	Optional<Diagnosis> findByIdAndUserId(Long id, Long userId);
}
