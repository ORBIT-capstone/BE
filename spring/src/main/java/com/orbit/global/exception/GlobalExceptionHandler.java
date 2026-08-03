package com.orbit.global.exception;

import com.orbit.diagnoses.exception.DiagnosisNotFoundException;
import com.orbit.diagnoses.exception.FastApiInvalidRequestException;
import com.orbit.diagnoses.exception.FastApiUnavailableException;
import com.orbit.users.exception.DuplicateEmailException;
import com.orbit.users.exception.InvalidCredentialsException;
import com.orbit.users.exception.InvalidTokenException;
import com.orbit.users.exception.UnauthorizedException;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.http.ResponseEntity;
import org.springframework.web.HttpMediaTypeNotSupportedException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

@RestControllerAdvice
public class GlobalExceptionHandler {

	@ExceptionHandler(MethodArgumentNotValidException.class)
	public ResponseEntity<ErrorResponse> handleValidationException(MethodArgumentNotValidException exception) {
		List<ErrorDetail> details = exception.getBindingResult()
			.getFieldErrors()
			.stream()
			.map(error -> new ErrorDetail(error.getField(), error.getDefaultMessage()))
			.toList();

		return ResponseEntity.badRequest()
			.body(ErrorResponse.of("VALIDATION_ERROR", "입력값을 확인해주세요.", details));
	}

	@ExceptionHandler(DuplicateEmailException.class)
	public ResponseEntity<ErrorResponse> handleDuplicateEmail(DuplicateEmailException exception) {
		return ResponseEntity.status(HttpStatus.CONFLICT)
			.body(ErrorResponse.of(
				"DUPLICATE_EMAIL",
				exception.getMessage(),
				List.of(new ErrorDetail("email", "이미 사용 중인 이메일입니다."))
			));
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

	@ExceptionHandler(MethodArgumentTypeMismatchException.class)
	public ResponseEntity<ErrorResponse> handleTypeMismatch(MethodArgumentTypeMismatchException exception) {
		String message = exception.getName() + " 값이 올바르지 않습니다.";
		return ResponseEntity.badRequest()
			.body(ErrorResponse.of(
				"INVALID_REQUEST",
				message,
				List.of(new ErrorDetail(exception.getName(), "요청 값의 타입이 올바르지 않습니다."))
			));
	}

	@ExceptionHandler(NoResourceFoundException.class)
	public ResponseEntity<ErrorResponse> handleNotFound(NoResourceFoundException exception) {
		return ResponseEntity.status(HttpStatus.NOT_FOUND)
			.body(ErrorResponse.of("NOT_FOUND", "요청한 리소스를 찾을 수 없습니다."));
	}

	@ExceptionHandler(DiagnosisNotFoundException.class)
	public ResponseEntity<ErrorResponse> handleDiagnosisNotFound(DiagnosisNotFoundException exception) {
		return ResponseEntity.status(HttpStatus.NOT_FOUND)
			.body(ErrorResponse.of("DIAGNOSIS_NOT_FOUND", exception.getMessage()));
	}

	@ExceptionHandler(FastApiUnavailableException.class)
	public ResponseEntity<ErrorResponse> handleFastApiUnavailable(FastApiUnavailableException exception) {
		return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
			.body(ErrorResponse.of("FASTAPI_UNAVAILABLE", exception.getMessage()));
	}

	@ExceptionHandler(FastApiInvalidRequestException.class)
	public ResponseEntity<ErrorResponse> handleFastApiInvalidRequest(FastApiInvalidRequestException exception) {
		return ResponseEntity.badRequest()
			.body(exception.getErrorResponse());
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

	@ExceptionHandler(HttpMessageNotReadableException.class)
	public ResponseEntity<ErrorResponse> handleMessageNotReadable(HttpMessageNotReadableException exception) {
		String message = exception.getMostSpecificCause().getMessage();
		if (message == null || message.isBlank()) {
			message = "요청 본문을 읽을 수 없습니다.";
		}

		return ResponseEntity.badRequest()
			.body(ErrorResponse.of("INVALID_REQUEST", message));
	}

	@ExceptionHandler(Exception.class)
	public ResponseEntity<ErrorResponse> handleException(Exception exception) {
		return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
			.body(ErrorResponse.of("INTERNAL_SERVER_ERROR", "서버 내부 오류가 발생했습니다."));
	}
}
