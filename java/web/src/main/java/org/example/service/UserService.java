package org.example.service;

import org.example.domain.User;

import java.util.List;
import java.util.Optional;

public interface UserService {
    User create(String username, String fullName);
    Optional<User> findByUsername(String username);
    List<User> list();
}

