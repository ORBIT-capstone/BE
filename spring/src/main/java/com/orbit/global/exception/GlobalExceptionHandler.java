package com.orbit.global.exception;

import com.orbit.users.exception.DuplicateEmailException;
import com.orbit.users.exception.InvalidCredentialsException;
import com.orbit.users.exception.InvalidTokenException;
import com.orbit.users.exception.UnauthorizedException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.HttpMediaTypeNotSupportedException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.servlet.resource.NoResourceFoundException;

@RestControllerAdvice
public class GlobalExceptionHandler {

	@ExceptionHandler(MethodArgumentNotValidException.class)
	public ResponseEntity<ErrorResponse> handleValidationException(MethodArgumentNotValidException exception) {
		String message = exception.getBindingResult()
			.getFieldErrors()
			.stream()
			.findFirst()
			.map(error -> error.getField() + ": " + error.getDefaultMessage())
			.orElse("요청 값이 올바르지 않습니다.");

		return ResponseEntity.badRequest()
			.body(ErrorResponse.of("INVALID_REQUEST", message));
	}

	@ExceptionHandler(DuplicateEmailException.class)
	public ResponseEntity<ErrorResponse> handleDuplicateEmail(DuplicateEmailException exception) {
		return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY)
			.body(ErrorResponse.of("DUPLICATE_EMAIL", exception.getMessage()));
	}

	@ExceptionHandler(InvalidCredentialsException.class)
	public ResponseEntity<ErrorResponse> handleInvalidCredentials(InvalidCredentialsException exception) {
		return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
			.body(ErrorResponse.of("INVALID_CREDENTIALS", exception.getMessage()));
	}

	@ExceptionHandler(UnauthorizedException.class)
	public ResponseEntity<ErrorResponse> handleUnauthorized(UnauthorizedException exception) {
		return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
			.body(ErrorResponse.of("UNAUTHORIZED", exception.getMessage()));
	}

	@ExceptionHandler(InvalidTokenException.class)
	public ResponseEntity<ErrorResponse> handleInvalidToken(InvalidTokenException exception) {
		return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
			.body(ErrorResponse.of("INVALID_TOKEN", exception.getMessage()));
	}

	@ExceptionHandler(NoResourceFoundException.class)
	public ResponseEntity<ErrorResponse> handleNotFound(NoResourceFoundException exception) {
		return ResponseEntity.status(HttpStatus.NOT_FOUND)
			.body(ErrorResponse.of("NOT_FOUND", "요청한 리소스를 찾을 수 없습니다."));
	}

	@ExceptionHandler(HttpRequestMethodNotSupportedException.class)
	public ResponseEntity<ErrorResponse> handleMethodNotAllowed(HttpRequestMethodNotSupportedException exception) {
		return ResponseEntity.status(HttpStatus.METHOD_NOT_ALLOWED)
			.body(ErrorResponse.of("METHOD_NOT_ALLOWED", "허용되지 않은 HTTP 메서드입니다."));
	}

	@ExceptionHandler(HttpMediaTypeNotSupportedException.class)
	public ResponseEntity<ErrorResponse> handleUnsupportedMediaType(HttpMediaTypeNotSupportedException exception) {
		return ResponseEntity.status(HttpStatus.UNSUPPORTED_MEDIA_TYPE)
			.body(ErrorResponse.of("UNSUPPORTED_MEDIA_TYPE", "지원하지 않는 요청 형식입니다."));
	}

	@ExceptionHandler(Exception.class)
	public ResponseEntity<ErrorResponse> handleException(Exception exception) {
		return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
			.body(ErrorResponse.of("INTERNAL_SERVER_ERROR", "서버 내부 오류가 발생했습니다."));
	}
}
