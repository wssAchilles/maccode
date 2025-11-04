package org.example.controller;

import org.example.service.UserService;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;

@Controller
public class HelloController {

    private final UserService userService;

    public HelloController(UserService userService) {
        this.userService = userService;
    }

    @GetMapping("/")
    public String index() {
        return "redirect:/home";
    }

    @GetMapping("/home")
    public String hello(Model model) {
        model.addAttribute("message", "Hello, Spring MVC!");
        model.addAttribute("users", userService.list());
        return "hello";
    }

    @PostMapping("/users")
    public String createUser(@RequestParam String username, @RequestParam String fullName) {
        userService.create(username, fullName);
        return "redirect:/home";
    }
}
