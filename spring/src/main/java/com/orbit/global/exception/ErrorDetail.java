package com.orbit.global.exception;

public record ErrorDetail(
	String field,
	String reason
) {
}
