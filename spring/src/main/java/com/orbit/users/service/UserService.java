package com.orbit.users.service;

import com.orbit.users.domain.User;
import com.orbit.users.dto.SignupRequest;
import com.orbit.users.dto.UpdateUserRequest;
import com.orbit.users.exception.DuplicateEmailException;
import com.orbit.users.exception.InvalidTokenException;
import com.orbit.users.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class UserService {

	private final UserRepository userRepository;
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
			.employmentStatus(request.employmentStatus())
			.build();

		userRepository.save(user);
	}

	@Transactional
	public void delete(User user) {
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
			request.employmentStatus()
		);

		return user;
	}
}
