package com.orbit.users.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDate;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Getter
@Table(name = "users")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class User {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@Column(nullable = false, unique = true, length = 255)
	private String email;

	@Column(nullable = false)
	private String password;

	@Column(name = "refresh_token_hash", length = 512)
	private String refreshTokenHash;

	@Column(name = "access_token_hash", length = 512)
	private String accessTokenHash;

	@Column(nullable = false, length = 20)
	private String name;

	@Column(nullable = false)
	private LocalDate birthDate;

	@Enumerated(EnumType.STRING)
	@Column(nullable = false, length = 20)
	private Gender gender;

	@Column(name = "asset")
	private Long asset;

	@Column(name = "monthly_expenses")
	private Long monthlyExpenses;

	@Column(name = "current_years")
	private Integer currentYears;

	@Column(name = "monthly_pension")
	private Long monthlyPension;

	@Column(name = "monthly_income")
	private Long monthlyIncome;

	@Builder
	private User(
		String email,
		String password,
		String name,
		LocalDate birthDate,
		Gender gender
	) {
		this.email = email;
		this.password = password;
		this.name = name;
		this.birthDate = birthDate;
		this.gender = gender;
	}

	public void updateRefreshTokenHash(String refreshTokenHash) {
		this.refreshTokenHash = refreshTokenHash;
	}

	public void updateAccessTokenHash(String accessTokenHash) {
		this.accessTokenHash = accessTokenHash;
	}

	public void clearRefreshTokenHash() {
		this.refreshTokenHash = null;
	}

	public void clearAccessTokenHash() {
		this.accessTokenHash = null;
	}

	public void updateProfile(
		String name,
		LocalDate birthDate,
		Gender gender,
		Long asset,
		Long monthlyExpenses,
		Integer currentYears,
		Long monthlyPension,
		Long monthlyIncome
	) {
		if (name != null) {
			this.name = name;
		}
		if (birthDate != null) {
			this.birthDate = birthDate;
		}
		if (gender != null) {
			this.gender = gender;
		}
		if (asset != null) {
			this.asset = asset;
		}
		if (monthlyExpenses != null) {
			this.monthlyExpenses = monthlyExpenses;
		}
		if (currentYears != null) {
			this.currentYears = currentYears;
		}
		if (monthlyPension != null) {
			this.monthlyPension = monthlyPension;
		}
		if (monthlyIncome != null) {
			this.monthlyIncome = monthlyIncome;
		}
	}
}
