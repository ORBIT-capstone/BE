package com.orbit.diagnoses.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;
import java.time.LocalDateTime;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Getter
@Table(name = "diagnoses", indexes = {
	@Index(name = "idx_diagnoses_user_id", columnList = "user_id")
})
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Diagnosis {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@Column(name = "user_id", nullable = false)
	private Long userId;

	@Column(nullable = false, length = 20)
	private String status;

	@Column(name = "depletion_age")
	private Integer depletionAge;

	@JdbcTypeCode(SqlTypes.JSON)
	@Column(name = "result_json", nullable = false, columnDefinition = "json")
	private String resultJson;

	@Column(name = "created_at", nullable = false, updatable = false)
	private LocalDateTime createdAt;

	@Builder
	private Diagnosis(Long userId, String status, Integer depletionAge, String resultJson) {
		this.userId = userId;
		this.status = status;
		this.depletionAge = depletionAge;
		this.resultJson = resultJson;
	}

	@PrePersist
	private void prePersist() {
		this.createdAt = LocalDateTime.now();
	}
}
