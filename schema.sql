-- Training Portal Schema

CREATE DATABASE IF NOT EXISTS training_portal;
USE training_portal;

CREATE TABLE IF NOT EXISTS users (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  full_name     VARCHAR(100) NOT NULL,
  email         VARCHAR(120) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role          ENUM('employee','hr') NOT NULL DEFAULT 'employee',
  department    VARCHAR(100),
  is_active     TINYINT(1) NOT NULL DEFAULT 1,
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trainings (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  title           VARCHAR(200) NOT NULL,
  description     TEXT,
  topic           VARCHAR(200),
  department      VARCHAR(100),
  trainer_name    VARCHAR(100),
  reg_open_date   DATE NOT NULL,
  reg_close_date  DATE NOT NULL,
  start_date      DATE NOT NULL,
  end_date        DATE NOT NULL,
  max_seats       INT DEFAULT 50,
  created_by      INT NOT NULL,
  source          ENUM('hr_created','employee_request') DEFAULT 'hr_created',
  request_id      INT DEFAULT NULL,
  is_active       TINYINT(1) DEFAULT 1,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS employee_requests (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  employee_id   INT NOT NULL,
  topic         VARCHAR(200) NOT NULL,
  reason        TEXT,
  status        ENUM('pending','approved','rejected') DEFAULT 'pending',
  hr_remarks    VARCHAR(255),
  training_id   INT DEFAULT NULL,
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (employee_id) REFERENCES users(id),
  FOREIGN KEY (training_id) REFERENCES trainings(id)
);

CREATE TABLE IF NOT EXISTS registrations (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  training_id   INT NOT NULL,
  employee_id   INT NOT NULL,
  registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_reg (training_id, employee_id),
  FOREIGN KEY (training_id) REFERENCES trainings(id),
  FOREIGN KEY (employee_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS feedback (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  training_id   INT NOT NULL,
  employee_id   INT NOT NULL,
  rating        TINYINT NOT NULL,
  comments      TEXT,
  submitted_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_feedback (training_id, employee_id),
  FOREIGN KEY (training_id) REFERENCES trainings(id),
  FOREIGN KEY (employee_id) REFERENCES users(id)
);