package com.orbit.users.service;

import com.orbit.diagnoses.repository.DiagnosisRepository;
import com.orbit.users.domain.User;
import com.orbit.users.dto.SignupRequest;
import com.orbit.users.dto.UpdateUserRequest;
import com.orbit.users.exception.DuplicateEmailException;
import com.orbit.users.exception.InvalidTokenException;
import com.orbit.users.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class UserService {

	private final UserRepository userRepository;
	private final DiagnosisRepository diagnosisRepository;
	private final PasswordEncoder passwordEncoder;

	@Transactional
	public void signup(SignupRequest request) {
		if (userRepository.existsByEmail(request.email())) {
			throw new DuplicateEmailException();
		}

		User user = User.builder()
			.email(request.email())
			.password(passwordEncoder.encode(request.password()))
			.name(request.name())
			.birthDate(request.birthDate())
			.gender(request.gender())
			.build();

		try {
			// flush 시점까지 unique 제약 위반을 확인해 동시 가입도 일관되게 409로 변환한다.
			userRepository.saveAndFlush(user);
		} catch (DataIntegrityViolationException exception) {
			throw new DuplicateEmailException();
		}
	}

	@Transactional
	public void delete(User user) {
		diagnosisRepository.deleteAllByUserId(user.getId());
		userRepository.delete(user);
	}

	@Transactional
	public User update(Long userId, UpdateUserRequest request) {
		User user = userRepository.findById(userId)
			.orElseThrow(InvalidTokenException::new);

		user.updateProfile(
			request.name(),
			request.birthDate(),
			request.gender(),
			request.asset(),
			request.monthlyExpenses(),
			request.currentYears(),
			request.monthlyPension(),
			request.monthlyIncome()
		);

		return user;
	}
}
