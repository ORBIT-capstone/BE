package com.orbit.users.exception;

public class UnauthorizedException extends RuntimeException {

	public UnauthorizedException() {
		super("인증이 필요합니다.");
	}
}
