package com.orbit.users.domain;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;
import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "재직 상태", allowableValues = {"employees", "retirees"})
public enum EmploymentStatus {
	EMPLOYEES("employees"),
	RETIREES("retirees");

	private final String value;

	EmploymentStatus(String value) {
		this.value = value;
	}

	@JsonCreator
	public static EmploymentStatus from(String value) {
		for (EmploymentStatus employmentStatus : values()) {
			if (employmentStatus.value.equals(value)) {
				return employmentStatus;
			}
		}
		throw new IllegalArgumentException("employmentStatus는 employees 또는 retirees 중 하나여야 합니다.");
	}

	@JsonValue
	public String getValue() {
		return value;
	}
}
