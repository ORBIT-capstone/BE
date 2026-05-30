package com.orbit.users.service;

import com.orbit.users.domain.User;
import com.orbit.users.exception.InvalidTokenException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.Base64;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Service
public class AuthTokenService {

	private static final String HMAC_ALGORITHM = "HmacSHA256";
	private static final String ACCESS_TOKEN_TYPE = "access";
	private static final String REFRESH_TOKEN_TYPE = "refresh";

	private final byte[] secretKey;
	private final long accessTokenValiditySeconds;
	private final long refreshTokenValiditySeconds;

	public AuthTokenService(
		@Value("${auth.token.secret:orbit-local-token-secret-change-me}") String secret,
		@Value("${auth.token.access-token-validity-seconds:3600}") long accessTokenValiditySeconds,
		@Value("${auth.token.refresh-token-validity-seconds:1209600}") long refreshTokenValiditySeconds
	) {
		this.secretKey = secret.getBytes(StandardCharsets.UTF_8);
		this.accessTokenValiditySeconds = accessTokenValiditySeconds;
		this.refreshTokenValiditySeconds = refreshTokenValiditySeconds;
	}

	public String createAccessToken(User user) {
		return createToken(user, ACCESS_TOKEN_TYPE, accessTokenValiditySeconds);
	}

	public String createRefreshToken(User user) {
		return createToken(user, REFRESH_TOKEN_TYPE, refreshTokenValiditySeconds);
	}

	public Long getUserIdFromAccessToken(String token) {
		return validateAndParse(token, ACCESS_TOKEN_TYPE).userId();
	}

	public Long getUserIdFromRefreshToken(String token) {
		return validateAndParse(token, REFRESH_TOKEN_TYPE).userId();
	}

	public String hashToken(String token) {
		try {
			MessageDigest digest = MessageDigest.getInstance("SHA-256");
			byte[] hashed = digest.digest(token.getBytes(StandardCharsets.UTF_8));
			return Base64.getUrlEncoder().withoutPadding().encodeToString(hashed);
		} catch (Exception exception) {
			throw new IllegalStateException("토큰 해시 생성에 실패했습니다.", exception);
		}
	}

	public boolean matchesHash(String token, String expectedHash) {
		if (expectedHash == null) {
			return false;
		}

		return MessageDigest.isEqual(
			hashToken(token).getBytes(StandardCharsets.UTF_8),
			expectedHash.getBytes(StandardCharsets.UTF_8)
		);
	}

	private String createToken(User user, String tokenType, long validitySeconds) {
		long expiresAt = Instant.now().plusSeconds(validitySeconds).getEpochSecond();
		String payload = user.getId() + ":" + user.getEmail() + ":" + tokenType + ":" + expiresAt;
		String encodedPayload = encode(payload.getBytes(StandardCharsets.UTF_8));
		String signature = sign(encodedPayload);
		return encodedPayload + "." + signature;
	}

	private TokenClaims validateAndParse(String token, String requiredType) {
		try {
			String[] parts = token.split("\\.");
			if (parts.length != 2 || !MessageDigest.isEqual(sign(parts[0]).getBytes(StandardCharsets.UTF_8), parts[1].getBytes(StandardCharsets.UTF_8))) {
				throw new InvalidTokenException();
			}

			String payload = new String(Base64.getUrlDecoder().decode(parts[0]), StandardCharsets.UTF_8);
			String[] claims = payload.split(":");
			if (claims.length != 4) {
				throw new InvalidTokenException();
			}

			String tokenType = claims[2];
			long expiresAt = Long.parseLong(claims[3]);
			if (!requiredType.equals(tokenType) || Instant.now().getEpochSecond() > expiresAt) {
				throw new InvalidTokenException();
			}

			return new TokenClaims(Long.parseLong(claims[0]), claims[1], tokenType, expiresAt);
		} catch (InvalidTokenException exception) {
			throw exception;
		} catch (Exception exception) {
			throw new InvalidTokenException();
		}
	}

	private String sign(String value) {
		try {
			Mac mac = Mac.getInstance(HMAC_ALGORITHM);
			mac.init(new SecretKeySpec(secretKey, HMAC_ALGORITHM));
			return encode(mac.doFinal(value.getBytes(StandardCharsets.UTF_8)));
		} catch (Exception exception) {
			throw new IllegalStateException("토큰 서명에 실패했습니다.", exception);
		}
	}

	private String encode(byte[] bytes) {
		return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
	}

	private record TokenClaims(
		Long userId,
		String email,
		String tokenType,
		long expiresAt
	) {
	}
}
