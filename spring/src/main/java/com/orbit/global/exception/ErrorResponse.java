package com.orbit.global.exception;

import java.time.OffsetDateTime;
import java.util.List;

public record ErrorResponse(
	String code,
	String message,
	List<ErrorDetail> details,
	OffsetDateTime timestamp
) {

	public static ErrorResponse of(String code, String message) {
		return of(code, message, List.of());
	}

	public static ErrorResponse of(String code, String message, List<ErrorDetail> details) {
		return new ErrorResponse(code, message, List.copyOf(details), OffsetDateTime.now());
	}
}
