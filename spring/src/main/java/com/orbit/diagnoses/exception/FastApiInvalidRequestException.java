package com.orbit.diagnoses.exception;

import com.orbit.global.exception.ErrorResponse;

public class FastApiInvalidRequestException extends RuntimeException {

	private final ErrorResponse errorResponse;

	public FastApiInvalidRequestException(Throwable cause) {
		this(ErrorResponse.of("INVALID_REQUEST", "진단 요청 값이 올바르지 않습니다."), cause);
	}

	public FastApiInvalidRequestException(ErrorResponse errorResponse, Throwable cause) {
		super(errorResponse.message(), cause);
		this.errorResponse = errorResponse;
	}

	public ErrorResponse getErrorResponse() {
		return errorResponse;
	}
}
