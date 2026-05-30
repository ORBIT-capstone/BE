package com.orbit.users.service;

import com.orbit.users.domain.User;
import com.orbit.users.dto.LoginRequest;
import com.orbit.users.dto.TokenResponse;
import com.orbit.users.exception.InvalidCredentialsException;
import com.orbit.users.exception.InvalidTokenException;
import com.orbit.users.exception.UnauthorizedException;
import com.orbit.users.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class AuthService {

	private static final String BEARER_PREFIX = "Bearer ";

	private final UserRepository userRepository;
	private final PasswordEncoder passwordEncoder;
	private final AuthTokenService authTokenService;

	@Transactional
	public TokenResponse login(LoginRequest request) {
		User user = userRepository.findByEmail(request.email())
			.filter(foundUser -> passwordEncoder.matches(request.password(), foundUser.getPassword()))
			.orElseThrow(InvalidCredentialsException::new);

		return issueTokens(user);
	}

	@Transactional
	public void logout(String authorizationHeader, String refreshToken) {
		User user = getUserFromAuthorizationHeader(authorizationHeader);
		Long refreshTokenUserId = authTokenService.getUserIdFromRefreshToken(refreshToken);

		if (!user.getId().equals(refreshTokenUserId)) {
			throw new InvalidTokenException();
		}

		User tokenOwner = userRepository.findById(refreshTokenUserId)
			.orElseThrow(InvalidTokenException::new);

		if (!authTokenService.matchesHash(refreshToken, tokenOwner.getRefreshTokenHash())) {
			throw new InvalidTokenException();
		}

		tokenOwner.clearRefreshTokenHash();
	}

	@Transactional
	public TokenResponse refresh(String refreshToken) {
		Long userId = authTokenService.getUserIdFromRefreshToken(refreshToken);
		User user = userRepository.findById(userId)
			.orElseThrow(InvalidTokenException::new);

		if (!authTokenService.matchesHash(refreshToken, user.getRefreshTokenHash())) {
			throw new InvalidTokenException();
		}

		return issueTokens(user);
	}

	@Transactional(readOnly = true)
	public User getUserFromAuthorizationHeader(String authorizationHeader) {
		String accessToken = extractBearerToken(authorizationHeader);
		Long userId = authTokenService.getUserIdFromAccessToken(accessToken);
		return userRepository.findById(userId)
			.orElseThrow(InvalidTokenException::new);
	}

	private TokenResponse issueTokens(User user) {
		String accessToken = authTokenService.createAccessToken(user);
		String refreshToken = authTokenService.createRefreshToken(user);
		user.updateRefreshTokenHash(authTokenService.hashToken(refreshToken));
		return TokenResponse.bearer(accessToken, refreshToken);
	}

	private String extractBearerToken(String authorizationHeader) {
		if (authorizationHeader == null || !authorizationHeader.startsWith(BEARER_PREFIX)) {
			throw new UnauthorizedException();
		}

		String token = authorizationHeader.substring(BEARER_PREFIX.length()).trim();
		if (token.isBlank()) {
			throw new UnauthorizedException();
		}

		return token;
	}
}
