package com.orbit.diagnoses.exception;

public class FastApiUnavailableException extends RuntimeException {

	public FastApiUnavailableException(Throwable cause) {
		super("진단 서버 호출에 실패했습니다.", cause);
	}
}
