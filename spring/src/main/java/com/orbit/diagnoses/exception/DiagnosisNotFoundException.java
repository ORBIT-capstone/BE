package com.orbit.diagnoses.exception;

public class DiagnosisNotFoundException extends RuntimeException {

	public DiagnosisNotFoundException() {
		super("진단 결과를 찾을 수 없습니다.");
	}
}
