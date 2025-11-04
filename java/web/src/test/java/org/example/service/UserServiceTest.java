package org.example.service;

import org.example.config.AppConfig;
import org.example.repository.UserRepository;
import org.example.domain.User;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.junit.jupiter.SpringJUnitConfig;

@SpringJUnitConfig(classes = AppConfig.class)
public class UserServiceTest {

    @Autowired
    private UserRepository repo;

    @Test
    void testCreateAndFind() {
        User user = new User("alice", "Alice Wonderland");
        repo.save(user);
        Assertions.assertTrue(repo.findByUsername("alice").isPresent());
    }
}
