package org.example.config;

import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.context.annotation.Configuration;
import org.springframework.dao.annotation.PersistenceExceptionTranslationPostProcessor;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;
import org.springframework.orm.jpa.JpaTransactionManager;
import org.springframework.orm.jpa.LocalContainerEntityManagerFactoryBean;
import org.springframework.orm.jpa.vendor.HibernateJpaVendorAdapter;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.annotation.EnableTransactionManagement;

import javax.sql.DataSource;
import java.util.Properties;

@Configuration
@EnableTransactionManagement
@EnableJpaRepositories(basePackages = "org.example.repository")
@ComponentScan(basePackages = {"org.example.service"})
public class AppConfig {

    @Bean
    public DataSource dataSource() {
        // Default to H2 in-memory; can be overridden by system properties
        String jdbcUrl = System.getProperty("app.jdbc.url", "jdbc:h2:mem:webdb;DB_CLOSE_DELAY=-1;MODE=MySQL");
        String username = System.getProperty("app.jdbc.username", "sa");
        String password = System.getProperty("app.jdbc.password", "");
        String driver = System.getProperty("app.jdbc.driver", jdbcUrl.startsWith("jdbc:h2") ? "org.h2.Driver" : "com.mysql.cj.jdbc.Driver");

        HikariConfig config = new HikariConfig();
        config.setJdbcUrl(jdbcUrl);
        config.setUsername(username);
        config.setPassword(password);
        config.setDriverClassName(driver);
        config.setMaximumPoolSize(5);
        config.setPoolName("web-hikari");
        return new HikariDataSource(config);
    }

    @Bean
    public LocalContainerEntityManagerFactoryBean entityManagerFactory(DataSource dataSource) {
        LocalContainerEntityManagerFactoryBean emf = new LocalContainerEntityManagerFactoryBean();
        emf.setDataSource(dataSource);
        emf.setPackagesToScan("org.example.domain");
        emf.setJpaVendorAdapter(new HibernateJpaVendorAdapter());

        Properties props = new Properties();
        props.setProperty("hibernate.hbm2ddl.auto", System.getProperty("app.jpa.ddl-auto", "update"));
        props.setProperty("hibernate.show_sql", System.getProperty("app.jpa.show-sql", "false"));
        props.setProperty("hibernate.format_sql", "true");
        props.setProperty("hibernate.dialect", System.getProperty("app.jpa.dialect", "org.hibernate.dialect.H2Dialect"));
        emf.setJpaProperties(props);
        return emf;
    }

    @Bean
    public PlatformTransactionManager transactionManager(jakarta.persistence.EntityManagerFactory emf) {
        JpaTransactionManager tx = new JpaTransactionManager();
        tx.setEntityManagerFactory(emf);
        return tx;
    }

    @Bean
    public PersistenceExceptionTranslationPostProcessor exceptionTranslation() {
        return new PersistenceExceptionTranslationPostProcessor();
    }
}
